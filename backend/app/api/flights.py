from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from backend.app.core.database import get_db
from backend.app.models.all_models import Flight, FlightClass, Seat, SeatHold, Passenger
from backend.app.models.enums import FlightStatus, SeatClassCode
from backend.app.schemas.flight_schemas import FlightResponse, FlightClassDetail
from backend.app.schemas.seatmap_schemas import SeatMapLayoutResponse, SeatItem

router = APIRouter(prefix="/flights", tags=["Search & Flight Inventory"])

# Exchange rate table for currency/locale handling (REQ-SRC-16)
CURRENCY_RATES = {
    "USD": 1.0,
    "GBP": 0.78,
    "EUR": 0.92,
    "AED": 3.67
}

@router.get("/search", response_model=List[FlightResponse])
async def search_flights(
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    date: Optional[str] = Query(None, description="Departure date in YYYY-MM-DD"),
    currency: str = Query("USD", description="Currency code: USD, GBP, EUR, AED"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search endpoint returning available seats per class for a given route/date.
    Deducts active unexpired holds to guarantee real-time transactional accuracy.
    Enforces REQ-SRC-12, REQ-SRC-16.
    """
    currency_code = currency.upper()
    rate = CURRENCY_RATES.get(currency_code, 1.0)

    conditions = [
        Flight.origin == origin.upper(),
        Flight.destination == destination.upper(),
        Flight.status != FlightStatus.CANCELLED.value,
        Flight.departure_time > datetime.now(timezone.utc)
    ]
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            conditions.append(func.date(Flight.departure_time) == target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    q = select(Flight).where(and_(*conditions)).order_by(Flight.departure_time.asc())
    flights_res = await db.execute(q)
    flights = flights_res.scalars().all()

    results = []
    now = datetime.now(timezone.utc)

    for f in flights:
        # Load classes for flight
        c_res = await db.execute(select(FlightClass).where(FlightClass.flight_id == f.id))
        classes = c_res.scalars().all()

        class_details = []
        for c in classes:
            # Active unexpired holds calculation
            hold_count_q = select(func.count(SeatHold.id)).where(
                and_(
                    SeatHold.flight_id == f.id,
                    SeatHold.class_code == c.class_code,
                    SeatHold.is_released == False,
                    SeatHold.expires_at > now
                )
            )
            active_holds = (await db.execute(hold_count_q)).scalar() or 0

            # Calculate real-time available seats
            available = max(0, c.total_seats - c.booked_seats - active_holds)
            converted_fare = round(float(c.base_fare) * rate, 2)

            class_details.append(
                FlightClassDetail(
                    id=c.id,
                    class_code=SeatClassCode(c.class_code),
                    total_seats=c.total_seats,
                    booked_seats=c.booked_seats,
                    held_seats=active_holds,
                    available_seats=available,
                    base_fare=converted_fare,
                    overbooking_buffer_pct=c.overbooking_buffer_pct,
                    max_overbooking_seats=c.max_overbooking_seats,
                    cutoff_hours_before_departure=c.cutoff_hours_before_departure
                )
            )

        results.append(
            FlightResponse(
                id=f.id,
                flight_number=f.flight_number,
                origin=f.origin,
                destination=f.destination,
                origin_tz=f.origin_tz,
                destination_tz=f.destination_tz,
                departure_time=f.departure_time,
                arrival_time=f.arrival_time,
                total_capacity=f.total_capacity,
                status=FlightStatus(f.status),
                cancellation_reason=f.cancellation_reason,
                schedule_version=f.schedule_version,
                classes=class_details
            )
        )

    return results

@router.get("/{flight_id}", response_model=FlightResponse)
async def get_flight_details(flight_id: str, db: AsyncSession = Depends(get_db)):
    f_res = await db.execute(select(Flight).where(Flight.id == flight_id))
    f = f_res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Flight not found.")

    c_res = await db.execute(select(FlightClass).where(FlightClass.flight_id == f.id))
    classes = c_res.scalars().all()
    now = datetime.now(timezone.utc)

    class_details = []
    for c in classes:
        hold_count_q = select(func.count(SeatHold.id)).where(
            and_(
                SeatHold.flight_id == f.id,
                SeatHold.class_code == c.class_code,
                SeatHold.is_released == False,
                SeatHold.expires_at > now
            )
        )
        active_holds = (await db.execute(hold_count_q)).scalar() or 0
        available = max(0, c.total_seats - c.booked_seats - active_holds)

        class_details.append(
            FlightClassDetail(
                id=c.id,
                class_code=SeatClassCode(c.class_code),
                total_seats=c.total_seats,
                booked_seats=c.booked_seats,
                held_seats=active_holds,
                available_seats=available,
                base_fare=float(c.base_fare),
                overbooking_buffer_pct=c.overbooking_buffer_pct,
                max_overbooking_seats=c.max_overbooking_seats,
                cutoff_hours_before_departure=c.cutoff_hours_before_departure
            )
        )

    return FlightResponse(
        id=f.id,
        flight_number=f.flight_number,
        origin=f.origin,
        destination=f.destination,
        origin_tz=f.origin_tz,
        destination_tz=f.destination_tz,
        departure_time=f.departure_time,
        arrival_time=f.arrival_time,
        total_capacity=f.total_capacity,
        status=FlightStatus(f.status),
        cancellation_reason=f.cancellation_reason,
        schedule_version=f.schedule_version,
        classes=class_details
    )

@router.get("/{flight_id}/seat-map", response_model=SeatMapLayoutResponse)
async def get_flight_seat_map(flight_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns physical seat map with live occupancy state.
    Enforces REQ-ADM-07.
    """
    f_res = await db.execute(select(Flight).where(Flight.id == flight_id))
    flight = f_res.scalar_one_or_none()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found.")

    seats_res = await db.execute(
        select(Seat).where(Seat.flight_id == flight_id).order_by(Seat.seat_row.asc(), Seat.seat_column.asc())
    )
    all_seats = seats_res.scalars().all()

    now = datetime.now(timezone.utc)

    # Get all currently assigned seat IDs
    assigned_seats_q = select(Passenger.seat_id).where(
        and_(Passenger.seat_id.isnot(None), Passenger.passenger_status != "CANCELLED")
    )
    assigned_seat_ids = set((await db.execute(assigned_seats_q)).scalars().all())

    # Get all active unexpired held seat IDs
    held_seats_q = select(SeatHold.seat_id).where(
        and_(
            SeatHold.flight_id == flight_id,
            SeatHold.seat_id.isnot(None),
            SeatHold.is_released == False,
            SeatHold.expires_at > now
        )
    )
    held_seat_ids = set((await db.execute(held_seats_q)).scalars().all())

    seat_items = []
    for s in all_seats:
        is_booked = (s.id in assigned_seat_ids)
        is_held = (s.id in held_seat_ids)
        is_free = (not is_booked) and (not is_held) and s.is_active
        seat_items.append(
            SeatItem(
                id=s.id,
                seat_number=s.seat_number,
                class_code=SeatClassCode(s.class_code),
                seat_row=s.seat_row,
                seat_column=s.seat_column,
                is_available=is_free,
                is_booked=is_booked,
                is_held=is_held
            )
        )

    return SeatMapLayoutResponse(
        flight_id=flight.id,
        flight_number=flight.flight_number,
        total_seats=len(seat_items),
        seats=seat_items
    )
