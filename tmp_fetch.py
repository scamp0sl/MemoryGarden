import asyncio
from sqlalchemy import select
from database.postgres import AsyncSessionLocal
from database.models import Conversation, User

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Conversation, User.name)
            .join(User, Conversation.user_id == User.id)
            .order_by(Conversation.created_at.desc())
            .limit(30)
        )
        convs = result.all()
        for idx, (conv, user_name) in enumerate(reversed(convs)):
            print(f"--- Turn {idx} | User: {user_name} | Created: {conv.created_at} ---")
            print(f"USER: {conv.message}")
            print(f"AI:   {conv.response}\n")

if __name__ == "__main__":
    asyncio.run(main())
