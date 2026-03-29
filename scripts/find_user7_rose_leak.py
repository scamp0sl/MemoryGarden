import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation, User
from sqlalchemy import select, desc

TARGET_USER_ID = "6d7c59af-b8da-485f-8510-430e4f39dfaa"

async def find_leak_instances():
    print(f"--- Searching for '로제' in Responses to User: {TARGET_USER_ID} ---")
    async with AsyncSessionLocal() as session:
        # Get all conversations for this user
        stmt = select(Conversation).where(
            Conversation.user_id == TARGET_USER_ID
        ).order_by(desc(Conversation.created_at))
        
        result = await session.execute(stmt)
        convs = result.scalars().all()
        
        found = 0
        for conv in convs:
            if "로제" in (conv.response or ""):
                print(f"[{conv.created_at}] MATCH FOUND!")
                print(f"  User MSG: {conv.message}")
                print(f"  AI RESP : {conv.response}")
                print("-" * 20)
                found += 1
        
        print(f"Total instances found: {found}")

if __name__ == "__main__":
    asyncio.run(find_leak_instances())
