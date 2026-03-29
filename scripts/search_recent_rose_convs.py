import asyncio
import os
import sys
from datetime import datetime, timedelta

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation, User
from sqlalchemy import select, desc

async def search_recent_rose_conversations():
    print("--- Searching for '로제' in Recent Conversations (Last 48 Hours) ---")
    cutoff = datetime.now() - timedelta(days=2)
    
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation, User.name, User.kakao_id).join(User, Conversation.user_id == User.id).where(
            (Conversation.created_at >= cutoff) &
            ((Conversation.message.ilike("%로제%")) | (Conversation.response.ilike("%로제%")))
        ).order_by(desc(Conversation.created_at))
        
        result = await session.execute(stmt)
        convs = result.all()
        
        print(f"Found {len(convs)} matches:")
        for conv, name, kakao_id in convs:
            print(f"[{conv.created_at}] User: {name} (ID: {conv.user_id}, Kakao: {kakao_id})")
            print(f"  Message: {conv.message}")
            print(f"  Response: {conv.response}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(search_recent_rose_conversations())
