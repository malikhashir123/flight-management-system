import asyncio
import uuid
import sys
import os

# Add the project root to the python path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from backend.app.core.database import async_session
from backend.app.models.flight import Flight, FlightClass
from backend.app.models.seat import Seat

async def seed_missing_seats():
    async with async_session() as db:
        # Get all flights
        flights_res = await db.execute(select(Flight))
        flights = flights_res.scalars().all()
        
        for flight in flights:
            # Check if this flight already has seats
            seats_res = await db.execute(select(Seat).where(Seat.flight_id == flight.id))
            existing_seats = seats_res.scalars().all()
            if len(existing_seats) > 0:
                continue # Already has physical seats mapped
            
            # Fetch capacities
            classes_res = await db.execute(select(FlightClass).where(FlightClass.flight_id == flight.id))
            flight_classes = classes_res.scalars().all()
            
            new_seats = []
            row_counter = 1
            for fc in flight_classes:
                capacity = fc.total_seats
                if capacity == 0:
                    continue
                
                rows = (capacity // 4) + (1 if capacity % 4 != 0 else 0)
                columns = ['A', 'B', 'C', 'D']
                
                seat_count = 0
                for r in range(row_counter, row_counter + rows):
                    for c in columns:
                        if seat_count >= capacity:
                            break
                        new_seats.append(Seat(
                            id=str(uuid.uuid4()),
                            flight_id=flight.id,
                            class_code=fc.class_code,
                            seat_number=f"{r}{c}",
                            seat_row=r,
                            seat_column=c,
                            is_active=True
                        ))
                        seat_count += 1
                row_counter += rows
                        
            if new_seats:
                db.add_all(new_seats)
                await db.commit()
                print(f"Seeded {len(new_seats)} physical seats for Flight {flight.flight_number}")

if __name__ == "__main__":
    asyncio.run(seed_missing_seats())
