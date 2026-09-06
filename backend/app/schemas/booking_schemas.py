from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.models.enums import (
    SeatClassCode, FareType, BookingStatus, PassengerStatus, PartialPolicy
)

class PassengerInput(BaseModel):
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    passport_number: str = Field(min_length=3, max_length=64)
    seat_id: Optional[str] = None

class SeatHoldRequest(BaseModel):
    flight_id: str
    class_code: SeatClassCode
    seat_id: Optional[str] = None # Optional physical seat choice

class SeatHoldResponse(BaseModel):
    hold_id: str
    flight_id: str
    class_code: SeatClassCode
    seat_id: Optional[str]
    session_token: str
    expires_at: datetime
    hold_duration_seconds: int

class BookingCreateRequest(BaseModel):
    flight_id: str
    class_code: SeatClassCode
    fare_type: FareType
    hold_id: Optional[str] = None
    passengers: List[PassengerInput] = Field(min_length=1)
    partial_policy: PartialPolicy = Field(default=PartialPolicy.FULL_FAIL)
    currency: str = Field(default="USD")
    credit_code: Optional[str] = None # Optional travel voucher redemption

class PassengerDetail(BaseModel):
    id: str
    first_name: str
    last_name: str
    passport_number: str
    seat_number: Optional[str] = None
    passenger_status: PassengerStatus
    fare_portion: float

class BookingResponse(BaseModel):
    id: str
    booking_reference: str
    flight_id: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    class_code: SeatClassCode
    fare_type: FareType
    total_fare: float
    currency: str
    status: BookingStatus
    passengers: List[PassengerDetail]
    schedule_change_acknowledged: bool
    eligible_for_involuntary_refund: bool
    created_at: datetime

class BookingCancelRequest(BaseModel):
    reason: Optional[str] = Field(default="Customer requested cancellation")
    cancellation_fee: Optional[float] = None
    prefer_credit: Optional[bool] = False

class BookingCancelResponse(BaseModel):
    booking_id: str
    booking_reference: str
    status: BookingStatus
    refund_type: str # 'ORIGINAL_PAYMENT', 'TRAVEL_CREDIT', 'NONE'
    refund_amount: float
    cancellation_fee: float
    travel_credit_code: Optional[str] = None
    message: str

class PartialPassengerCancelRequest(BaseModel):
    passenger_id: Optional[str] = None
    passenger_ids: Optional[List[str]] = None
    reason: Optional[str] = Field(default="Partial group cancellation")

class RemediationChoice(BaseModel):
    remediation_type: str = Field(description="'CASH_REFUND', 'TRAVEL_CREDIT', or 'REBOOK'")
    rebook_flight_id: Optional[str] = None

class RemediationResponse(BaseModel):
    booking_id: str
    remediation_type: str
    status: str
    credit_code: Optional[str] = None
    amount: float
    message: str

class PassengerAdminUpdate(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    passport_number: Optional[str] = None
    passenger_status: Optional[PassengerStatus] = None

class BookingAdminUpdateRequest(BaseModel):
    status: Optional[BookingStatus] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    total_price: Optional[float] = None
    currency: Optional[str] = None
    passengers: Optional[List[PassengerAdminUpdate]] = None
