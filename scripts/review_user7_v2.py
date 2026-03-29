import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User, MemoryEvent, Conversation
from database.redis_client import redis_client
from database.qdrant_client import qdrant_manager, BIOGRAPHICAL_COLLECTION, EPISODIC_COLLECTION
from sqlalchemy import select, desc

TARGET_USER_ID = "a98d44bc-9cd4-43fd-b7de-109c514ef540"
SEARCH_TERM = "로제"

async def review_memories_v2():
    print(f"--- Reviewing memories for User: {TARGET_USER_ID} (Numbered #7) for '{SEARCH_TERM}' ---")
    
    # 1. Redis
    print("\n[1] Redis:")
    patterns = [f"biographical:{TARGET_USER_ID}:*", f"session:{TARGET_USER_ID}"]
    for pattern in patterns:
        keys = await redis_client.keys(pattern)
        for key in keys:
            data = await redis_client.get(key)
            if data and SEARCH_TERM in data:
                print(f"  MATCH in Redis Key {key}: {data}")

    # 2. Qdrant
    print("\n[2] Qdrant:")
    await qdrant_manager.initialize()
    for coll in [BIOGRAPHICAL_COLLECTION, EPISODIC_COLLECTION]:
        results, _ = await qdrant_manager.client.scroll(
            collection_name=coll,
            scroll_filter={"must": [{"key": "user_id", "match": {"value": TARGET_USER_ID}}]},
            with_payload=True
        )
        for point in results:
            if SEARCH_TERM in str(point.payload):
                print(f"  MATCH in Qdrant {coll}: Payload={point.payload}")

    # 3. Conversations
    print("\n[3] Recent Conversations:")
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation).where(Conversation.user_id == TARGET_USER_ID).order_by(desc(Conversation.created_at)).limit(10)
        res = await session.execute(stmt)
        for c in res.scalars().all():
            print(f"[{c.created_at}] Msg: {c.message} | Resp: {c.response}")

if __name__ == "__main__":
    asyncio.run(review_memories_v2())
