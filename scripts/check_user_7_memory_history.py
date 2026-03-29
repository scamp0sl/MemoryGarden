import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import MemoryEvent
from sqlalchemy import select, or_

TARGET_USER_ID = "6d7c59af-b8da-485f-8510-430e4f39dfaa"

async def check_user_7_memory_history():
    print(f"--- Memory Event History for User: {TARGET_USER_ID} (7번) ---")
    async with AsyncSessionLocal() as session:
        stmt = select(MemoryEvent).where(
            (MemoryEvent.user_id == TARGET_USER_ID) &
            (
                or_(
                    MemoryEvent.entity.ilike("%로제%"),
                    MemoryEvent.old_value.ilike("%로제%"),
                    MemoryEvent.new_value.ilike("%로제%")
                )
            )
        )
        
        result = await session.execute(stmt)
        events = result.scalars().all()
        
        print(f"Found {len(events)} events:")
        for e in events:
            print(f"[{e.created_at}] Event: {e.event_type} | Entity: {e.entity} | Old: {e.old_value} | New: {e.new_value}")

if __name__ == "__main__":
    asyncio.run(check_user_7_memory_history())
