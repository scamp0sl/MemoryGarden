import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation, User
from sqlalchemy import select, desc

TARGET_USER_ID = "a98d44bc-9cd4-43fd-b7de-109c514ef540"

async def check_user7_convs():
    print(f"--- Conversation History for User: {TARGET_USER_ID} (User #7) ---")
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
    asyncio.run(check_user7_convs())
