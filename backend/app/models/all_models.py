import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey, 
    Text, UniqueConstraint, CheckConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.enums import (
    UserRole, LoyaltyTier, FlightStatus, SeatClassCode, 
    FareType, BookingStatus, PassengerStatus, WaitlistStatus, 
    RefundStatus, ApprovalStatus
)

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default=UserRole.PASSENGER.value)
    loyalty_tier = Column(String(32), nullable=False, default=LoyaltyTier.NONE.value)
    is_flagged = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")
    seat_holds = relationship("SeatHold", back_populates="user", cascade="all, delete-orphan")
    waitlist_entries = relationship("WaitlistEntry", back_populates="user", cascade="all, delete-orphan")
    price_alerts = relationship("PriceAlert", back_populates="user", cascade="all, delete-orphan")
    travel_credits = relationship("TravelCredit", back_populates="user", cascade="all, delete-orphan")

class Flight(Base):
    __tablename__ = "flights"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_number = Column(String(16), nullable=False, index=True)
    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)
    origin_tz = Column(String(64), nullable=False, default="UTC")
    destination_tz = Column(String(64), nullable=False, default="UTC")
    departure_time = Column(DateTime(timezone=True), nullable=False, index=True)
    arrival_time = Column(DateTime(timezone=True), nullable=False)
    total_capacity = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default=FlightStatus.SCHEDULED.value)
    cancellation_reason = Column(Text, nullable=True)
    schedule_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    classes = relationship("FlightClass", back_populates="flight", cascade="all, delete-orphan")
    seats = relationship("Seat", back_populates="flight", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="flight")
    waitlist_entries = relationship("WaitlistEntry", back_populates="flight")

    __table_args__ = (
        CheckConstraint("total_capacity > 0", name="chk_flight_capacity_positive"),
        CheckConstraint("arrival_time > departure_time", name="chk_flight_times"),
        CheckConstraint("origin <> destination", name="chk_flight_airports"),
    )

class FlightClass(Base):
    __tablename__ = "flight_classes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_id = Column(String(36), ForeignKey("flights.id", ondelete="RESTRICT"), nullable=False)
    class_code = Column(String(32), nullable=False)
    total_seats = Column(Integer, nullable=False)
    booked_seats = Column(Integer, nullable=False, default=0)
    held_seats = Column(Integer, nullable=False, default=0)
    base_fare = Column(Numeric(10, 2), nullable=False)
    overbooking_buffer_pct = Column(Integer, nullable=False, default=0)
    max_overbooking_seats = Column(Integer, nullable=False, default=0)
    cutoff_hours_before_departure = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    flight = relationship("Flight", back_populates="classes")

    __table_args__ = (
        UniqueConstraint("flight_id", "class_code", name="uq_flight_class"),
        CheckConstraint("total_seats > 0", name="chk_class_seats_positive"),
        CheckConstraint("booked_seats >= 0", name="chk_booked_seats_nonneg"),
        CheckConstraint("held_seats >= 0", name="chk_held_seats_nonneg"),
        CheckConstraint("base_fare > 0", name="chk_fare_positive"),
    )

