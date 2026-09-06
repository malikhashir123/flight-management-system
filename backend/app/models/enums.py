from enum import Enum

class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    OPS_AGENT = "OPS_AGENT"
    PASSENGER = "PASSENGER"

class LoyaltyTier(str, Enum):
    NONE = "NONE"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"

class FlightStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    DELAYED = "DELAYED"
    DEPARTED = "DEPARTED"
    CANCELLED = "CANCELLED"

class SeatClassCode(str, Enum):
    FIRST = "FIRST"
    BUSINESS = "BUSINESS"
    ECONOMY = "ECONOMY"

class FareType(str, Enum):
    BASIC_ECONOMY = "BASIC_ECONOMY"
    FLEXIBLE = "FLEXIBLE"
    BUSINESS_FLEX = "BUSINESS_FLEX"

class BookingStatus(str, Enum):
    HELD = "HELD"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    SCHEDULE_CHANGED = "SCHEDULE_CHANGED"
    REFUNDED = "REFUNDED"

class PassengerStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    CHECKED_IN = "CHECKED_IN"

class WaitlistStatus(str, Enum):
    PENDING = "PENDING"
    OFFERED = "OFFERED"
    CLAIMED = "CLAIMED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class RefundStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PROCESSED = "PROCESSED"
    ESCALATED = "ESCALATED"
    REJECTED = "REJECTED"

class ApprovalStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class PartialPolicy(str, Enum):
    FULL_FAIL = "FULL_FAIL"
    PARTIAL_HOLD = "PARTIAL_HOLD"
