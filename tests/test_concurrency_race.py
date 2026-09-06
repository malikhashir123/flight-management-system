import pytest
import asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from database.init_db import init_and_seed_db

@pytest.mark.asyncio
async def test_atomic_seat_decrement_oversell_prevention():
    """
    REQ-BKG-18: Atomic seat-class decrement to prevent two simultaneous bookings 
    selling the same last seat.
    Simulates 10 concurrent requests attempting to book when only 2 seats remain.
    Exactly 2 must succeed, 8 must receive 409 Conflict. Zero overbooking!
    """
    await init_and_seed_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post("/api/v1/auth/login", json={"email": "superadmin@airline.com", "password": "Admin123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create a limited flight with only 2 First Class seats
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        f_res = await ac.post("/api/v1/admin/flights", json={
            "flight_number": f"TEST{uuid.uuid4().hex[:4].upper()}",
            "origin": "LHR",
            "destination": "DXB",
            "departure_time": (now + timedelta(days=5)).isoformat(),
            "arrival_time": (now + timedelta(days=5, hours=7)).isoformat(),
            "total_capacity": 2,
            "seat_classes": [
                {"class_code": "FIRST", "total_seats": 2, "base_fare": 1000.0, "overbooking_buffer_pct": 0, "max_overbooking_seats": 0}
            ]
        }, headers=headers)
        flight_id = f_res.json()["id"]

        # 2. Fire 10 concurrent booking requests simultaneously
        async def make_booking_attempt(user_num: int):
            booking_headers = {
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": f"race-idemp-{user_num}-{uuid.uuid4()}"
            }
            payload = {
                "flight_id": flight_id,
                "class_code": "FIRST",
                "fare_type": "FLEXIBLE",
                "passengers": [{"first_name": f"User{user_num}", "last_name": "Racer", "passport_number": f"PASS{user_num}"}]
            }
            return await ac.post("/api/v1/bookings", json=payload, headers=booking_headers)

        responses = await asyncio.gather(*(make_booking_attempt(i) for i in range(10)))

        successes = [r for r in responses if r.status_code == 201]
        failures = [r for r in responses if r.status_code == 409]

        assert len(successes) == 2, f"Expected exactly 2 bookings to succeed, got {len(successes)}"
        assert len(failures) == 8, f"Expected 8 requests to fail with 409 Conflict, got {len(failures)}"