class Seat(Base):
    __tablename__ = "seats"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_id = Column(String(36), ForeignKey("flights.id", ondelete="CASCADE"), nullable=False)
    seat_number = Column(String(8), nullable=False)
    class_code = Column(String(32), nullable=False)
    seat_row = Column(Integer, nullable=False)
    seat_column = Column(String(2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    flight = relationship("Flight", back_populates="seats")

    __table_args__ = (
        UniqueConstraint("flight_id", "seat_number", name="uq_flight_seat"),
    )

class PriceQuote(Base):
    __tablename__ = "price_quotes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_id = Column(String(36), ForeignKey("flights.id", ondelete="CASCADE"), nullable=False)
    class_code = Column(String(32), nullable=False)
    fare_type = Column(String(32), nullable=False)
    quoted_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class SeatHold(Base):
    __tablename__ = "seat_holds"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_id = Column(String(36), ForeignKey("flights.id", ondelete="CASCADE"), nullable=False)
    class_code = Column(String(32), nullable=False)
    seat_id = Column(String(36), ForeignKey("seats.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_released = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="seat_holds")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_reference = Column(String(12), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    flight_id = Column(String(36), ForeignKey("flights.id", ondelete="RESTRICT"), nullable=False)
    class_code = Column(String(32), nullable=False)
    fare_type = Column(String(32), nullable=False)
    total_fare = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(32), nullable=False, default=BookingStatus.CONFIRMED.value)
    schedule_change_acknowledged = Column(Boolean, nullable=False, default=True)
    eligible_for_involuntary_refund = Column(Boolean, nullable=False, default=False)
    checkin_reminder_sent = Column(Boolean, nullable=False, default=False)
    fraud_score = Column(Numeric(5, 2), default=0.0)
    fraud_flag = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="bookings")
    flight = relationship("Flight", back_populates="bookings")
    passengers = relationship("Passenger", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")
    refunds = relationship("Refund", back_populates="booking", cascade="all, delete-orphan")

class Passenger(Base):
    __tablename__ = "passengers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    seat_id = Column(String(36), ForeignKey("seats.id", ondelete="SET NULL"), nullable=True)
    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=False)
    passport_number = Column(String(64), nullable=False)
    passenger_status = Column(String(32), nullable=False, default=PassengerStatus.CONFIRMED.value)
    fare_portion = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    booking = relationship("Booking", back_populates="passengers")

class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_id = Column(String(36), ForeignKey("flights.id", ondelete="CASCADE"), nullable=False)
    class_code = Column(String(32), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    passenger_name = Column(String(255), nullable=False)
    loyalty_tier = Column(String(32), nullable=False, default=LoyaltyTier.NONE.value)
    priority_score = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default=WaitlistStatus.PENDING.value)
    claim_deadline = Column(DateTime(timezone=True), nullable=True)
    offered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="waitlist_entries")
    flight = relationship("Flight", back_populates="waitlist_entries")

    __table_args__ = (
        UniqueConstraint("flight_id", "class_code", "user_id", name="uq_flight_user_waitlist"),
    )

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    payment_method = Column(String(64), nullable=False)
    transaction_reference = Column(String(128), unique=True, nullable=False)
    status = Column(String(32), nullable=False, default="SUCCESS")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    booking = relationship("Booking", back_populates="payments")

class Refund(Base):
    __tablename__ = "refunds"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    refund_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default=RefundStatus.PENDING.value)
    reason = Column(Text, nullable=True)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    booking = relationship("Booking", back_populates="refunds")

class TravelCredit(Base):
    __tablename__ = "travel_credits"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    credit_code = Column(String(32), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_redeemed = Column(Boolean, nullable=False, default=False)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="travel_credits")

class PriceAlert(Base):
    __tablename__ = "price_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    target_price = Column(Numeric(10, 2), nullable=False)
    last_notified_price = Column(Numeric(10, 2), nullable=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="price_alerts")

class SupportDraft(Base):
    __tablename__ = "support_drafts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True)
    customer_email = Column(String(255), nullable=False)
    customer_query = Column(Text, nullable=False)
    retrieved_context = Column(JSON, nullable=True)
    rag_drafted_answer = Column(Text, nullable=False)
    approval_status = Column(String(32), nullable=False, default=ApprovalStatus.PENDING_REVIEW.value)
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class FraudLog(Base):
    __tablename__ = "fraud_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_batch_id = Column(String(36), nullable=False)
    booking_id = Column(String(36), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    risk_score = Column(Numeric(5, 2), nullable=False)
    reasons = Column(JSON, nullable=False)
    flagged_action = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_user_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(36), nullable=False)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class SystemAuditTrail(Base):
    __tablename__ = "system_audit_trail"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(64), nullable=False)
    actor_system = Column(String(32), nullable=False)
    actor_id = Column(String(128), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(36), nullable=False)
    rule_applied = Column(String(128), nullable=False)
    decision_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    
    idempotency_key = Column(String(128), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    request_path = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_code = Column(Integer, nullable=False)
    response_body = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

class SystemReconciliationLog(Base):
    __tablename__ = "system_reconciliation_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_type = Column(String(64), nullable=False)
    discrepancies_count = Column(Integer, nullable=False, default=0)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    template_name = Column(String(64), nullable=False)
    reference_id = Column(String(36), nullable=True)
    status = Column(String(32), nullable=False, default="SENT")
    sent_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
