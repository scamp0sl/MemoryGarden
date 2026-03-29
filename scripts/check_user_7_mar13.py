import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation
from sqlalchemy import select

TARGET_USER_ID = "6d7c59af-b8da-485f-8510-430e4f39dfaa"

async def check_user_7_mar13():
    print(f"--- March 13th Conversations for User: {TARGET_USER_ID} (7번) ---")
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation).where(
            (Conversation.user_id == TARGET_USER_ID) &
            (Conversation.created_at >= "2026-03-13 00:00:00") &
            (Conversation.created_at < "2026-03-14 00:00:00")
        ).order_by(Conversation.created_at.asc())
        
        result = await session.execute(stmt)
        for c in result.scalars().all():
            print(f"[{c.created_at}] User: {c.message} | Resp: {c.response}")

if __name__ == "__main__":
    asyncio.run(check_user_7_mar13())
