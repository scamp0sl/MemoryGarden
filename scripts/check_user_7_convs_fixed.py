import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation
from sqlalchemy import select, desc

TARGET_USER_ID = "6d7c59af-b8da-485f-8510-430e4f39dfaa"

async def check_user_7_convs():
    print(f"--- Conversation History for User ID: {TARGET_USER_ID} (Nickname: 7번) ---")
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation).where(
            Conversation.user_id == TARGET_USER_ID
        ).order_by(desc(Conversation.created_at)).limit(30)
        
        result = await session.execute(stmt)
        convs = result.scalars().all()
        
        print(f"Found {len(convs)} conversations:")
        for conv in convs:
            print(f"[{conv.created_at}]")
            print(f"  User: {conv.message}")
            print(f"  Bot : {conv.response}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_user_7_convs())
