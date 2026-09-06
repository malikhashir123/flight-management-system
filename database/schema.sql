-- =============================================================================
-- Flight Management System: Comprehensive Supabase PostgreSQL Schema
-- Derived strictly from flight_management_system_feature_list.pdf
-- Single Ledger of Truth for Flights, Seats, Bookings & Auditing
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- 1. ENUMS & DOMAIN TYPES
-- =============================================================================

DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('SUPER_ADMIN', 'OPS_AGENT', 'PASSENGER');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE loyalty_tier_enum AS ENUM ('NONE', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE flight_status_enum AS ENUM ('SCHEDULED', 'DELAYED', 'DEPARTED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE seat_class_code_enum AS ENUM ('FIRST', 'BUSINESS', 'ECONOMY');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE fare_type_enum AS ENUM ('BASIC_ECONOMY', 'FLEXIBLE', 'BUSINESS_FLEX');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE booking_status_enum AS ENUM ('HELD', 'CONFIRMED', 'CANCELLED', 'SCHEDULE_CHANGED', 'REFUNDED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE passenger_status_enum AS ENUM ('CONFIRMED', 'CANCELLED', 'CHECKED_IN');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE waitlist_status_enum AS ENUM ('PENDING', 'OFFERED', 'CLAIMED', 'EXPIRED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE refund_status_enum AS ENUM ('PENDING', 'APPROVED', 'PROCESSED', 'ESCALATED', 'REJECTED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE approval_status_enum AS ENUM ('PENDING_REVIEW', 'APPROVED', 'REJECTED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE partial_policy_enum AS ENUM ('FULL_FAIL', 'PARTIAL_HOLD');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =============================================================================
-- 2. CORE USERS & AUTHENTICATION (FastAPI Writer)
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'PASSENGER',
    loyalty_tier loyalty_tier_enum NOT NULL DEFAULT 'NONE',
    is_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 3. FLIGHTS & AIRCRAFT INVENTORY (FastAPI Sole Writer)
-- REQ-ADM-01, REQ-ADM-05, REQ-ADM-06, REQ-ADM-09, REQ-SHD-46
-- =============================================================================

CREATE TABLE IF NOT EXISTS flights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_number VARCHAR(16) NOT NULL,
    origin VARCHAR(3) NOT NULL,
    destination VARCHAR(3) NOT NULL,
    origin_tz VARCHAR(64) NOT NULL DEFAULT 'UTC',
    destination_tz VARCHAR(64) NOT NULL DEFAULT 'UTC',
    departure_time TIMESTAMPTZ NOT NULL,
    arrival_time TIMESTAMPTZ NOT NULL,
    total_capacity INTEGER NOT NULL,
    status flight_status_enum NOT NULL DEFAULT 'SCHEDULED',
    cancellation_reason TEXT,
    schedule_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_flight_capacity_positive CHECK (total_capacity > 0),
    CONSTRAINT chk_flight_times CHECK (arrival_time > departure_time),
    CONSTRAINT chk_flight_airports CHECK (origin <> destination)
);

-- REQ-ADM-09: Duplicate flight number detection for same day/route
CREATE UNIQUE INDEX IF NOT EXISTS uq_flight_number_date_route 
ON flights (flight_number, origin, destination, (departure_time::DATE)) 
WHERE status != 'CANCELLED';

-- =============================================================================
-- 4. FLIGHT SEAT CLASSES (FastAPI & n8n Dual-Writer with Row-Locking)
-- REQ-ADM-02, REQ-ADM-03, REQ-ADM-04, REQ-ADM-08, REQ-BKG-18, REQ-BKG-20
-- =============================================================================

CREATE TABLE IF NOT EXISTS flight_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_id UUID NOT NULL REFERENCES flights(id) ON DELETE RESTRICT,
    class_code seat_class_code_enum NOT NULL,
    total_seats INTEGER NOT NULL,
    booked_seats INTEGER NOT NULL DEFAULT 0,
    held_seats INTEGER NOT NULL DEFAULT 0,
    base_fare NUMERIC(10, 2) NOT NULL,
    overbooking_buffer_pct INTEGER NOT NULL DEFAULT 0, -- 0 for First, 5 for Economy
    max_overbooking_seats INTEGER NOT NULL DEFAULT 0,
    cutoff_hours_before_departure INTEGER NOT NULL DEFAULT 2, -- e.g. 1h for First/Biz, 3h for Eco
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_flight_class UNIQUE (flight_id, class_code),
    CONSTRAINT chk_class_seats_positive CHECK (total_seats > 0),
    CONSTRAINT chk_booked_seats_nonneg CHECK (booked_seats >= 0),
    CONSTRAINT chk_held_seats_nonneg CHECK (held_seats >= 0),
    CONSTRAINT chk_fare_positive CHECK (base_fare > 0),
    CONSTRAINT chk_overbooking_limit CHECK (booked_seats + held_seats <= total_seats + max_overbooking_seats)
);

-- =============================================================================
-- 5. PHYSICAL SEATS MAP (FastAPI Sole Writer)
-- REQ-ADM-07
-- =============================================================================

CREATE TABLE IF NOT EXISTS seats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_id UUID NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    seat_number VARCHAR(8) NOT NULL,
    class_code seat_class_code_enum NOT NULL,
    seat_row INTEGER NOT NULL,
    seat_column VARCHAR(2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_flight_seat UNIQUE (flight_id, seat_number)
);

-- =============================================================================
-- 6. SEARCH PRICE QUOTES (FastAPI Sole Writer)
-- REQ-SRC-14
-- =============================================================================

CREATE TABLE IF NOT EXISTS price_quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_id UUID NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    class_code seat_class_code_enum NOT NULL,
    fare_type fare_type_enum NOT NULL,
    quoted_price NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quote_expiry ON price_quotes(expires_at);

-- =============================================================================
-- 7. TEMPORARY SEAT HOLDS (FastAPI Sole Writer)
-- REQ-BKG-17
-- =============================================================================

CREATE TABLE IF NOT EXISTS seat_holds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_id UUID NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    class_code seat_class_code_enum NOT NULL,
    seat_id UUID REFERENCES seats(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(128) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_released BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_active_seat_holds ON seat_holds(flight_id, class_code) WHERE is_released = FALSE;

-- =============================================================================
-- 8. BOOKINGS (FastAPI Sole Writer)
-- REQ-BKG-18, REQ-BKG-19, REQ-CHG-23, REQ-CHG-25, REQ-SCH-33
-- =============================================================================

CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_reference VARCHAR(12) UNIQUE NOT NULL, -- PNR Code (e.g. FMS-8291A)
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    flight_id UUID NOT NULL REFERENCES flights(id) ON DELETE RESTRICT,
    class_code seat_class_code_enum NOT NULL,
    fare_type fare_type_enum NOT NULL,
    total_fare NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status booking_status_enum NOT NULL DEFAULT 'CONFIRMED',
    schedule_change_acknowledged BOOLEAN NOT NULL DEFAULT TRUE,
    eligible_for_involuntary_refund BOOLEAN NOT NULL DEFAULT FALSE,
    checkin_reminder_sent BOOLEAN NOT NULL DEFAULT FALSE,
    fraud_score NUMERIC(5, 2) DEFAULT 0.0,
    fraud_flag BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bookings_reminder ON bookings(flight_id, checkin_reminder_sent) WHERE status = 'CONFIRMED';
CREATE INDEX IF NOT EXISTS idx_bookings_fraud ON bookings(created_at, fraud_score) WHERE fraud_flag = TRUE;

-- =============================================================================
-- 9. PASSENGERS (FastAPI Sole Writer)
-- REQ-BKG-21, REQ-CHG-24
-- =============================================================================

CREATE TABLE IF NOT EXISTS passengers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    seat_id UUID REFERENCES seats(id) ON DELETE SET NULL,
    first_name VARCHAR(128) NOT NULL,
    last_name VARCHAR(128) NOT NULL,
    passport_number VARCHAR(64) NOT NULL,
    passenger_status passenger_status_enum NOT NULL DEFAULT 'CONFIRMED',
    fare_portion NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 10. WAITLIST ENTRIES (FastAPI Inserts, n8n Updates Status/Offers)
-- REQ-WST-28, REQ-WST-29, REQ-WST-30, REQ-WST-31, REQ-WST-32
-- =============================================================================

CREATE TABLE IF NOT EXISTS waitlist_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_id UUID NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    class_code seat_class_code_enum NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    passenger_name VARCHAR(255) NOT NULL,
    loyalty_tier loyalty_tier_enum NOT NULL DEFAULT 'NONE',
    priority_score INTEGER NOT NULL DEFAULT 0, -- Higher score = higher priority
    status waitlist_status_enum NOT NULL DEFAULT 'PENDING',
    claim_deadline TIMESTAMPTZ,
    offered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_flight_user_waitlist UNIQUE (flight_id, class_code, user_id)
);
CREATE INDEX IF NOT EXISTS idx_waitlist_pending ON waitlist_entries(flight_id, class_code, priority_score DESC, created_at ASC) 
WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_waitlist_offered ON waitlist_entries(claim_deadline) 
WHERE status = 'OFFERED';

-- =============================================================================
-- 11. PAYMENTS (FastAPI Sole Writer)
-- =============================================================================

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE RESTRICT,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_method VARCHAR(64) NOT NULL,
    transaction_reference VARCHAR(128) UNIQUE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 12. REFUNDS (FastAPI Creates, n8n Escalates)
-- REQ-CHG-23, REQ-CHG-27
-- =============================================================================

CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE RESTRICT,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    refund_type VARCHAR(32) NOT NULL, -- 'ORIGINAL_PAYMENT', 'TRAVEL_CREDIT'
    status refund_status_enum NOT NULL DEFAULT 'PENDING',
    reason TEXT,
    escalated_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_refunds_unresolved ON refunds(created_at) WHERE status = 'PENDING' AND escalated_at IS NULL;

-- =============================================================================
-- 13. TRAVEL CREDITS (FastAPI Issues, n8n Monitors)
-- REQ-CHG-26
-- =============================================================================

CREATE TABLE IF NOT EXISTS travel_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credit_code VARCHAR(32) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    expires_at TIMESTAMPTZ NOT NULL, -- Strictly 365 days
    is_redeemed BOOLEAN NOT NULL DEFAULT FALSE,
    redeemed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_travel_credit_lookup ON travel_credits(credit_code) WHERE is_redeemed = FALSE;

-- =============================================================================
-- 14. PRICE ALERTS (FastAPI Subscribes, n8n Evaluates & Updates)
-- REQ-SCH-34
-- =============================================================================

CREATE TABLE IF NOT EXISTS price_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    origin VARCHAR(3) NOT NULL,
    destination VARCHAR(3) NOT NULL,
    target_price NUMERIC(10, 2) NOT NULL,
    last_notified_price NUMERIC(10, 2),
    last_notified_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 15. SUPPORT DRAFTS & HUMAN APPROVAL (n8n Drafts & Updates on Approval)
-- REQ-FRD-37, REQ-FRD-38, REQ-APP-43
-- =============================================================================

CREATE TABLE IF NOT EXISTS support_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID REFERENCES bookings(id) ON DELETE SET NULL,
    customer_email VARCHAR(255) NOT NULL,
    customer_query TEXT NOT NULL,
    retrieved_context JSONB,
    rag_drafted_answer TEXT NOT NULL,
    approval_status approval_status_enum NOT NULL DEFAULT 'PENDING_REVIEW',
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    review_notes TEXT,
    approved_at TIMESTAMPTZ,
    email_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 16. FRAUD LOGS (n8n Sole Writer)
-- REQ-FRD-39, REQ-FRD-41
-- =============================================================================

CREATE TABLE IF NOT EXISTS fraud_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_batch_id UUID NOT NULL,
    booking_id UUID REFERENCES bookings(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    risk_score NUMERIC(5, 2) NOT NULL,
    reasons JSONB NOT NULL,
    flagged_action VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 17. ADMIN AUDIT LOGS (FastAPI Sole Writer)
-- REQ-ADM-11
-- =============================================================================

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id UUID NOT NULL,
    before_state JSONB,
    after_state JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 18. SYSTEM AUDIT TRAIL (FastAPI & n8n Regulatory Decision Ledger)
-- REQ-APP-44
-- =============================================================================

CREATE TABLE IF NOT EXISTS system_audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(64) NOT NULL,
    actor_system VARCHAR(32) NOT NULL, -- 'FASTAPI', 'N8N', 'HUMAN'
    actor_id VARCHAR(128) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id UUID NOT NULL,
    rule_applied VARCHAR(128) NOT NULL,
    decision_metadata JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 19. IDEMPOTENCY KEYS (FastAPI Sole Writer)
-- REQ-BKG-19, REQ-INF-52
-- =============================================================================

CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key VARCHAR(128) PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    request_path VARCHAR(255) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_code INTEGER NOT NULL,
    response_body JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_idemp_expires ON idempotency_keys(expires_at);

-- =============================================================================
-- 20. RECONCILIATION LOGS [IMPLEMENTATION RECOMMENDATION]
-- REQ-SHD-49
-- =============================================================================

CREATE TABLE IF NOT EXISTS system_reconciliation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_type VARCHAR(64) NOT NULL,
    discrepancies_count INTEGER NOT NULL DEFAULT 0,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 21. EMAIL LOGS (FastAPI Transactional Send Logging)
-- REQ-INF-56
-- =============================================================================

CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    template_name VARCHAR(64) NOT NULL,
    reference_id UUID,
    status VARCHAR(32) NOT NULL DEFAULT 'SENT',
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
