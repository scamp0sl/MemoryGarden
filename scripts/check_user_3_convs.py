import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation
from sqlalchemy import select, desc

TARGET_USER_ID = "ccc04a7a-4708-47cd-8bd0-9e10a1f77f21"

async def check_user_3_convs():
    print(f"--- Recent Conversations for User ID: {TARGET_USER_ID} (User #3) ---")
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation).where(
            Conversation.user_id == TARGET_USER_ID
        ).order_by(desc(Conversation.created_at)).limit(20)
        
        result = await session.execute(stmt)
        convs = result.scalars().all()
        
        print(f"Found {len(convs)} conversations:")
        for conv in convs:
            print(f"[{conv.created_at}]")
            print(f"  User: {conv.message}")
            print(f"  Bot : {conv.response}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_user_3_convs())
