import pytest
import asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from database.init_db import init_and_seed_db

@pytest.mark.asyncio
async def test_search_flight_inventory():
    """REQ-SRC-12: Search endpoint returns live seat availability per class."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/flights/search?origin=LHR&destination=DXB")
        assert res.status_code == 200
        flights = res.json()
        assert len(flights) >= 1
        ba105 = next(f for f in flights if f["flight_number"] == "BA105")
        assert ba105["total_capacity"] == 100
        
        # Verify 3 classes: First, Business, Economy
        classes = {c["class_code"]: c for c in ba105["classes"]}
        assert classes["FIRST"]["total_seats"] == 20
        assert classes["BUSINESS"]["total_seats"] == 30
        assert classes["ECONOMY"]["total_seats"] == 50

@pytest.mark.asyncio
async def test_idempotency_key_deduplication():
    """REQ-BKG-19, REQ-INF-52: Duplicate requests with same Idempotency-Key return cached response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login
        login_res = await ac.post("/api/v1/auth/login", json={"email": "superadmin@airline.com", "password": "Admin123!"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": f"test-idemp-{uuid.uuid4()}"}

        payload = {
            "flight_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "class_code": "ECONOMY",
            "fare_type": "FLEXIBLE",
            "passengers": [{"first_name": "Alice", "last_name": "Smith", "passport_number": "P123456"}]
        }

        # First request
        res1 = await ac.post("/api/v1/bookings", json=payload, headers=headers)
        assert res1.status_code == 201
        data1 = res1.json()
        pnr = data1["booking_reference"]

        # Retry with identical Idempotency-Key
        res2 = await ac.post("/api/v1/bookings", json=payload, headers=headers)
        assert res2.status_code in [200, 201]
        data2 = res2.json()
        assert data2["booking_reference"] == pnr # Must return exact same booking reference

@pytest.mark.asyncio
async def test_basic_economy_rejects_seat_selection():
    """REQ-SRC-13: Basic economy does not allow advance seat choice."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post("/api/v1/auth/login", json={"email": "superadmin@airline.com", "password": "Admin123!"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "flight_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "class_code": "ECONOMY",
            "fare_type": "BASIC_ECONOMY",
            "passengers": [{"first_name": "Bob", "last_name": "Brown", "passport_number": "P99999", "seat_id": str(uuid.uuid4())}]
        }
        res = await ac.post("/api/v1/bookings", json=payload, headers=headers)
        assert res.status_code == 400
        assert "Seat selection not permitted for Basic Economy" in res.json()["detail"]

@pytest.mark.asyncio
async def test_group_booking_full_fail_policy():
    """REQ-BKG-21: Group booking where seats are insufficient under FULL_FAIL policy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post("/api/v1/auth/login", json={"email": "superadmin@airline.com", "password": "Admin123!"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to book 25 First Class seats (only 20 exist)
        pax = [{"first_name": f"P{i}", "last_name": "Group", "passport_number": f"P{i:04d}"} for i in range(25)]
        payload = {
            "flight_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "class_code": "FIRST",
            "fare_type": "FLEXIBLE",
            "partial_policy": "FULL_FAIL",
            "passengers": pax
        }
        res = await ac.post("/api/v1/bookings", json=payload, headers=headers)
        assert res.status_code == 409
        assert "FULL_FAIL" in res.json()["detail"]
