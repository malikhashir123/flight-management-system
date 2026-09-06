import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from backend.app.core.database import engine, AsyncSessionLocal, Base
from backend.app.core.security import get_password_hash
from backend.app.models.all_models import (
    User, Flight, FlightClass, Seat, Booking, Passenger, WaitlistEntry
)
from backend.app.models.enums import (
    UserRole, LoyaltyTier, FlightStatus, SeatClassCode, FareType, BookingStatus
)

async def init_and_seed_db():
    print("Creating all tables in database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        res = await session.execute(select(User).where(User.email == "superadmin@airline.com"))
        if res.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        print("Seeding initial users...")
        superadmin = User(
            id="11111111-1111-1111-1111-111111111111",
            email="superadmin@airline.com",
            hashed_password=get_password_hash("Admin123!"),
            full_name="Chief Operations Admin",
            role=UserRole.SUPER_ADMIN.value,
            loyalty_tier=LoyaltyTier.PLATINUM.value
        )
        ops_agent = User(
            id="22222222-2222-2222-2222-222222222222",
            email="ops.agent@airline.com",
            hashed_password=get_password_hash("Agent123!"),
            full_name="LHR Gate Agent",
            role=UserRole.OPS_AGENT.value,
            loyalty_tier=LoyaltyTier.GOLD.value
        )
        passenger1 = User(
            id="33333333-3333-3333-3333-333333333333",
            email="john.doe@example.com",
            hashed_password=get_password_hash("Pass123!"),
            full_name="John Doe (Platinum Member)",
            role=UserRole.PASSENGER.value,
            loyalty_tier=LoyaltyTier.PLATINUM.value
        )
        passenger2 = User(
            id="44444444-4444-4444-4444-444444444444",
            email="jane.smith@example.com",
            hashed_password=get_password_hash("Pass123!"),
            full_name="Jane Smith (Standard Member)",
            role=UserRole.PASSENGER.value,
            loyalty_tier=LoyaltyTier.NONE.value
        )
        session.add_all([superadmin, ops_agent, passenger1, passenger2])

        # Seed UK -> Dubai Flight BA105 (REQ-ADM-02: 100 seats — 20 First, 30 Business, 50 Economy)
        print("Seeding UK -> Dubai Flight BA105 (20 First, 30 Business, 50 Economy)...")
        now = datetime.now(timezone.utc)
        dep_time = (now + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
        arr_time = (now + timedelta(days=1)).replace(hour=12, minute=30, second=0, microsecond=0)

        flight_ba105 = Flight(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            flight_number="BA105",
            origin="LHR",
            destination="DXB",
            origin_tz="Europe/London",
            destination_tz="Asia/Dubai",
            departure_time=dep_time,
            arrival_time=arr_time,
            total_capacity=100,
            status=FlightStatus.SCHEDULED.value,
            schedule_version=1
        )
        session.add(flight_ba105)

        fc_first = FlightClass(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0001",
            flight_id=flight_ba105.id,
            class_code=SeatClassCode.FIRST.value,
            total_seats=20,
            booked_seats=0,
            held_seats=0,
            base_fare=1500.00,
            overbooking_buffer_pct=0,
            max_overbooking_seats=0,
            cutoff_hours_before_departure=1
        )
        fc_biz = FlightClass(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0002",
            flight_id=flight_ba105.id,
            class_code=SeatClassCode.BUSINESS.value,
            total_seats=30,
            booked_seats=0,
            held_seats=0,
            base_fare=750.00,
            overbooking_buffer_pct=0,
            max_overbooking_seats=0,
            cutoff_hours_before_departure=1
        )
        fc_eco = FlightClass(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0003",
            flight_id=flight_ba105.id,
            class_code=SeatClassCode.ECONOMY.value,
            total_seats=50,
            booked_seats=0,
            held_seats=0,
            base_fare=250.00,
            overbooking_buffer_pct=6,
            max_overbooking_seats=3,
            cutoff_hours_before_departure=3
        )
        session.add_all([fc_first, fc_biz, fc_eco])

        # Seed physical seats for BA105
        print("Seeding 100 physical seats...")
        seats = []
        # First class: rows 1-5, cols A-D (20 seats)
        for r in range(1, 6):
            for c in ["A", "B", "C", "D"]:
                seats.append(
                    Seat(
                        id=str(uuid.uuid4()),
                        flight_id=flight_ba105.id,
                        seat_number=f"{r}{c}",
                        class_code=SeatClassCode.FIRST.value,
                        seat_row=r,
                        seat_column=c,
                        is_active=True
                    )
                )
        # Business class: rows 6-10, cols A-F (30 seats)
        for r in range(6, 11):
            for c in ["A", "B", "C", "D", "E", "F"]:
                seats.append(
                    Seat(
                        id=str(uuid.uuid4()),
                        flight_id=flight_ba105.id,
                        seat_number=f"{r}{c}",
                        class_code=SeatClassCode.BUSINESS.value,
                        seat_row=r,
                        seat_column=c,
                        is_active=True
                    )
                )
        # Economy class: rows 11-18 cols A-F (48 seats) + row 19 cols A-B (2 seats) = 50 seats
        for r in range(11, 19):
            for c in ["A", "B", "C", "D", "E", "F"]:
                seats.append(
                    Seat(
                        id=str(uuid.uuid4()),
                        flight_id=flight_ba105.id,
                        seat_number=f"{r}{c}",
                        class_code=SeatClassCode.ECONOMY.value,
                        seat_row=r,
                        seat_column=c,
                        is_active=True
                    )
                )
        seats.append(
            Seat(
                id=str(uuid.uuid4()),
                flight_id=flight_ba105.id,
                seat_number="19A",
                class_code=SeatClassCode.ECONOMY.value,
                seat_row=19,
                seat_column="A",
                is_active=True
            )
        )
        seats.append(
            Seat(
                id=str(uuid.uuid4()),
                flight_id=flight_ba105.id,
                seat_number="19B",
                class_code=SeatClassCode.ECONOMY.value,
                seat_row=19,
                seat_column="B",
                is_active=True
            )
        )
        session.add_all(seats)

        # Seed Secondary Flight: LHR -> JFK (BA177)
        dep_jfk = (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        arr_jfk = (now + timedelta(days=2)).replace(hour=13, minute=0, second=0, microsecond=0)
        flight_ba177 = Flight(
            id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            flight_number="BA177",
            origin="LHR",
            destination="JFK",
            origin_tz="Europe/London",
            destination_tz="America/New_York",
            departure_time=dep_jfk,
            arrival_time=arr_jfk,
            total_capacity=100,
            status=FlightStatus.SCHEDULED.value,
            schedule_version=1
        )
        session.add(flight_ba177)
        session.add_all([
            FlightClass(
                id=str(uuid.uuid4()),
                flight_id=flight_ba177.id,
                class_code=SeatClassCode.FIRST.value,
                total_seats=20,
                booked_seats=0,
                held_seats=0,
                base_fare=2000.00,
                cutoff_hours_before_departure=1
            ),
            FlightClass(
                id=str(uuid.uuid4()),
                flight_id=flight_ba177.id,
                class_code=SeatClassCode.BUSINESS.value,
                total_seats=30,
                booked_seats=0,
                held_seats=0,
                base_fare=1100.00,
                cutoff_hours_before_departure=1
            ),
            FlightClass(
                id=str(uuid.uuid4()),
                flight_id=flight_ba177.id,
                class_code=SeatClassCode.ECONOMY.value,
                total_seats=50,
                booked_seats=0,
                held_seats=0,
                base_fare=450.00,
                cutoff_hours_before_departure=3
            )
        ])

        await session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(init_and_seed_db())
