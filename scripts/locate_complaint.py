import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation
from sqlalchemy import select, desc

async def locate_complaint():
    print("--- Locating '나는 7번님인데...' Message ---")
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation).where(
            Conversation.message.ilike("%나는 7번님인데%")
        )
        result = await session.execute(stmt)
        conv = result.scalar_one_or_none()
        
        if conv:
            print(f"MATCH FOUND!")
            print(f"  User ID  : {conv.user_id}")
            print(f"  Timestamp: {conv.created_at}")
            print(f"  Message  : {conv.message}")
            print(f"  Response : {conv.response}")
            
            # Now find neighbors
            print("\nAdjacent Conversations:")
            stmt_adj = select(Conversation).where(
                (Conversation.user_id == conv.user_id) &
                (Conversation.created_at <= conv.created_at)
            ).order_by(desc(Conversation.created_at)).limit(5)
            
            results_adj = await session.execute(stmt_adj)
            for c in results_adj.scalars().all():
                print(f"[{c.created_at}] User: {c.message} | Resp: {c.response}")
        else:
            print("Message not found.")

if __name__ == "__main__":
    asyncio.run(locate_complaint())
