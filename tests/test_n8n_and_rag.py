import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from database.init_db import init_and_seed_db
from n8n.runner.standalone_worker import runner

@pytest.mark.asyncio
async def test_waitlist_priority_ranking():
    """REQ-WST-28, REQ-WST-29: Waitlist priority ranking by loyalty tier."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_email = f"vip.{uuid.uuid4().hex[:6]}@airline.com"
        reg = await ac.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Password123!",
            "full_name": "VIP Platinum Passenger",
            "role": "PASSENGER",
            "loyalty_tier": "PLATINUM"
        })
        token1 = (await ac.post("/api/v1/auth/login", json={"email": unique_email, "password": "Password123!"})).json()["access_token"]
        
        w1 = await ac.post(
            "/api/v1/waitlist/flights/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            json={"class_code": "FIRST", "passenger_name": "VIP Platinum"},
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert w1.status_code == 201
        assert w1.json()["priority_score"] == 4000 # Platinum = 4000

@pytest.mark.asyncio
async def test_rag_policy_grounding_basic_economy():
    """REQ-FRD-37: Grounded RAG draft reflects specific booking's Basic Economy fare rule."""
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
            "passengers": [{"first_name": "Grace", "last_name": "Hopper", "passport_number": "P77777"}]
        }, headers=headers)
        pnr = b_res.json()["booking_reference"]

        # Submit inquiry referencing PNR
        inq_res = await ac.post("/api/v1/support/inquiry", json={
            "booking_reference": pnr,
            "customer_email": "grace@example.com",
            "query": "Can I get a refund if I cancel?"
        })
        assert inq_res.status_code == 201
        draft = inq_res.json()
        assert draft["approval_status"] == "PENDING_REVIEW"
        # Grounding check: RAG draft MUST cite Basic Economy terms!
        assert "BASIC ECONOMY" in draft["rag_drafted_answer"]
        assert "non-refundable" in draft["rag_drafted_answer"]

@pytest.mark.asyncio
async def test_rag_human_approval_gate():
    """REQ-FRD-38, REQ-APP-43: Draft requires supervisor approval before dispatch."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post("/api/v1/auth/login", json={"email": "superadmin@airline.com", "password": "Admin123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Submit draft
        inq_res = await ac.post("/api/v1/support/inquiry", json={
            "customer_email": "tester@example.com",
            "query": "What are your check-in luggage rules?"
        })
        draft_id = inq_res.json()["id"]

        # Supervisor approves draft
        app_res = await ac.post(
            f"/api/v1/support/drafts/{draft_id}/approve",
            json={"action": "APPROVE", "notes": "Approved by supervisor."},
            headers=headers
        )
        assert app_res.status_code == 200
        assert app_res.json()["status"] == "APPROVED"
