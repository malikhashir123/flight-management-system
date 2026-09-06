from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from backend.app.models.enums import SeatClassCode, FlightStatus, FareType

class SeatClassAllocation(BaseModel):
    class_code: SeatClassCode
    total_seats: int = Field(gt=0, description="Strictly non-negative integer > 0")
    base_fare: float = Field(gt=0, description="Strictly positive base fare")
    overbooking_buffer_pct: int = Field(default=0, ge=0, description="Overbooking buffer %")
    max_overbooking_seats: int = Field(default=0, ge=0, description="Max overbooked seats")
    cutoff_hours_before_departure: int = Field(default=2, ge=0)

class FlightCreateRequest(BaseModel):
    flight_number: str = Field(min_length=2, max_length=16, description="Flight number, e.g. BA105")
    origin: str = Field(min_length=3, max_length=3, description="3-letter IATA origin code")
    destination: str = Field(min_length=3, max_length=3, description="3-letter IATA destination code")
    origin_tz: str = Field(default="UTC")
    destination_tz: str = Field(default="UTC")
    departure_time: datetime
    arrival_time: datetime
    total_capacity: int = Field(gt=0, description="Declared total aircraft capacity")
    seat_classes: List[SeatClassAllocation]

    @field_validator("origin", "destination")
    @classmethod
    def uppercase_iata(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def validate_flight_invariants(self):
        # REQ-ADM-01: chk_flight_airports
        if self.origin == self.destination:
            raise ValueError("Origin and destination airports cannot be identical.")
        # REQ-ADM-01: chk_flight_times
        if self.arrival_time <= self.departure_time:
            raise ValueError("Arrival time must be strictly after departure time.")
        # REQ-ADM-03: seat class totals sum exactly to declared aircraft capacity
        allocated_total = sum(c.total_seats for c in self.seat_classes)
        if allocated_total != self.total_capacity:
            raise ValueError(
                f"Seat class totals sum ({allocated_total}) must equal declared aircraft capacity ({self.total_capacity})."
            )
        # Verify no duplicate class codes in request
        class_codes = [c.class_code for c in self.seat_classes]
        if len(class_codes) != len(set(class_codes)):
            raise ValueError("Duplicate seat class code declared in allocation.")
        return self

class FlightScheduleUpdateRequest(BaseModel):
    departure_time: datetime
    arrival_time: datetime
    origin: Optional[str] = Field(default=None, min_length=3, max_length=3)
    destination: Optional[str] = Field(default=None, min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_times(self):
        if self.arrival_time <= self.departure_time:
            raise ValueError("Arrival time must be strictly after departure time.")
        return self

class FlightCancelRequest(BaseModel):
    cancellation_reason: str = Field(min_length=5, max_length=500)

class SeatClassAdjustRequest(BaseModel):
    class_code: SeatClassCode
    new_total_seats: int = Field(gt=0)

class ClassCapacityItem(BaseModel):
    class_code: SeatClassCode
    new_total_seats: int = Field(gt=0)

class BatchCapacityAdjustRequest(BaseModel):
    classes: List[ClassCapacityItem]

class FlightClassDetail(BaseModel):
    id: str
    class_code: SeatClassCode
    total_seats: int
    booked_seats: int
    held_seats: int
    available_seats: int
    base_fare: float
    overbooking_buffer_pct: int
    max_overbooking_seats: int
    cutoff_hours_before_departure: int

class FlightResponse(BaseModel):
    id: str
    flight_number: str
    origin: str
    destination: str
    origin_tz: str
    destination_tz: str
    departure_time: datetime
    arrival_time: datetime
    total_capacity: int
    status: FlightStatus
    cancellation_reason: Optional[str]
    schedule_version: int
    classes: List[FlightClassDetail] = []

    class Config:
        from_attributes = True

class FlightSearchQuery(BaseModel):
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    date: Optional[str] = None # YYYY-MM-DD
    currency: str = Field(default="USD")
