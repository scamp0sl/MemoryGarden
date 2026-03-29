import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import MemoryEvent, User
from sqlalchemy import select, or_

async def search_events():
    print("--- Searching MemoryEvents for '로제' or '7' ---")
    async with AsyncSessionLocal() as session:
        stmt = select(MemoryEvent, User.name).join(User, MemoryEvent.user_id == User.id).where(
            or_(
                MemoryEvent.entity.ilike("%로제%"),
                MemoryEvent.old_value.ilike("%로제%"),
                MemoryEvent.new_value.ilike("%로제%"),
                MemoryEvent.entity.ilike("%7%"),
                MemoryEvent.old_value.ilike("%7%"),
                MemoryEvent.new_value.ilike("%7%")
            )
        )
        result = await session.execute(stmt)
        events = result.all()
        
        print(f"Found {len(events)} events:")
        for event, user_name in events:
            print(f"- User: {user_name} (ID: {event.user_id})")
            print(f"  Entity: {event.entity}, Old: {event.old_value}, New: {event.new_value}")

if __name__ == "__main__":
    asyncio.run(search_events())
