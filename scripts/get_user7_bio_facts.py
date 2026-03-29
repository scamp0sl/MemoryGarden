import asyncio
import os
import sys
import json

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client
from database.qdrant_client import qdrant_manager, BIOGRAPHICAL_COLLECTION

TARGET_USER_ID = "a98d44bc-9cd4-43fd-b7de-109c514ef540"

async def get_all_bio_facts():
    print(f"--- All Biographical Facts for User: {TARGET_USER_ID} ---")
    
    # 1. Redis
    print("\n[1] Redis:")
    keys = await redis_client.keys(f"biographical:{TARGET_USER_ID}:*")
    for key in keys:
        data = await redis_client.get(key)
        print(f"  {key}: {data}")

    # 2. Qdrant
    print("\n[2] Qdrant:")
    await qdrant_manager.initialize()
    if qdrant_manager.client:
        results, _ = await qdrant_manager.client.scroll(
            collection_name=BIOGRAPHICAL_COLLECTION,
            scroll_filter={"must": [{"key": "user_id", "match": {"value": TARGET_USER_ID}}]},
            with_payload=True
        )
        for point in results:
            print(f"  ID={point.id}, Payload={point.payload}")

if __name__ == "__main__":
    asyncio.run(get_all_bio_facts())
