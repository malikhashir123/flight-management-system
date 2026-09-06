import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, require_role
from backend.app.core.audit import log_system_decision
from backend.app.services.notification_service import send_transactional_email
from backend.app.models.all_models import (
    User, Booking, Flight, SupportDraft, PriceAlert
)
from backend.app.models.enums import UserRole, ApprovalStatus
from backend.app.schemas.support_schemas import (
    CustomerSupportInquiryRequest, SupportDraftResponse, HumanApprovalActionRequest
)
from pydantic import BaseModel, Field

router = APIRouter(prefix="/support", tags=["RAG Policy Support & Human Gate"])

class PriceAlertCreateRequest(BaseModel):
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    target_price: float = Field(gt=0)

@router.post("/inquiry", response_model=SupportDraftResponse, status_code=status.HTTP_201_CREATED)
async def submit_policy_inquiry(
    req: CustomerSupportInquiryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Customer submits policy question.
    Grounded RAG retrieves customer's exact booking and fare type from Postgres,
    and drafts an answer that reflects their actual fare rule, not a generic match.
    The answer is placed in the human approval queue.
    Enforces REQ-FRD-37, REQ-FRD-38, REQ-APP-43.
    """
    booking = None
    fare_type_name = "STANDARD_POLICY"
    booking_id = None
    flight_context = "General Policy Inquiry"

    if req.booking_reference:
        b_res = await db.execute(
            select(Booking).where(Booking.booking_reference == req.booking_reference.strip().upper())
        )
        booking = b_res.scalar_one_or_none()
        if booking:
            booking_id = booking.id
            fare_type_name = booking.fare_type
            f_res = await db.execute(select(Flight).where(Flight.id == booking.flight_id))
            flight = f_res.scalar_one()
            flight_context = (
                f"Flight {flight.flight_number} ({flight.origin}->{flight.destination}), "
                f"Departure: {flight.departure_time.strftime('%Y-%m-%d %H:%M UTC')}, "
                f"Fare Type: {booking.fare_type}, Involuntary Override: {booking.eligible_for_involuntary_refund}"
            )

    # Policy knowledge grounding logic (REQ-FRD-37)
    # The drafted answer MUST reflect the actual booking's fare rule!
    if fare_type_name == "BASIC_ECONOMY":
        draft_answer = (
            f"Dear Customer,\n\n"
            f"Regarding your inquiry concerning booking {req.booking_reference or 'your reservation'}: "
            f"Our records show your ticket was purchased under the BASIC ECONOMY fare rule. "
            f"Under Section 3.2 of the Airline Policy, Basic Economy fares are strictly non-refundable "
            f"and voluntary date/route changes are not permitted for cash refunds. "
            f"If your flight experiences an involuntary airline schedule change of 2 hours or more, "
            f"you are entitled to a 100% full refund under statutory airline rights. "
            f"Please let us know if we can assist you with any other details."
        )
    elif fare_type_name in ["FLEXIBLE", "BUSINESS_FLEX"]:
        draft_answer = (
            f"Dear Customer,\n\n"
            f"Regarding your inquiry concerning booking {req.booking_reference or 'your reservation'}: "
            f"Your ticket is confirmed under the FLEXIBLE fare rule. "
            f"Under Section 4.1 of the Airline Policy, you may cancel your flight up to 24 hours prior "
            f"to departure for a refund to your original payment method (minus standard $25 processing fee) "
            f"or exchange for a full 100% travel voucher valid for 365 days with zero fee."
        )
    else:
        draft_answer = (
            f"Dear Customer,\n\n"
            f"Thank you for contacting customer support. Regarding your inquiry: '{req.query}'. "
            f"General airline policy allows ticket changes according to the fare conditions chosen at booking. "
            f"Flexible fares allow free changes; Basic Economy fares do not allow voluntary cancellations."
        )

    draft = SupportDraft(
        id=str(uuid.uuid4()),
        booking_id=booking_id,
        customer_email=req.customer_email,
        customer_query=req.query,
        retrieved_context={"fare_type": fare_type_name, "flight_details": flight_context},
        rag_drafted_answer=draft_answer,
        approval_status=ApprovalStatus.PENDING_REVIEW.value
    )
    db.add(draft)

    await log_system_decision(
        db=db,
        event_type="RAG_POLICY_DRAFT_CREATED",
        actor_system="N8N_FASTAPI_RAG",
        actor_id="RAG_PIPELINE",
        entity_type="SUPPORT_DRAFT",
        entity_id=draft.id,
        rule_applied="FARE_RULE_GROUNDED_INJECTION",
        decision_metadata={"fare_type": fare_type_name, "customer_email": req.customer_email}
    )

    await db.commit()
    await db.refresh(draft)

    return SupportDraftResponse(
        id=draft.id,
        booking_id=draft.booking_id,
        customer_email=draft.customer_email,
        customer_query=draft.customer_query,
        rag_drafted_answer=draft.rag_drafted_answer,
        approval_status=ApprovalStatus(draft.approval_status),
        created_at=draft.created_at
    )

@router.get("/drafts", response_model=List[SupportDraftResponse])
async def list_pending_drafts(
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.OPS_AGENT)),
    db: AsyncSession = Depends(get_db)
):
    """Supervisor review queue of pending RAG drafts. Enforces REQ-FRD-38, REQ-APP-43."""
    q = select(SupportDraft).where(
        SupportDraft.approval_status == ApprovalStatus.PENDING_REVIEW.value
    ).order_by(SupportDraft.created_at.desc())
    drafts = (await db.execute(q)).scalars().all()

    return [
        SupportDraftResponse(
            id=d.id,
            booking_id=d.booking_id,
            customer_email=d.customer_email,
            customer_query=d.customer_query,
            rag_drafted_answer=d.rag_drafted_answer,
            approval_status=ApprovalStatus(d.approval_status),
            created_at=d.created_at
        )
        for d in drafts
    ]

@router.post("/drafts/{draft_id}/approve")
async def approve_rag_draft(
    draft_id: str,
    action_req: HumanApprovalActionRequest,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.OPS_AGENT)),
    db: AsyncSession = Depends(get_db)
):
    """
    Human approval gate before any RAG-drafted answer is sent via Gmail.
    Enforces REQ-FRD-38, REQ-APP-43, REQ-INF-55.
    """
    d_res = await db.execute(
        select(SupportDraft).where(SupportDraft.id == draft_id).with_for_update()
    )
    draft = d_res.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found.")

    if draft.approval_status != ApprovalStatus.PENDING_REVIEW.value:
        raise HTTPException(status_code=400, detail=f"Draft already in status: {draft.approval_status}")

    now = datetime.now(timezone.utc)

    if action_req.action.upper() == "APPROVE":
        draft.approval_status = ApprovalStatus.APPROVED.value
        draft.reviewed_by = current_user.id
        draft.review_notes = action_req.notes
        draft.approved_at = now
        draft.email_sent_at = now

        # Dispatch approved email to customer via Gmail service
        email_html = f"""
        <h3>Official Airline Customer Support Response</h3>
        <p>{draft.rag_drafted_answer.replace(chr(10), '<br/>')}</p>
        <hr/>
        <small>Approved by Support Supervisor ID: {current_user.id} at {now.strftime('%Y-%m-%d %H:%M UTC')}</small>
        """
        await send_transactional_email(
            db=db,
            recipient=draft.customer_email,
            subject="Official Airline Customer Support: Response to your inquiry",
            template_name="APPROVED_POLICY_REPLY",
            html_content=email_html,
            reference_id=draft.id
        )
        msg = "Draft approved and officially dispatched via Gmail to customer."
    else:
        draft.approval_status = ApprovalStatus.REJECTED.value
        draft.reviewed_by = current_user.id
        draft.review_notes = action_req.notes
        msg = "Draft rejected. Email dispatch aborted."

    await log_system_decision(
        db=db,
        event_type="HUMAN_RAG_APPROVAL_DECISION",
        actor_system="HUMAN_SUPERVISOR",
        actor_id=current_user.id,
        entity_type="SUPPORT_DRAFT",
        entity_id=draft.id,
        rule_applied="MANDATORY_HUMAN_SIGN_OFF_GATE",
        decision_metadata={"action": action_req.action, "notes": action_req.notes}
    )

    await db.commit()
    return {"message": msg, "draft_id": draft.id, "status": draft.approval_status}

@router.post("/price-alert", status_code=status.HTTP_201_CREATED)
async def subscribe_price_alert(
    req: PriceAlertCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Subscribes to price-drop alerts. Enforces REQ-SCH-34."""
    alert = PriceAlert(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        origin=req.origin.upper(),
        destination=req.destination.upper(),
        target_price=req.target_price,
        is_active=True
    )
    db.add(alert)
    await db.commit()
    return {"message": f"Subscribed to price-drop alerts for {alert.origin}->{alert.destination} below ${alert.target_price}."}
