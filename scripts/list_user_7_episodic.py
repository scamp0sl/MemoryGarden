import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.qdrant_client import qdrant_manager, EPISODIC_COLLECTION

TARGET_USER_ID = "6d7c59af-b8da-485f-8510-430e4f39dfaa"

async def list_user_7_episodic():
    print(f"--- All Episodic Memories for User: {TARGET_USER_ID} (Nickname: 7번) ---")
    await qdrant_manager.initialize()
    if qdrant_manager.client:
        results, _ = await qdrant_manager.client.scroll(
            collection_name=EPISODIC_COLLECTION,
            scroll_filter={"must": [{"key": "user_id", "match": {"value": TARGET_USER_ID}}]},
            limit=100,
            with_payload=True
        )
        print(f"Found {len(results)} points:")
        for point in results:
            print(f"  ID={point.id}, Payload={point.payload}")
    else:
        print("Qdrant client unavailable")

if __name__ == "__main__":
    asyncio.run(list_user_7_episodic())
