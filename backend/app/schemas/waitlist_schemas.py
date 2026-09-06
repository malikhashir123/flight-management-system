from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from backend.app.models.enums import SeatClassCode, LoyaltyTier, WaitlistStatus

class WaitlistJoinRequest(BaseModel):
    class_code: SeatClassCode
    passenger_name: str = Field(min_length=2, max_length=255)

class WaitlistEntryResponse(BaseModel):
    id: str
    flight_id: str
    class_code: SeatClassCode
    passenger_name: str
    loyalty_tier: LoyaltyTier
    priority_score: int
    status: WaitlistStatus
    position: Optional[int] = None
    claim_deadline: Optional[datetime] = None
    created_at: datetime

class GateSeatAssignRequest(BaseModel):
    passenger_id: Optional[str] = None
    waitlist_entry_id: Optional[str] = None
    seat_id: str
    class_code: SeatClassCode
