import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User, MemoryEvent, Conversation
from sqlalchemy import select, or_

async def master_search_rose():
    print("--- Master Database Search for '로제' ---")
    async with AsyncSessionLocal() as session:
        # 1. Users
        print("\n[1] Users Table:")
        stmt = select(User).where(or_(User.name.ilike("%로제%"), User.garden_name.ilike("%로제%")))
        res = await session.execute(stmt)
        users = res.scalars().all()
        for u in users:
            print(f"  User: {u.id} | Name: {u.name} | Garden: {u.garden_name}")

        # 2. MemoryEvents
        print("\n[2] MemoryEvents Table:")
        stmt = select(MemoryEvent, User.name).join(User, MemoryEvent.user_id == User.id).where(
            or_(
                MemoryEvent.entity.ilike("%로제%"),
                MemoryEvent.old_value.ilike("%로제%"),
                MemoryEvent.new_value.ilike("%로제%")
            )
        )
        res = await session.execute(stmt)
        for event, user_name in res.all():
            print(f"  Event: {user_name} ({event.user_id}) | Entity: {event.entity} | New: {event.new_value}")

        # 3. Conversations
        print("\n[3] Conversations Table (Last 10 matches):")
        stmt = select(Conversation, User.name).join(User, Conversation.user_id == User.id).where(
            or_(Conversation.message.ilike("%로제%"), Conversation.response.ilike("%로제%"))
        ).order_by(Conversation.created_at.desc()).limit(10)
        res = await session.execute(stmt)
        for conv, user_name in res.all():
            print(f"  Conv: {user_name} ({conv.user_id}) | Msg: {conv.message[:50]}...")

if __name__ == "__main__":
    asyncio.run(master_search_rose())
