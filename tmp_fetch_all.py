import asyncio
from datetime import datetime
from sqlalchemy import select
from database.postgres import AsyncSessionLocal
from database.models import Conversation, User

async def main():
    target_time = datetime(2026, 3, 19, 18, 0, 0)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Conversation, User.name)
            .join(User, Conversation.user_id == User.id)
            .where(Conversation.created_at >= target_time)
            .order_by(Conversation.created_at.asc())
        )
        convs = result.all()
        print(f"Total conversations since {target_time}: {len(convs)}")
        for idx, (conv, user_name) in enumerate(convs):
            print(f"--- Turn {idx} | User: {user_name} | Created: {conv.created_at} | Category: {conv.category} ---")
            print(f"USER: {conv.message}")
            print(f"AI:   {conv.response}\n")

if __name__ == "__main__":
    asyncio.run(main())
