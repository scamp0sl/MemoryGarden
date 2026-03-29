import asyncio
import os
import sys

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client
from database.qdrant_client import qdrant_manager, BIOGRAPHICAL_COLLECTION, EPISODIC_COLLECTION

async def cleanup():
    print("Starting cleanup of poisoned memories...")
    
    # 1. Redis Biographical, Episodic, Session keys
    deleted_redis = 0
    for pattern in ["biographical:*", "episodic:*", "session:*"]:
        keys = await redis_client.keys(pattern)
        for key in keys:
            data = await redis_client.get_json(key)
            if data:
                data_str = str(data)
                if "용이" in data_str or "로제" in data_str:
                    await redis_client.delete(key)
                    print(f"Deleted corrupted Redis key ({pattern}): {key}")
                    deleted_redis += 1
                
    print(f"Total Redis biographical keys deleted: {deleted_redis}")
            
    # 2. Qdrant
    await qdrant_manager.initialize()
    if qdrant_manager.client:
        for collection in [BIOGRAPHICAL_COLLECTION, EPISODIC_COLLECTION]:
            try:
                # Scroll all points
                results, _ = await qdrant_manager.client.scroll(
                    collection_name=collection,
                    limit=10000,
                    with_payload=True
                )
                points_to_delete = []
                for point in results:
                    payload_str = str(point.payload)
                    if "용이" in payload_str or "로제" in payload_str:
                        points_to_delete.append(point.id)
                
                if points_to_delete:
                    await qdrant_manager.client.delete(
                        collection_name=collection,
                        points_selector=points_to_delete
                    )
                    print(f"Deleted {len(points_to_delete)} corrupted points from Qdrant {collection}")
                else:
                    print(f"No corrupted points found in Qdrant {collection}")
            except Exception as e:
                print(f"Error checking {collection}: {e}")
    else:
        print("Qdrant client not available.")
        
    print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup())
