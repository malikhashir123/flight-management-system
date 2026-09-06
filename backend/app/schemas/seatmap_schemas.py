from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.models.enums import SeatClassCode

class SeatItem(BaseModel):
    id: str
    seat_number: str
    class_code: SeatClassCode
    seat_row: int
    seat_column: str
    is_available: bool
    is_booked: bool = False
    is_held: bool = False

class SeatMapLayoutResponse(BaseModel):
    flight_id: str
    flight_number: str
    total_seats: int
    seats: List[SeatItem]

class SeatMapDefineRequest(BaseModel):
    seats: List[SeatItem]

class AdminSeatDefineItem(BaseModel):
    id: Optional[str] = None
    seat_number: str
    class_code: SeatClassCode
    seat_row: int
    seat_column: str
    is_active: bool = True

class AdminSeatMapDefineRequest(BaseModel):
    seats: List[AdminSeatDefineItem]

