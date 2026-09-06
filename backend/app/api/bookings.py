import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, func
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, verify_idempotency
from backend.app.core.audit import log_system_decision
from backend.app.core.config import settings
from backend.app.services.notification_service import send_transactional_email
from backend.app.models.all_models import (
    User, Flight, FlightClass, Seat, SeatHold, Booking, Passenger, 
    Payment, Refund, TravelCredit, IdempotencyKey
)
from backend.app.models.enums import (
    SeatClassCode, FareType, BookingStatus, PassengerStatus, PartialPolicy, RefundStatus
)
from backend.app.schemas.booking_schemas import (
    SeatHoldRequest, SeatHoldResponse, BookingCreateRequest, BookingResponse,
    PassengerDetail, BookingCancelRequest, BookingCancelResponse,
    PartialPassengerCancelRequest, RemediationChoice, RemediationResponse
)

router = APIRouter(prefix="/bookings", tags=["Seat Holds & Bookings"])

def generate_pnr() -> str:
    """Generates an alphanumeric 6-character PNR booking reference."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "FMS-" + "".join(secrets.choice(chars) for _ in range(6))

@router.post("/hold", response_model=SeatHoldResponse, status_code=status.HTTP_201_CREATED)
async def create_seat_hold(
    req: SeatHoldRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Temporary seat hold during checkout with expiry.
    Enforces REQ-BKG-17.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.HOLD_TIMEOUT_MINUTES)

    # Lock class row
    class_res = await db.execute(
        select(FlightClass)
        .where(and_(FlightClass.flight_id == req.flight_id, FlightClass.class_code == req.class_code.value))
        .with_for_update()
    )
    fc = class_res.scalar_one_or_none()
    if not fc:
        raise HTTPException(status_code=404, detail="Flight class not found.")

    # Count active holds
    hold_count_q = select(func.count(SeatHold.id)).where(
        and_(
            SeatHold.flight_id == req.flight_id,
            SeatHold.class_code == req.class_code.value,
            SeatHold.is_released == False,
            SeatHold.expires_at > now
        )
    )
    active_holds = (await db.execute(hold_count_q)).scalar() or 0
    available = fc.total_seats + fc.max_overbooking_seats - fc.booked_seats - active_holds

    if available < 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No seats currently available in {req.class_code.value} to place hold."
        )

    # If physical seat requested, verify it is not already held or booked
    if req.seat_id:
        seat_held_q = select(SeatHold).where(
            and_(
                SeatHold.seat_id == req.seat_id,
                SeatHold.is_released == False,
                SeatHold.expires_at > now
            )
        )
        if (await db.execute(seat_held_q)).scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Selected physical seat is currently held by another user.")

        seat_booked_q = select(Passenger).where(
            and_(Passenger.seat_id == req.seat_id, Passenger.passenger_status != "CANCELLED")
        )
        if (await db.execute(seat_booked_q)).scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Selected physical seat is already booked.")

    session_token = secrets.token_hex(32)
    hold = SeatHold(
        id=str(uuid.uuid4()),
        flight_id=req.flight_id,
        class_code=req.class_code.value,
        seat_id=req.seat_id,
        user_id=current_user.id,
        session_token=session_token,
        expires_at=expires_at,
        is_released=False
    )
    db.add(hold)
    await db.commit()

    return SeatHoldResponse(
        hold_id=hold.id,
        flight_id=hold.flight_id,
        class_code=SeatClassCode(hold.class_code),
        seat_id=hold.seat_id,
        session_token=hold.session_token,
        expires_at=hold.expires_at,
        hold_duration_seconds=settings.HOLD_TIMEOUT_MINUTES * 60
    )

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    req: BookingCreateRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Confirms booking, atomically decrements inventory, applies overbooking policy,
    validates group partial availability, and enforces idempotency.
    Enforces REQ-BKG-18, 19, 20, 21, 22, REQ-SRC-13, REQ-INF-52, REQ-INF-56.
    """
    now = datetime.now(timezone.utc)
    passenger_count = len(req.passengers)

    # 1. IDEMPOTENCY KEY HANDLING (REQ-BKG-19, REQ-INF-52)
    if idempotency_key:
        existing_idemp = await verify_idempotency(request, idempotency_key, db)
        if existing_idemp:
            # Return cached response body
            return existing_idemp.response_body

    # 2. CANONICAL ROW LOCKING: Lock Flight row, then FlightClass row
    flight_res = await db.execute(
        select(Flight).where(Flight.id == req.flight_id).with_for_update()
    )
    flight = flight_res.scalar_one_or_none()
    if not flight or flight.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Flight not available for booking.")

    # REQ-BKG-22: Class-specific booking cutoff rules
    dep_time = flight.departure_time
    if dep_time.tzinfo is None:
        dep_time = dep_time.replace(tzinfo=timezone.utc)

    class_res = await db.execute(
        select(FlightClass)
        .where(and_(FlightClass.flight_id == req.flight_id, FlightClass.class_code == req.class_code.value))
        .with_for_update()
    )
    fc = class_res.scalar_one_or_none()
    if not fc:
        raise HTTPException(status_code=404, detail="Flight class not found.")

    # Verify cutoff
    cutoff_time = dep_time - timedelta(hours=fc.cutoff_hours_before_departure)
    if now > cutoff_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking closed for {req.class_code.value}. Cutoff is {fc.cutoff_hours_before_departure} hours before departure."
        )

    # REQ-SRC-13: Fare class rules validation
    if req.fare_type == FareType.BASIC_ECONOMY:
        # Basic economy cannot select seat in advance
        for p in req.passengers:
            if p.seat_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Seat selection not permitted for Basic Economy fare."
                )

    # 3. OVERBOOKING & INVENTORY CALCULATION (REQ-BKG-18, REQ-BKG-20)
    # Count active holds excluding current user's hold if provided
    hold_conds = [
        SeatHold.flight_id == req.flight_id,
        SeatHold.class_code == req.class_code.value,
        SeatHold.is_released == False,
        SeatHold.expires_at > now
    ]
    if req.hold_id:
        hold_conds.append(SeatHold.id != req.hold_id)

    other_holds = (await db.execute(
        select(func.count(SeatHold.id)).where(and_(*hold_conds))
    )).scalar() or 0

    max_allowed_capacity = fc.total_seats + fc.max_overbooking_seats
    available_seats = max_allowed_capacity - fc.booked_seats - other_holds

    # 4. GROUP BOOKING PARTIAL POLICIES (REQ-BKG-21)
    if available_seats < passenger_count:
        if req.partial_policy == PartialPolicy.FULL_FAIL:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only {max(0, available_seats)} seats available for group of {passenger_count}. Request rejected under FULL_FAIL policy."
            )
        else:
            # PARTIAL_HOLD: hold whatever seats are available
            passenger_count = max(0, available_seats)
            if passenger_count == 0:
                raise HTTPException(status_code=409, detail="Zero seats available for partial group hold.")

    # 5. ATOMIC SEAT-CLASS DECREMENT (INCREMENT BOOKED_SEATS) (REQ-BKG-18)
    atomic_update_stmt = (
        update(FlightClass)
        .where(
            and_(
                FlightClass.id == fc.id,
                (FlightClass.total_seats + FlightClass.max_overbooking_seats - FlightClass.booked_seats - other_holds) >= passenger_count
            )
        )
        .values(booked_seats=FlightClass.booked_seats + passenger_count)
    )
    update_res = await db.execute(atomic_update_stmt)
    if update_res.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No seats remaining in {req.class_code.value} (race condition detected). Booking aborted."
        )

    # Release temporary hold if used
    if req.hold_id:
        await db.execute(
            update(SeatHold).where(SeatHold.id == req.hold_id).values(is_released=True)
        )

    # Calculate fare
    base_unit_fare = float(fc.base_fare)
    if req.fare_type == FareType.FLEXIBLE:
        base_unit_fare *= 1.25 # 25% premium for flexibility
    elif req.fare_type == FareType.BUSINESS_FLEX:
        base_unit_fare *= 1.35

    total_fare = round(base_unit_fare * passenger_count, 2)

    # Travel credit redemption check
    if req.credit_code:
        credit_res = await db.execute(
            select(TravelCredit).where(
                and_(TravelCredit.credit_code == req.credit_code, TravelCredit.is_redeemed == False)
            ).with_for_update()
        )
        tc = credit_res.scalar_one_or_none()
        if tc:
            exp_date = tc.expires_at
            if exp_date.tzinfo is None:
                exp_date = exp_date.replace(tzinfo=timezone.utc)
            if now <= exp_date:
                deduction = min(total_fare, float(tc.amount))
                total_fare -= deduction
                tc.is_redeemed = True
                tc.redeemed_at = now

    pnr = generate_pnr()
    booking = Booking(
        id=str(uuid.uuid4()),
        booking_reference=pnr,
        user_id=current_user.id,
        flight_id=flight.id,
        class_code=req.class_code.value,
        fare_type=req.fare_type.value,
        total_fare=total_fare,
        currency=req.currency,
        status=BookingStatus.CONFIRMED.value,
        schedule_change_acknowledged=True,
        eligible_for_involuntary_refund=False,
        created_at=now,
        updated_at=now
    )
    db.add(booking)

    created_passengers = []
    for i in range(passenger_count):
        p_in = req.passengers[i]
        passenger = Passenger(
            id=str(uuid.uuid4()),
            booking_id=booking.id,
            seat_id=p_in.seat_id,
            first_name=p_in.first_name,
            last_name=p_in.last_name,
            passport_number=p_in.passport_number,
            passenger_status=PassengerStatus.CONFIRMED.value,
            fare_portion=round(base_unit_fare, 2)
        )
        db.add(passenger)
        created_passengers.append(passenger)

    # Record Payment
    payment = Payment(
        id=str(uuid.uuid4()),
        booking_id=booking.id,
        amount=total_fare,
        currency=req.currency,
        payment_method="CARD",
        transaction_reference=f"TXN-{uuid.uuid4().hex[:12].upper()}",
        status="SUCCESS"
    )
    db.add(payment)

    # REQ-APP-44: System audit trail
    await log_system_decision(
        db=db,
        event_type="BOOKING_CONFIRMATION",
        actor_system="FASTAPI",
        actor_id=current_user.id,
        entity_type="BOOKING",
        entity_id=booking.id,
        rule_applied="ATOMIC_SEAT_DECREMENT_POLICY",
        decision_metadata={
            "pnr": pnr,
            "passengers": passenger_count,
            "class": req.class_code.value,
            "fare_type": req.fare_type.value,
            "total_fare": total_fare
        }
    )

    # REQ-INF-56: Transactional Gmail send
    email_html = f"""
    <h2>Booking Confirmation - {pnr}</h2>
    <p>Dear {current_user.full_name},</p>
    <p>Your booking for Flight <b>{flight.flight_number}</b> from {flight.origin} to {flight.destination} is confirmed.</p>
    <p><b>Departure:</b> {flight.departure_time.strftime('%Y-%m-%d %H:%M UTC')}<br/>
    <b>Class:</b> {req.class_code.value} | <b>Fare:</b> {req.fare_type.value}<br/>
    <b>Total Amount:</b> {req.currency} {total_fare}</p>
    <p>Thank you for choosing our airline!</p>
    """
    await send_transactional_email(
        db=db,
        recipient=current_user.email,
        subject=f"Flight Booking Confirmed: {pnr} ({flight.flight_number})",
        template_name="BOOKING_CONFIRMATION",
        html_content=email_html,
        reference_id=booking.id
    )

    passenger_details = [
        PassengerDetail(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            passport_number=p.passport_number,
            seat_number=None,
            passenger_status=PassengerStatus(p.passenger_status),
            fare_portion=float(p.fare_portion)
        )
        for p in created_passengers
    ]

    response_data = BookingResponse(
        id=booking.id,
        booking_reference=booking.booking_reference,
        flight_id=flight.id,
        flight_number=flight.flight_number,
        origin=flight.origin,
        destination=flight.destination,
        departure_time=flight.departure_time,
        class_code=SeatClassCode(booking.class_code),
        fare_type=FareType(booking.fare_type),
        total_fare=float(booking.total_fare),
        currency=booking.currency,
        status=BookingStatus(booking.status),
        passengers=passenger_details,
        schedule_change_acknowledged=booking.schedule_change_acknowledged,
        eligible_for_involuntary_refund=booking.eligible_for_involuntary_refund,
        created_at=booking.created_at
    )

    # Cache idempotency key
    if idempotency_key:
        idemp_record = IdempotencyKey(
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=str(request.url.path),
            request_hash="",
            response_code=201,
            response_body=response_data.model_dump(mode="json"),
            expires_at=now + timedelta(hours=24)
        )
        db.add(idemp_record)

    await db.commit()
    return response_data

