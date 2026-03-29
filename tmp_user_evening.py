import asyncio
from datetime import datetime
from sqlalchemy import select
from database.postgres import AsyncSessionLocal
from database.models import Conversation, User
from uuid import UUID

async def main():
    user_uuid = UUID("aa96e75d-70e2-4546-9001-043cc5db047d")
    # Last night 18:00 - today 00:00
    start = datetime(2026, 3, 19, 18, 0, 0)
    end   = datetime(2026, 3, 20, 0, 0, 0)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_uuid)
            .where(Conversation.created_at >= start)
            .where(Conversation.created_at <= end)
            .order_by(Conversation.created_at.asc())
        )
        convs = result.scalars().all()
        print(f"Total convs for user aa96e75d (18:00-24:00 yesterday): {len(convs)}")
        for idx, conv in enumerate(convs):
            print(f"--- Turn {idx} | Created: {conv.created_at} | Category: {conv.category} ---")
            print(f"USER: {conv.message}")
            print(f"AI:   {conv.response}\n")

if __name__ == "__main__":
    asyncio.run(main())
