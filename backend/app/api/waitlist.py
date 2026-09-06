import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.core.audit import log_system_decision
from backend.app.models.all_models import User, Flight, FlightClass, WaitlistEntry
from backend.app.models.enums import SeatClassCode, LoyaltyTier, WaitlistStatus
from backend.app.schemas.waitlist_schemas import WaitlistJoinRequest, WaitlistEntryResponse

router = APIRouter(prefix="/waitlist", tags=["Waitlist & Standby"])

TIER_SCORES = {
    LoyaltyTier.PLATINUM.value: 4000,
    LoyaltyTier.GOLD.value: 3000,
    LoyaltyTier.SILVER.value: 2000,
    LoyaltyTier.BRONZE.value: 1000,
    LoyaltyTier.NONE.value: 0
}

@router.post("/flights/{flight_id}", response_model=WaitlistEntryResponse, status_code=status.HTTP_201_CREATED)
async def join_waitlist(
    flight_id: str,
    req: WaitlistJoinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Adds passenger to waitlist when a class/flight is full.
    Computes priority score based on loyalty tier and booking timestamp.
    Enforces REQ-WST-28, REQ-WST-29.
    """
    f_res = await db.execute(select(Flight).where(Flight.id == flight_id))
    flight = f_res.scalar_one_or_none()
    if not flight or flight.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Flight not active.")

    c_res = await db.execute(
        select(FlightClass).where(
            and_(FlightClass.flight_id == flight_id, FlightClass.class_code == req.class_code.value)
        )
    )
    fc = c_res.scalar_one_or_none()
    if not fc:
        raise HTTPException(status_code=404, detail="Flight class not found.")

    # Check if user already on waitlist
    existing_res = await db.execute(
        select(WaitlistEntry).where(
            and_(
                WaitlistEntry.flight_id == flight_id,
                WaitlistEntry.class_code == req.class_code.value,
                WaitlistEntry.user_id == current_user.id,
                WaitlistEntry.status.in_([WaitlistStatus.PENDING.value, WaitlistStatus.OFFERED.value])
            )
        )
    )
    if existing_res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You already have an active waitlist entry for this flight and class.")

    # Priority score: loyalty tier weight (0-4000)
    score = TIER_SCORES.get(current_user.loyalty_tier, 0)

    now = datetime.now(timezone.utc)
    entry = WaitlistEntry(
        id=str(uuid.uuid4()),
        flight_id=flight_id,
        class_code=req.class_code.value,
        user_id=current_user.id,
        passenger_name=req.passenger_name,
        loyalty_tier=current_user.loyalty_tier,
        priority_score=score,
        status=WaitlistStatus.PENDING.value,
        created_at=now
    )
    db.add(entry)

    await log_system_decision(
        db=db,
        event_type="WAITLIST_JOIN",
        actor_system="FASTAPI",
        actor_id=current_user.id,
        entity_type="WAITLIST_ENTRY",
        entity_id=entry.id,
        rule_applied="LOYALTY_TIER_PRIORITY_WEIGHTING",
        decision_metadata={
            "flight_number": flight.flight_number,
            "loyalty_tier": current_user.loyalty_tier,
            "priority_score": score
        }
    )

    # Calculate position among active waitlist entries for this flight and class
    ordered_q = select(WaitlistEntry).where(
        and_(
            WaitlistEntry.flight_id == flight_id,
            WaitlistEntry.class_code == req.class_code.value,
            WaitlistEntry.status.in_([WaitlistStatus.PENDING.value, WaitlistStatus.OFFERED.value])
        )
    ).order_by(WaitlistEntry.priority_score.desc(), WaitlistEntry.created_at.asc())
    all_active = (await db.execute(ordered_q)).scalars().all()
    position = 1
    for idx, e in enumerate(all_active, 1):
        if e.id == entry.id:
            position = idx
            break

    await db.commit()
    await db.refresh(entry)

    return WaitlistEntryResponse(
        id=entry.id,
        flight_id=entry.flight_id,
        class_code=SeatClassCode(entry.class_code),
        passenger_name=entry.passenger_name,
        loyalty_tier=LoyaltyTier(entry.loyalty_tier),
        priority_score=entry.priority_score,
        status=WaitlistStatus(entry.status),
        position=position,
        claim_deadline=entry.claim_deadline,
        created_at=entry.created_at
    )

@router.get("/flights/{flight_id}", response_model=List[WaitlistEntryResponse])
async def get_flight_waitlist(
    flight_id: str,
    class_code: SeatClassCode,
    db: AsyncSession = Depends(get_db)
):
    q = select(WaitlistEntry).where(
        and_(WaitlistEntry.flight_id == flight_id, WaitlistEntry.class_code == class_code.value)
    ).order_by(WaitlistEntry.priority_score.desc(), WaitlistEntry.created_at.asc())

    entries = (await db.execute(q)).scalars().all()
    return [
        WaitlistEntryResponse(
            id=e.id,
            flight_id=e.flight_id,
            class_code=SeatClassCode(e.class_code),
            passenger_name=e.passenger_name,
            loyalty_tier=LoyaltyTier(e.loyalty_tier),
            priority_score=e.priority_score,
            status=WaitlistStatus(e.status),
            position=idx,
            claim_deadline=e.claim_deadline,
            created_at=e.created_at
        )
        for idx, e in enumerate(entries, 1)
    ]

@router.get("/user/current-offer")
async def get_user_current_offer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns any active waitlist offer for the user."""
    res = await db.execute(
        select(WaitlistEntry, Flight)
        .join(Flight, WaitlistEntry.flight_id == Flight.id)
        .where(
            and_(
                WaitlistEntry.user_id == current_user.id,
                WaitlistEntry.status == WaitlistStatus.OFFERED.value
            )
        )
    )
    row = res.first()
    if not row:
        return {"has_offer": False}
    entry, flight = row
    return {
        "has_offer": True,
        "entry_id": entry.id,
        "flight_id": flight.id,
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "class_code": entry.class_code,
        "claim_deadline": entry.claim_deadline.isoformat() if entry.claim_deadline else None
    }

@router.post("/{entry_id}/claim")
async def claim_promoted_seat(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Passenger claims an offered waitlist promotion within the claim window."""
    entry_res = await db.execute(
        select(WaitlistEntry).where(WaitlistEntry.id == entry_id).with_for_update()
    )
    entry = entry_res.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found.")

    if entry.user_id != current_user.id and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized.")

    if entry.status != WaitlistStatus.OFFERED.value:
        raise HTTPException(status_code=400, detail=f"Cannot claim entry in status: {entry.status}.")

    now = datetime.now(timezone.utc)
    deadline = entry.claim_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if now > deadline:
        entry.status = WaitlistStatus.EXPIRED.value
        await db.commit()
        raise HTTPException(status_code=410, detail="Offer claim window has expired.")

    entry.status = WaitlistStatus.CLAIMED.value
    await log_system_decision(
        db=db,
        event_type="WAITLIST_OFFER_CLAIMED",
        actor_system="FASTAPI",
        actor_id=current_user.id,
        entity_type="WAITLIST_ENTRY",
        entity_id=entry.id,
        rule_applied="CLAIM_WITHIN_2H_WINDOW",
        decision_metadata={"flight_id": entry.flight_id, "class_code": entry.class_code}
    )
    await db.commit()
    return {"message": "Waitlist offer claimed successfully! Seat reserved.", "entry_id": entry.id, "status": "CLAIMED"}

@router.post("/{entry_id}/decline")
async def decline_waitlist_offer(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Passenger declines an offered waitlist promotion, releasing it to next in line."""
    entry_res = await db.execute(
        select(WaitlistEntry).where(WaitlistEntry.id == entry_id).with_for_update()
    )
    entry = entry_res.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found.")

    if entry.user_id != current_user.id and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized.")

    entry.status = "DECLINED"
    await log_system_decision(
        db=db,
        event_type="WAITLIST_OFFER_DECLINED",
        actor_system="FASTAPI",
        actor_id=current_user.id,
        entity_type="WAITLIST_ENTRY",
        entity_id=entry.id,
        rule_applied="PASSENGER_DECLINE_REASSIGN_NEXT",
        decision_metadata={"flight_id": entry.flight_id, "class_code": entry.class_code}
    )
    await db.commit()
    return {"message": "Waitlist offer declined successfully.", "entry_id": entry.id, "status": "DECLINED"}