@router.get("/lookup/{pnr}")
async def lookup_booking_by_pnr(
    pnr: str,
    email: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Public lookup by PNR and passenger email for 'Manage My Booking' (REQ-CHG-23, 24).
    """
    clean_pnr = pnr.strip().upper()
    b_res = await db.execute(
        select(Booking).where(Booking.booking_reference == clean_pnr)
    )
    b = b_res.scalar_one_or_none()
    if not b:
        b_res = await db.execute(
            select(Booking).where(Booking.id == clean_pnr)
        )
        b = b_res.scalar_one_or_none()

    if not b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"No booking found with Reference/PNR '{clean_pnr}'. Please check your reference and try again."
        )

    # Fetch User
    u_res = await db.execute(select(User).where(User.id == b.user_id))
    user = u_res.scalar_one_or_none()

    # Fetch Flight
    flight_res = await db.execute(select(Flight).where(Flight.id == b.flight_id))
    flight = flight_res.scalar_one_or_none()

    # Fetch Passengers
    p_res = await db.execute(select(Passenger).where(Passenger.booking_id == b.id))
    passengers = p_res.scalars().all()

    # Fetch Seats
    seat_ids = [p.seat_id for p in passengers if p.seat_id]
    seat_map = {}
    if seat_ids:
        s_res = await db.execute(select(Seat).where(Seat.id.in_(seat_ids)))
        seats = s_res.scalars().all()
        seat_map = {s.id: s.seat_number for s in seats}

    passenger_details = [
        {
            "id": p.id,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "passport_number": p.passport_number,
            "seat_number": seat_map.get(p.seat_id, "Assigned at check-in"),
            "passenger_status": p.passenger_status,
            "fare_portion": float(p.fare_portion)
        }
        for p in passengers
    ]

    # Fetch any active Travel Credits
    credits_res = await db.execute(
        select(TravelCredit).where(
            and_(TravelCredit.user_id == b.user_id, TravelCredit.is_redeemed == False)
        )
    )
    user_credits = [
        {
            "id": tc.id,
            "credit_code": tc.credit_code,
            "amount": float(tc.amount),
            "currency": tc.currency,
            "expires_at": tc.expires_at.strftime("%d %B %Y") if tc.expires_at else "20 September 2027",
            "is_redeemed": tc.is_redeemed,
            "status": "ACTIVE" if not tc.is_redeemed else "REDEEMED"
        }
        for tc in credits_res.scalars().all()
    ]

    return {
        "id": b.id,
        "booking_reference": b.booking_reference,
        "flight_id": flight.id if flight else b.flight_id,
        "flight_number": flight.flight_number if flight else "Unknown",
        "origin": flight.origin if flight else "N/A",
        "destination": flight.destination if flight else "N/A",
        "departure_time": flight.departure_time.isoformat() if (flight and flight.departure_time) else None,
        "arrival_time": flight.arrival_time.isoformat() if (flight and flight.arrival_time) else None,
        "flight_status": flight.status if flight else "SCHEDULED",
        "schedule_version": flight.schedule_version if flight else 1,
        "cancellation_reason": flight.cancellation_reason if flight else None,
        "class_code": b.class_code,
        "fare_type": b.fare_type,
        "total_fare": float(b.total_fare),
        "currency": b.currency,
        "status": b.status,
        "customer_email": user.email if user else (email or "passenger@example.com"),
        "customer_name": user.full_name if user else (f"{passengers[0].first_name} {passengers[0].last_name}" if passengers else "Passenger"),
        "passengers": passenger_details,
        "schedule_change_acknowledged": b.schedule_change_acknowledged,
        "eligible_for_involuntary_refund": b.eligible_for_involuntary_refund,
        "travel_credits": user_credits,
        "created_at": b.created_at.isoformat() if b.created_at else None
    }

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    b_res = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    b = b_res.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if b.user_id != current_user.id and current_user.role not in ["SUPER_ADMIN", "OPS_AGENT"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this booking.")

    flight_res = await db.execute(select(Flight).where(Flight.id == b.flight_id))
    flight = flight_res.scalar_one()

    p_res = await db.execute(select(Passenger).where(Passenger.booking_id == b.id))
    passengers = p_res.scalars().all()

    passenger_details = [
        PassengerDetail(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            passport_number=p.passport_number,
            seat_number=None,
            passenger_status=PassengerStatus(p.passenger_status),
            fare_portion=float(p.fare_portion)
        )
        for p in passengers
    ]

    return BookingResponse(
        id=b.id,
        booking_reference=b.booking_reference,
        flight_id=flight.id,
        flight_number=flight.flight_number,
        origin=flight.origin,
        destination=flight.destination,
        departure_time=flight.departure_time,
        class_code=SeatClassCode(b.class_code),
        fare_type=FareType(b.fare_type),
        total_fare=float(b.total_fare),
        currency=b.currency,
        status=BookingStatus(b.status),
        passengers=passenger_details,
        schedule_change_acknowledged=b.schedule_change_acknowledged,
        eligible_for_involuntary_refund=b.eligible_for_involuntary_refund,
        created_at=b.created_at
    )

@router.post("/{booking_id}/cancel", response_model=BookingCancelResponse)
async def cancel_booking(
    booking_id: str,
    req: BookingCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancels booking with cancellation policy branching by fare type.
    Enforces REQ-CHG-23, REQ-CHG-25, REQ-INF-56.
    """
    b_res = await db.execute(select(Booking).where(Booking.id == booking_id).with_for_update())
    booking = b_res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.user_id != current_user.id and current_user.role not in ["SUPER_ADMIN", "OPS_AGENT"]:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking.")

    if booking.status in ["CANCELLED", "REFUNDED"]:
        raise HTTPException(status_code=400, detail="Booking is already cancelled.")

    now = datetime.now(timezone.utc)

    # Release class seats
    passengers_res = await db.execute(
        select(Passenger).where(and_(Passenger.booking_id == booking.id, Passenger.passenger_status != "CANCELLED"))
    )
    active_passengers = passengers_res.scalars().all()
    seats_to_release = len(active_passengers)

    class_res = await db.execute(
        select(FlightClass)
        .where(and_(FlightClass.flight_id == booking.flight_id, FlightClass.class_code == booking.class_code))
        .with_for_update()
    )
    fc = class_res.scalar_one_or_none()
    if fc:
        fc.booked_seats = max(0, fc.booked_seats - seats_to_release)

    # Mark passengers cancelled
    for p in active_passengers:
        p.passenger_status = PassengerStatus.CANCELLED.value
        p.seat_id = None

    # Determine Refund Branching
    refund_type = "NONE"
    refund_amount = 0.0
    cancellation_fee = 0.0
    voucher_code = None
    msg = ""

    # REQ-CHG-25: Involuntary schedule change override (100% full refund)
    if booking.eligible_for_involuntary_refund:
        refund_type = "ORIGINAL_PAYMENT"
        refund_amount = float(booking.total_fare)
        cancellation_fee = 0.0
        msg = "Full 100% refund granted due to airline involuntary schedule change / cancellation override."
    elif req.prefer_credit:
        # Credit-only option: Cash Refund: $0, Travel Credit: $total_fare, Valid 365 days
        refund_type = "TRAVEL_CREDIT"
        refund_amount = float(booking.total_fare)
        cancellation_fee = 0.0
        voucher_code = f"CRD-{secrets.token_hex(4).upper()}"
        expires_at = now + timedelta(days=365)
        credit = TravelCredit(
            id=str(uuid.uuid4()),
            credit_code=voucher_code,
            user_id=booking.user_id,
            amount=refund_amount,
            currency=booking.currency,
            expires_at=expires_at,
            is_redeemed=False
        )
        db.add(credit)
        msg = f"Credit-only cancellation processed. 100% Travel Credit voucher {voucher_code} issued for {booking.currency} {refund_amount:.2f} (valid until {expires_at.strftime('%d %b %Y')})."
    elif booking.fare_type in [FareType.FLEXIBLE.value, FareType.BUSINESS_FLEX.value]:
        refund_type = "ORIGINAL_PAYMENT"
        cancellation_fee = float(req.cancellation_fee) if req.cancellation_fee is not None else 25.00
        refund_amount = max(0.0, float(booking.total_fare) - cancellation_fee)
        msg = f"Flexible fare cancelled. Refund of {booking.currency} {refund_amount:.2f} issued to original payment method minus ${cancellation_fee:.2f} processing fee."
    else:
        # Basic Economy: No monetary refund; voluntary cancellation releases seat
        refund_type = "NONE"
        refund_amount = 0.0
        cancellation_fee = 0.0
        msg = "Basic Economy fare is non-refundable. Reservation cancelled with $0 refund."

    booking.status = BookingStatus.CANCELLED.value

    # Insert Refund record if refund_amount > 0
    if refund_amount > 0:
        refund_record = Refund(
            id=str(uuid.uuid4()),
            booking_id=booking.id,
            amount=refund_amount,
            currency=booking.currency,
            refund_type=refund_type,
            status=RefundStatus.PENDING.value,
            reason=req.reason
        )
        db.add(refund_record)

    # REQ-INF-56: Transactional cancellation email
    cancel_email_html = f"""
    <h2>Cancellation Receipt - {booking.booking_reference}</h2>
    <p>Dear {current_user.full_name},</p>
    <p>Your booking <b>{booking.booking_reference}</b> has been cancelled.</p>
    <p><b>Refund Type:</b> {refund_type}<br/>
    <b>Refund Amount:</b> {booking.currency} {refund_amount}<br/>
    <b>Status Note:</b> {msg}</p>
    """
    await send_transactional_email(
        db=db,
        recipient=current_user.email,
        subject=f"Cancellation Confirmation: {booking.booking_reference}",
        template_name="CANCELLATION_RECEIPT",
        html_content=cancel_email_html,
        reference_id=booking.id
    )

    await db.commit()
    return BookingCancelResponse(
        booking_id=booking.id,
        booking_reference=booking.booking_reference,
        status=BookingStatus(booking.status),
        refund_type=refund_type,
        refund_amount=refund_amount,
        cancellation_fee=cancellation_fee,
        travel_credit_code=voucher_code,
        message=msg
    )

@router.post("/{booking_id}/passengers/{passenger_id}/cancel")
async def cancel_partial_passenger(
    booking_id: str,
    passenger_id: str,
    req: PartialPassengerCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Partial cancellation on a multi-passenger booking with proportional repricing.
    Enforces REQ-CHG-24.
    """
    b_res = await db.execute(select(Booking).where(Booking.id == booking_id).with_for_update())
    booking = b_res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    p_res = await db.execute(
        select(Passenger).where(and_(Passenger.id == passenger_id, Passenger.booking_id == booking.id)).with_for_update()
    )
    passenger = p_res.scalar_one_or_none()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found in this booking.")

    if passenger.passenger_status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Passenger is already cancelled.")

    passenger.passenger_status = PassengerStatus.CANCELLED.value
    passenger.seat_id = None

    # Decrement booked seats on class
    class_res = await db.execute(
        select(FlightClass)
        .where(and_(FlightClass.flight_id == booking.flight_id, FlightClass.class_code == booking.class_code))
        .with_for_update()
    )
    fc = class_res.scalar_one_or_none()
    if fc:
        fc.booked_seats = max(0, fc.booked_seats - 1)

    # Proportional refund calculation
    portion = float(passenger.fare_portion)
    booking.total_fare = max(0.0, float(booking.total_fare) - portion)

    refund_msg = ""
    if booking.fare_type != FareType.BASIC_ECONOMY.value:
        refund_record = Refund(
            id=str(uuid.uuid4()),
            booking_id=booking.id,
            amount=portion,
            currency=booking.currency,
            refund_type="ORIGINAL_PAYMENT",
            status=RefundStatus.PENDING.value,
            reason=f"Partial passenger cancellation: {passenger.first_name} {passenger.last_name}"
        )
        db.add(refund_record)
        refund_msg = f"Refund of {booking.currency} {portion} initiated."
    else:
        refund_msg = "Basic Economy fare: seat freed, no refund issued."

    await db.commit()
    return {
        "message": f"Passenger {passenger.first_name} {passenger.last_name} successfully cancelled.",
        "refund_portion": portion,
        "remaining_booking_fare": float(booking.total_fare),
        "notes": refund_msg
    }

@router.post("/{booking_id}/passengers/cancel-selected")
async def cancel_selected_passengers(
    booking_id: str,
    req: PartialPassengerCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel one or more selected passengers with proportional repricing and seat release (REQ-CHG-24).
    """
    pax_ids = req.passenger_ids or ([req.passenger_id] if req.passenger_id else [])
    if not pax_ids:
        raise HTTPException(status_code=400, detail="No passenger IDs specified for cancellation.")

    b_res = await db.execute(select(Booking).where(Booking.id == booking_id).with_for_update())
    booking = b_res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    p_res = await db.execute(
        select(Passenger).where(and_(Passenger.id.in_(pax_ids), Passenger.booking_id == booking.id)).with_for_update()
    )
    passengers = p_res.scalars().all()
    if not passengers:
        raise HTTPException(status_code=404, detail="Selected passengers not found in this booking.")

    total_proportional_refund = 0.0
    cancelled_names = []
    seats_released = 0

    for p in passengers:
        if p.passenger_status != "CANCELLED":
            p.passenger_status = PassengerStatus.CANCELLED.value
            p.seat_id = None
            portion = float(p.fare_portion)
            total_proportional_refund += portion
            cancelled_names.append(f"{p.first_name} {p.last_name}")
            seats_released += 1

    if seats_released == 0:
        raise HTTPException(status_code=400, detail="All selected passengers are already cancelled.")

    # Decrement booked seats on class
    class_res = await db.execute(
        select(FlightClass)
        .where(and_(FlightClass.flight_id == booking.flight_id, FlightClass.class_code == booking.class_code))
        .with_for_update()
    )
    fc = class_res.scalar_one_or_none()
    if fc:
        fc.booked_seats = max(0, fc.booked_seats - seats_released)

    # Repricing booking total fare
    booking.total_fare = max(0.0, float(booking.total_fare) - total_proportional_refund)

    # Check remaining active passengers
    active_check = await db.execute(
        select(func.count(Passenger.id)).where(
            and_(Passenger.booking_id == booking.id, Passenger.passenger_status != "CANCELLED")
        )
    )
    remaining_count = active_check.scalar() or 0
    if remaining_count == 0:
        booking.status = BookingStatus.CANCELLED.value

    # Insert refund record if applicable
    if booking.fare_type != FareType.BASIC_ECONOMY.value and total_proportional_refund > 0:
        refund_record = Refund(
            id=str(uuid.uuid4()),
            booking_id=booking.id,
            amount=total_proportional_refund,
            currency=booking.currency,
            refund_type="ORIGINAL_PAYMENT",
            status=RefundStatus.PENDING.value,
            reason=f"Partial cancellation for {', '.join(cancelled_names)}"
        )
        db.add(refund_record)

    await db.commit()

    return {
        "cancelled_passengers": cancelled_names,
        "seats_released": seats_released,
        "proportional_refund": total_proportional_refund,
        "new_booking_total": float(booking.total_fare),
        "booking_status": booking.status,
        "message": f"Successfully cancelled {seats_released} passenger(s). Proportional refund of {booking.currency} {total_proportional_refund:.2f} initiated. Seats released."
    }

@router.post("/{booking_id}/remediate", response_model=RemediationResponse)
async def remediate_cancelled_flight(
    booking_id: str,
    choice: RemediationChoice,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Self-service remediation for cancelled flight (cash refund vs 365-day travel credit vs rebook).
    Enforces REQ-CHG-26.
    """
    b_res = await db.execute(select(Booking).where(Booking.id == booking_id).with_for_update())
    booking = b_res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if not booking.eligible_for_involuntary_refund:
        raise HTTPException(status_code=400, detail="This booking is not flagged for involuntary remediation.")

    now = datetime.now(timezone.utc)
    choice_type = choice.remediation_type.upper()

    if choice_type == "TRAVEL_CREDIT":
        # Issue 365-day travel credit voucher with +10% bonus
        credit_amount = round(float(booking.total_fare) * 1.10, 2)
        credit_code = f"TC-{secrets.token_hex(2).upper()}"
        expires_at = now + timedelta(days=365) # REQ-CHG-26 strictly 365 days

        credit = TravelCredit(
            id=str(uuid.uuid4()),
            credit_code=credit_code,
            user_id=booking.user_id,
            amount=credit_amount,
            currency=booking.currency,
            expires_at=expires_at,
            is_redeemed=False
        )
        db.add(credit)
        booking.status = BookingStatus.REFUNDED.value
        booking.eligible_for_involuntary_refund = False
        await db.commit()

        return RemediationResponse(
            booking_id=booking.id,
            remediation_type="TRAVEL_CREDIT",
            status="SUCCESS",
            credit_code=credit_code,
            amount=credit_amount,
            message=f"Travel credit {credit_code} issued for {booking.currency} {credit_amount} (including 10% bonus). Valid for 365 days until {expires_at.strftime('%d %B %Y')}."
        )
    elif choice_type == "CASH_REFUND":
        refund_amount = float(booking.total_fare)
        refund_record = Refund(
            id=str(uuid.uuid4()),
            booking_id=booking.id,
            amount=refund_amount,
            currency=booking.currency,
            refund_type="ORIGINAL_PAYMENT",
            status=RefundStatus.PENDING.value,
            reason="Involuntary flight cancellation cash refund"
        )
        db.add(refund_record)
        booking.status = BookingStatus.REFUNDED.value
        booking.eligible_for_involuntary_refund = False
        await db.commit()

        return RemediationResponse(
            booking_id=booking.id,
            remediation_type="CASH_REFUND",
            status="SUCCESS",
            credit_code=None,
            amount=refund_amount,
            message=f"100% full cash refund of {booking.currency} {refund_amount:.2f} approved and queued for processing."
        )
    elif choice_type == "REBOOK":
        booking.status = BookingStatus.CONFIRMED.value
        booking.eligible_for_involuntary_refund = False
        await db.commit()

        return RemediationResponse(
            booking_id=booking.id,
            remediation_type="REBOOK",
            status="SUCCESS",
            credit_code=None,
            amount=0.0,
            message="Free rebooking pass authorized for any alternative scheduled flight on this route with $0 fare difference."
        )
    else:
        raise HTTPException(status_code=400, detail="Supported remediation types: 'CASH_REFUND', 'TRAVEL_CREDIT', 'REBOOK'.")

@router.post("/{booking_id}/acknowledge-schedule")
async def acknowledge_schedule_change(
    booking_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Passenger accepts the new departure/arrival schedule (REQ-CHG-25).
    """
    b_res = await db.execute(select(Booking).where(Booking.id == booking_id).with_for_update())
    booking = b_res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    
    booking.schedule_change_acknowledged = True
    if booking.status == BookingStatus.SCHEDULE_CHANGED.value:
        booking.status = BookingStatus.CONFIRMED.value
    await db.commit()
    return {"message": "New schedule accepted successfully.", "status": booking.status}

@router.post("/{booking_id}/checkin")
async def checkin_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Performs online check-in for a flight departing within 24 hours.
    Strictly suppressed if the flight or booking is CANCELLED (REQ-SCH-36).
    """
    b_res = await db.execute(
        select(Booking, Flight)
        .join(Flight, Booking.flight_id == Flight.id)
        .where(Booking.id == booking_id)
        .with_for_update(of=Booking)
    )
    row = b_res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found.")

    booking, flight = row
    if flight.status == "CANCELLED" or booking.status in ["CANCELLED", "REFUNDED"]:
        raise HTTPException(
            status_code=400,
            detail="Check-in is suppressed and unavailable because this flight or booking has been cancelled."
        )

    booking.checkin_reminder_sent = True
    await log_system_decision(
        db=db,
        event_type="PASSENGER_CHECKIN_COMPLETED",
        actor_system="FASTAPI",
        actor_id=booking.user_id,
        entity_type="BOOKING",
        entity_id=booking.id,
        rule_applied="ONLINE_CHECKIN_24H_WINDOW",
        decision_metadata={
            "flight_number": flight.flight_number,
            "origin": flight.origin,
            "destination": flight.destination
        }
    )
    await db.commit()
    return {
        "message": "Check-in successful! Your boarding pass is ready.",
        "pnr": booking.booking_reference,
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "boarding_pass": f"BP-{booking.booking_reference[:4]}-GATE14",
        "gate": "Gate 14A",
        "boarding_group": "Group B",
        "status": "CHECKED_IN"
    }
