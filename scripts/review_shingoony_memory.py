import asyncio
import os
import sys
import json
import uuid

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User, MemoryEvent
from database.redis_client import redis_client
from database.qdrant_client import qdrant_manager, BIOGRAPHICAL_COLLECTION, EPISODIC_COLLECTION
from sqlalchemy import select

TARGET_USER_ID = "1f729443-7b80-4d82-a227-c4751b3bf35f"

async def review_memories():
    user_uuid = uuid.UUID(TARGET_USER_ID)
    print(f"--- Reviewing memories for User: {TARGET_USER_ID} (shingoony@gmail.com) ---")
    
    # 1. PostgreSQL
    print("\n[1] PostgreSQL:")
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_uuid)
        if user:
            print(f"User Table -> Name: {user.name}, Garden Name: {user.garden_name}")
            if "용이" in (user.name or ""):
                print(f"  MATCH in User.name: {user.name}")
        
        stmt = select(MemoryEvent).where(MemoryEvent.user_id == user_uuid)
        result = await session.execute(stmt)
        events = result.scalars().all()
        for event in events:
            if "용이" in str(event.old_value) or "용이" in str(event.new_value) or "용이" in str(event.entity):
                print(f"  MATCH in MemoryEvent: ID={event.id}, Entity={event.entity}, Old={event.old_value}, New={event.new_value}")

    # 2. Redis
    print("\n[2] Redis:")
    patterns = [f"biographical:{TARGET_USER_ID}:*", f"session:{TARGET_USER_ID}", f"context:{TARGET_USER_ID}"]
    for pattern in patterns:
        keys = await redis_client.keys(pattern)
        for key in keys:
            data = await redis_client.get(key)
            if data and "용이" in data:
                print(f"  MATCH in Redis Key {key}: {data}")

    # 3. Qdrant Biographical
    print("\n[3] Qdrant Biographical:")
    await qdrant_manager.initialize()
    if qdrant_manager.client:
        results, _ = await qdrant_manager.client.scroll(
            collection_name=BIOGRAPHICAL_COLLECTION,
            scroll_filter={"must": [{"key": "user_id", "match": {"value": TARGET_USER_ID}}]},
            with_payload=True
        )
        for point in results:
            if "용이" in str(point.payload):
                print(f"  MATCH in Qdrant Bio: ID={point.id}, Payload={point.payload}")

    # 4. Qdrant Episodic
    print("\n[4] Qdrant Episodic:")
    if qdrant_manager.client:
        results, _ = await qdrant_manager.client.scroll(
            collection_name=EPISODIC_COLLECTION,
            scroll_filter={"must": [{"key": "user_id", "match": {"value": TARGET_USER_ID}}]},
            with_payload=True
        )
        for point in results:
            if "용이" in str(point.payload):
                print(f"  MATCH in Qdrant Episodic: ID={point.id}, Payload={point.payload}")

if __name__ == "__main__":
    asyncio.run(review_memories())
