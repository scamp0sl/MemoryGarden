import asyncio
import os
import sys
from datetime import datetime
from uuid import uuid4

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client
from database.qdrant_client import qdrant_manager, BIOGRAPHICAL_COLLECTION, EPISODIC_COLLECTION
from qdrant_client.models import PointStruct
from core.nlp.embedder import Embedder

# Hardcoded true memories based on log recovery
RESTORE_DATA = [
    {
        "user_id": "ccc04a7a-4708-47cd-8bd0-9e10a1f77f21",
        "category": "biographical",
        "entity": "dog_name",
        "value": "로제",
        "fact_category": "object",
        "fact_type": "immutable",
        "confidence": 0.95,
        "context": "사용자가 반려견 로제에 대해 언급함"
    },
    {
        "user_id": "ccc04a7a-4708-47cd-8bd0-9e10a1f77f21",
        "category": "episodic",
        "content": "강아지 시절 태어난 지 2달도 안 되어 집에 처음 왔다.",
        "fact_category": "event",
        "confidence": 0.95,
        "importance": 0.8
    },
    {
        "user_id": "1f729443-7b80-4d82-a227-c4751b3bf35f",
        "category": "biographical",
        "entity": "name",
        "value": "용이",
        "fact_category": "object",
        "fact_type": "immutable",
        "confidence": 0.95,
        "context": "사용자가 본인의 이름을 용이라고 알려줌"
    }
]

async def restore():
    print("Starting restoration of legitimate memories...")
    
    await qdrant_manager.initialize()
    embedder = Embedder()
    
    for item in RESTORE_DATA:
        user_id = item["user_id"]
        timestamp = datetime.now().isoformat()
        
        if item["category"] == "biographical":
            # Redis restoration
            entity = item["entity"]
            cache_key = f"biographical:{user_id}:{entity}"
            fact_data = {
                "user_id": user_id,
                "entity": entity,
                "value": item["value"],
                "category": item["fact_category"],
                "fact_type": item["fact_type"],
                "confidence": item["confidence"],
                "context": item["context"],
                "timestamp": timestamp,
            }
            await redis_client.set_json(cache_key, fact_data, ttl=86400 * 365)
            print(f"Restored Redis key: {cache_key}")
            
            # Qdrant restoration
            if qdrant_manager.client:
                embed_text = f"{entity}: {item['value']}"
                vector = await embedder.embed(embed_text)
                point_id = str(uuid4())
                await qdrant_manager.client.upsert(
                    collection_name=BIOGRAPHICAL_COLLECTION,
                    points=[PointStruct(
                        id=point_id,
                        vector=vector.tolist(),
                        payload=fact_data,
                    )]
                )
                print(f"Restored Qdrant point (biographical) for {user_id}: {entity}")
                
        elif item["category"] == "episodic":
            # Qdrant restoration only
            if qdrant_manager.client:
                vector = await embedder.embed(item["content"])
                point_id = str(uuid4())
                payload = {
                    "user_id": user_id,
                    "content": item["content"],
                    "category": item["fact_category"],
                    "confidence": item["confidence"],
                    "importance": item["importance"],
                    "timestamp": timestamp,
                    "metadata": {}
                }
                await qdrant_manager.client.upsert(
                    collection_name=EPISODIC_COLLECTION,
                    points=[PointStruct(
                        id=point_id,
                        vector=vector.tolist(),
                        payload=payload,
                    )]
                )
                print(f"Restored Qdrant point (episodic) for {user_id}")

    print("Restoration complete.")

if __name__ == "__main__":
    asyncio.run(restore())
