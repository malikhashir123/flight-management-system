-- =============================================================================
-- Flight Management System: Comprehensive Seed Data
-- Fulfills REQ-ADM-02 (UK -> Dubai flight departing 05:00, 100 total seats)
-- 20 First, 30 Business, 50 Economy
-- =============================================================================

-- 1. Seed Users (password: 'Admin123!' and 'Pass123!')
-- bcrypt hash for 'Admin123!' is '$2b$12$e8qRj8cT9zGvN3n1e8qRjOu7E1v3QzN1e8qRjOu7E1v3QzN1e8qRj' (or mock for seed)
INSERT INTO users (id, email, hashed_password, full_name, role, loyalty_tier)
VALUES 
    ('11111111-1111-1111-1111-111111111111', 'superadmin@airline.com', '$2b$12$e8qRj8cT9zGvN3n1e8qRjOu7E1v3QzN1e8qRjOu7E1v3QzN1e8qRj', 'Chief Operations Admin', 'SUPER_ADMIN', 'PLATINUM'),
    ('22222222-2222-2222-2222-222222222222', 'ops.agent@airline.com', '$2b$12$e8qRj8cT9zGvN3n1e8qRjOu7E1v3QzN1e8qRjOu7E1v3QzN1e8qRj', 'LHR Gate Agent', 'OPS_AGENT', 'GOLD'),
    ('33333333-3333-3333-3333-333333333333', 'john.doe@example.com', '$2b$12$e8qRj8cT9zGvN3n1e8qRjOu7E1v3QzN1e8qRjOu7E1v3QzN1e8qRj', 'John Doe (Platinum Member)', 'PASSENGER', 'PLATINUM'),
    ('44444444-4444-4444-4444-444444444444', 'jane.smith@example.com', '$2b$12$e8qRj8cT9zGvN3n1e8qRjOu7E1v3QzN1e8qRjOu7E1v3QzN1e8qRj', 'Jane Smith (Standard Member)', 'PASSENGER', 'NONE')
ON CONFLICT (email) DO NOTHING;

-- 2. Seed Flight: UK (LHR) -> Dubai (DXB) departing 05:00 UTC, 100 total capacity
-- REQ-ADM-01, REQ-ADM-02
INSERT INTO flights (
    id, flight_number, origin, destination, origin_tz, destination_tz,
    departure_time, arrival_time, total_capacity, status, schedule_version
) VALUES (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'BA105',
    'LHR',
    'DXB',
    'Europe/London',
    'Asia/Dubai',
    (CURRENT_DATE + INTERVAL '1 day' + TIME '05:00:00')::TIMESTAMPTZ,
    (CURRENT_DATE + INTERVAL '1 day' + TIME '12:30:00')::TIMESTAMPTZ,
    100,
    'SCHEDULED',
    1
) ON CONFLICT DO NOTHING;

-- 3. Seed Flight Classes (20 First, 30 Business, 50 Economy = 100 Total)
-- REQ-ADM-02, REQ-ADM-03, REQ-ADM-04, REQ-BKG-20
INSERT INTO flight_classes (
    id, flight_id, class_code, total_seats, booked_seats, held_seats, 
    base_fare, overbooking_buffer_pct, max_overbooking_seats, cutoff_hours_before_departure
) VALUES 
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'FIRST', 20, 0, 0, 1500.00, 0, 0, 1),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'BUSINESS', 30, 0, 0, 750.00, 0, 0, 1),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0003', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'ECONOMY', 50, 0, 0, 250.00, 6, 3, 3)
ON CONFLICT (flight_id, class_code) DO NOTHING;

-- 4. Seed Physical Seats (100 total seats)
-- REQ-ADM-07
-- Rows 1-5: First Class (20 seats: 1A-1D, 2A-2D, 3A-3D, 4A-4D, 5A-5D)
DO $$
DECLARE
    r INT;
    c TEXT;
    cols TEXT[] := ARRAY['A', 'B', 'C', 'D'];
BEGIN
    FOR r IN 1..5 LOOP
        FOREACH c IN ARRAY cols LOOP
            INSERT INTO seats (flight_id, seat_number, class_code, seat_row, seat_column)
            VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', r || c, 'FIRST', r, c)
            ON CONFLICT (flight_id, seat_number) DO NOTHING;
        END LOOP;
    END LOOP;
END $$;

-- Rows 6-10: Business Class (30 seats: 6 seats per row A-F)
DO $$
DECLARE
    r INT;
    c TEXT;
    cols TEXT[] := ARRAY['A', 'B', 'C', 'D', 'E', 'F'];
BEGIN
    FOR r IN 6..10 LOOP
        FOREACH c IN ARRAY cols LOOP
            INSERT INTO seats (flight_id, seat_number, class_code, seat_row, seat_column)
            VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', r || c, 'BUSINESS', r, c)
            ON CONFLICT (flight_id, seat_number) DO NOTHING;
        END LOOP;
    END LOOP;
END $$;

-- Rows 11-19: Economy Class (50 seats: Rows 11-18 have 6 seats A-F = 48, Row 19 has 2 seats A,B)
DO $$
DECLARE
    r INT;
    c TEXT;
    cols TEXT[] := ARRAY['A', 'B', 'C', 'D', 'E', 'F'];
BEGIN
    FOR r IN 11..18 LOOP
        FOREACH c IN ARRAY cols LOOP
            INSERT INTO seats (flight_id, seat_number, class_code, seat_row, seat_column)
            VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', r || c, 'ECONOMY', r, c)
            ON CONFLICT (flight_id, seat_number) DO NOTHING;
        END LOOP;
    END LOOP;
    INSERT INTO seats (flight_id, seat_number, class_code, seat_row, seat_column)
    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '19A', 'ECONOMY', 19, 'A'),
           ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '19B', 'ECONOMY', 19, 'B')
    ON CONFLICT (flight_id, seat_number) DO NOTHING;
END $$;

-- 5. Seed Secondary Route for Search Testing: LHR -> JFK
INSERT INTO flights (
    id, flight_number, origin, destination, origin_tz, destination_tz,
    departure_time, arrival_time, total_capacity, status, schedule_version
) VALUES (
    'cccccccc-cccc-cccc-cccc-cccccccccccc',
    'BA177',
    'LHR',
    'JFK',
    'Europe/London',
    'America/New_York',
    (CURRENT_DATE + INTERVAL '2 days' + TIME '10:00:00')::TIMESTAMPTZ,
    (CURRENT_DATE + INTERVAL '2 days' + TIME '13:00:00')::TIMESTAMPTZ,
    100,
    'SCHEDULED',
    1
) ON CONFLICT DO NOTHING;

INSERT INTO flight_classes (
    id, flight_id, class_code, total_seats, booked_seats, held_seats, 
    base_fare, overbooking_buffer_pct, max_overbooking_seats, cutoff_hours_before_departure
) VALUES 
    ('dddddddd-dddd-dddd-dddd-dddddddd0001', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'FIRST', 20, 0, 0, 2000.00, 0, 0, 1),
    ('dddddddd-dddd-dddd-dddd-dddddddd0002', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'BUSINESS', 30, 0, 0, 1100.00, 0, 0, 1),
    ('dddddddd-dddd-dddd-dddd-dddddddd0003', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'ECONOMY', 50, 0, 0, 450.00, 6, 3, 3)
ON CONFLICT (flight_id, class_code) DO NOTHING;
