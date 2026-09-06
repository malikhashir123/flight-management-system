import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from backend.app.schemas.flight_schemas import FlightCreateRequest, SeatClassAllocation
from backend.app.models.enums import SeatClassCode

def test_flight_capacity_sum_validation_success():
    """REQ-ADM-02, REQ-ADM-03: UK -> Dubai flight departing 05:00 with 100 total capacity (20F, 30B, 50E)."""
    now = datetime.now(timezone.utc)
    req = FlightCreateRequest(
        flight_number="BA105",
        origin="LHR",
        destination="DXB",
        departure_time=now + timedelta(days=1),
        arrival_time=now + timedelta(days=1, hours=7),
        total_capacity=100,
        seat_classes=[
            SeatClassAllocation(class_code=SeatClassCode.FIRST, total_seats=20, base_fare=1500),
            SeatClassAllocation(class_code=SeatClassCode.BUSINESS, total_seats=30, base_fare=750),
            SeatClassAllocation(class_code=SeatClassCode.ECONOMY, total_seats=50, base_fare=250),
        ]
    )
    assert req.total_capacity == 100
    assert sum(c.total_seats for c in req.seat_classes) == 100

def test_flight_capacity_sum_mismatch_fails():
    """REQ-ADM-03: Validation that seat class totals sum exactly to declared aircraft capacity."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc:
        FlightCreateRequest(
            flight_number="BA105",
            origin="LHR",
            destination="DXB",
            departure_time=now + timedelta(days=1),
            arrival_time=now + timedelta(days=1, hours=7),
            total_capacity=100,
            seat_classes=[
                SeatClassAllocation(class_code=SeatClassCode.FIRST, total_seats=20, base_fare=1500),
                SeatClassAllocation(class_code=SeatClassCode.BUSINESS, total_seats=30, base_fare=750),
                SeatClassAllocation(class_code=SeatClassCode.ECONOMY, total_seats=40, base_fare=250), # Sum = 90 != 100
            ]
        )
    assert "Seat class totals sum (90) must equal declared aircraft capacity (100)" in str(exc.value)

def test_reject_negative_or_zero_seats():
    """REQ-ADM-04: Reject seat class allocation with negative or zero values."""
    with pytest.raises(ValidationError):
        SeatClassAllocation(class_code=SeatClassCode.ECONOMY, total_seats=-5, base_fare=250)

    with pytest.raises(ValidationError):
        SeatClassAllocation(class_code=SeatClassCode.ECONOMY, total_seats=0, base_fare=250)

def test_reject_identical_origin_destination():
    """REQ-ADM-01: Origin and destination cannot be identical."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc:
        FlightCreateRequest(
            flight_number="BA105",
            origin="LHR",
            destination="LHR",
            departure_time=now + timedelta(days=1),
            arrival_time=now + timedelta(days=1, hours=7),
            total_capacity=100,
            seat_classes=[
                SeatClassAllocation(class_code=SeatClassCode.ECONOMY, total_seats=100, base_fare=250),
            ]
        )
    assert "Origin and destination airports cannot be identical" in str(exc.value)

def test_reject_arrival_before_departure():
    """REQ-ADM-01: Arrival time must be after departure time."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc:
        FlightCreateRequest(
            flight_number="BA105",
            origin="LHR",
            destination="DXB",
            departure_time=now + timedelta(days=1, hours=8),
            arrival_time=now + timedelta(days=1, hours=5), # Arrival before departure
            total_capacity=100,
            seat_classes=[
                SeatClassAllocation(class_code=SeatClassCode.ECONOMY, total_seats=100, base_fare=250),
            ]
        )
    assert "Arrival time must be strictly after departure time" in str(exc.value)
