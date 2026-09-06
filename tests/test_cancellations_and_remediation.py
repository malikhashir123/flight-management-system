import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from database.init_db import init_and_seed_db

@pytest.mark.asyncio
async def test_flexible_fare_cancellation_refund():
    """REQ-CHG-23: Flexible fare voluntary cancellation issues monetary refund minus processing fee."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post("/api/v1/auth/login", json={"email": "superadmin@airline.com", "password": "Admin123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create flexible booking
        b_res = await ac.post("/api/v1/bookings", json={
            "flight_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "class_code": "ECONOMY",
            "fare_type": "FLEXIBLE",
            "passengers": [{"first_name": "Charlie", "last_name": "Day", "passport_number": "P44444"}]
        }, headers=headers)
        b_data = b_res.json()
        b_id = b_data["id"]

        # Cancel booking
        c_res = await ac.post(f"/api/v1/bookings/{b_id}/cancel", json={"reason": "Change of plans"}, headers=headers)
        assert c_res.status_code == 200
        c_data = c_res.json()
        assert c_data["refund_type"] == "ORIGINAL_PAYMENT"
        assert c_data["cancellation_fee"] == 25.00
        assert c_data["refund_amount"] > 0

@pytest.mark.asyncio
async def test_basic_economy_voluntary_cancellation_zero_refund():
    """REQ-CHG-23: Basic economy voluntary cancellation results in $0 monetary refund."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post("/api/v1/auth/login", json={"email": "superadmin@airline.com", "password": "Admin123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create basic economy booking
        b_res = await ac.post("/api/v1/bookings", json={
            "flight_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "class_code": "ECONOMY",
            "fare_type": "BASIC_ECONOMY",
            "passengers": [{"first_name": "Dana", "last_name": "White", "passport_number": "P55555"}]
        }, headers=headers)
        b_data = b_res.json()
        b_id = b_data["id"]

        # Cancel booking
        c_res = await ac.post(f"/api/v1/bookings/{b_id}/cancel", json={"reason": "Voluntary cancel"}, headers=headers)
        assert c_res.status_code == 200
        c_data = c_res.json()
        assert c_data["refund_amount"] == 0.0
        assert "non-refundable" in c_data["message"]

@pytest.mark.asyncio
async def test_involuntary_schedule_change_override():
    """REQ-ADM-05, REQ-CHG-25: Schedule delay >= 2h grants 100% full refund on non-refundable Basic Economy ticket."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post("/api/v1/auth/login", json={"email": "superadmin@airline.com", "password": "Admin123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create Basic Economy booking on BA177 (LHR->JFK)
        b_res = await ac.post("/api/v1/bookings", json={
            "flight_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "class_code": "ECONOMY",
            "fare_type": "BASIC_ECONOMY",
            "passengers": [{"first_name": "Eve", "last_name": "Polastri", "passport_number": "P66666"}]
        }, headers=headers)
        b_data = b_res.json()
        b_id = b_data["id"]

        # 2. Airline delays flight BA177 by 3 hours (180 minutes >= 120 minutes)
        orig_dep = b_data["departure_time"]
        from datetime import datetime, timezone, timedelta
        dep_dt = datetime.fromisoformat(orig_dep.replace("Z", "+00:00"))
        new_dep = dep_dt + timedelta(hours=3)
        new_arr = new_dep + timedelta(hours=8)

        sched_res = await ac.patch(
            f"/api/v1/admin/flights/cccccccc-cccc-cccc-cccc-cccccccccccc/schedule",
            json={"departure_time": new_dep.isoformat(), "arrival_time": new_arr.isoformat()},
            headers=headers
        )
        assert sched_res.status_code == 200

        # 3. Passenger cancels: involuntary override must grant 100% refund despite Basic Economy!
        c_res = await ac.post(f"/api/v1/bookings/{b_id}/cancel", json={"reason": "Flight delayed by 3 hours"}, headers=headers)
        assert c_res.status_code == 200
        c_data = c_res.json()
        assert c_data["refund_type"] == "ORIGINAL_PAYMENT"
        assert c_data["refund_amount"] > 0
        assert c_data["cancellation_fee"] == 0.0
        assert "involuntary" in c_data["message"]
