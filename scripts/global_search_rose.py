import asyncio
import os
import sys
import uuid

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client
from database.qdrant_client import qdrant_manager, BIOGRAPHICAL_COLLECTION, EPISODIC_COLLECTION
from database.postgres import AsyncSessionLocal
from database.models import User, MemoryEvent
from sqlalchemy import select

SEARCH_TERM = "로제"

async def global_search_rose():
    print(f"--- Global Search for '{SEARCH_TERM}' ---")
    
    # 1. PostgreSQL User Table
    print("\n[1] PostgreSQL Users:")
    async with AsyncSessionLocal() as session:
        stmt = select(User).where((User.name.ilike(f"%{SEARCH_TERM}%")) | (User.garden_name.ilike(f"%{SEARCH_TERM}%")))
        result = await session.execute(stmt)
        users = result.scalars().all()
        for u in users:
            print(f"  Found in User: ID={u.id}, NAME={u.name}, GARDEN={u.garden_name}")

    # 2. Redis
    print("\n[2] Redis:")
    for pattern in ["biographical:*", "session:*", "context:*", "episodic:*"]:
        keys = await redis_client.keys(pattern)
        for key in keys:
            data = await redis_client.get(key)
            if data and SEARCH_TERM in data:
                print(f"  MATCH in Redis Key {key}")

    # 3. Qdrant Biographical
    print("\n[3] Qdrant Biographical:")
    await qdrant_manager.initialize()
    if qdrant_manager.client:
        # Note: scroll without filter to see all matches (if any)
        # Actually, scroll is better with a filter if we have many points, 
        # but let's just scroll a bit and check.
        results, _ = await qdrant_manager.client.scroll(
            collection_name=BIOGRAPHICAL_COLLECTION,
            limit=100,
            with_payload=True
        )
        for point in results:
            if SEARCH_TERM in str(point.payload):
                print(f"  MATCH in Qdrant Bio: ID={point.id}, User={point.payload.get('user_id')}, Payload={point.payload}")

    # 4. Qdrant Episodic
    print("\n[4] Qdrant Episodic:")
    if qdrant_manager.client:
        results, _ = await qdrant_manager.client.scroll(
            collection_name=EPISODIC_COLLECTION,
            limit=100,
            with_payload=True
        )
        for point in results:
            if SEARCH_TERM in str(point.payload):
                print(f"  MATCH in Qdrant Episodic: ID={point.id}, User={point.payload.get('user_id')}, Payload={point.payload}")

if __name__ == "__main__":
    asyncio.run(global_search_rose())
