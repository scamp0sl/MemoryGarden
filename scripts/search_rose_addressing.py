import asyncio
import os
import sys
from datetime import datetime

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation, User
from sqlalchemy import select

async def search_rose_addressing():
    print("--- Searching for Direct Addressing as '로제' Today ---")
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation, User.name).join(User, Conversation.user_id == User.id).where(
            (Conversation.created_at >= today_start) &
            (
                (Conversation.response.ilike("%로제님%")) |
                (Conversation.response.ilike("%로제 씨%")) |
                (Conversation.response.ilike("%로제야%")) |
                (Conversation.response.ilike("%로제!%"))
            )
        )
        
        result = await session.execute(stmt)
        for conv, user_name in result.all():
            print(f"[{conv.created_at}] User ID: {conv.user_id} (DB Name: {user_name})")
            print(f"  Msg : {conv.message}")
            print(f"  Resp: {conv.response}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(search_rose_addressing())
