import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.qdrant_client import qdrant_manager, BIOGRAPHICAL_COLLECTION, EPISODIC_COLLECTION

async def search_qdrant_7():
    print("--- Searching Qdrant for '7' in any payload field ---")
    await qdrant_manager.initialize()
    if not qdrant_manager.client:
        print("Qdrant client unavailable")
        return

    for collection in [BIOGRAPHICAL_COLLECTION, EPISODIC_COLLECTION]:
        print(f"\nScanning collection: {collection}")
        # Scroll through points (limited to 500 for demo)
        results, _ = await qdrant_manager.client.scroll(
            collection_name=collection,
            limit=500,
            with_payload=True
        )
        for point in results:
            if "7" in str(point.payload):
                print(f"  MATCH: ID={point.id}, User={point.payload.get('user_id')}, Payload={point.payload}")

if __name__ == "__main__":
    asyncio.run(search_qdrant_7())
