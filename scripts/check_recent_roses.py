import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation, User
from sqlalchemy import select, desc

async def check_recent_roses():
    print("--- Searching Recent Conversations for '로제' ---")
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation, User.name).join(User, Conversation.user_id == User.id).where(
            (Conversation.message.ilike("%로제%")) | (Conversation.response.ilike("%로제%"))
        ).order_by(desc(Conversation.created_at)).limit(30)
        
        result = await session.execute(stmt)
        convs = result.all()
        
        print(f"Found {len(convs)} conversations:")
        for conv, user_name in convs:
            print(f"- User: {user_name} (ID: {conv.user_id})")
            print(f"  Message: {conv.message}")
            print(f"  Response: {conv.response}")
            print(f"  Created At: {conv.created_at}")

if __name__ == "__main__":
    asyncio.run(check_recent_roses())
