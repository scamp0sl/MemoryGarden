import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User, Guardian
from sqlalchemy import select, or_

async def find_moongoory():
    print("--- Searching for 'moongoory' across all possible fields ---")
    async with AsyncSessionLocal() as session:
        # 1. Search Users (including deleted)
        print("\n[1] Users Table:")
        stmt = select(User).where(
            or_(
                User.email.ilike("%moongoory%"),
                User.name.ilike("%moongoory%"),
                User.name.ilike("%문구리%")
            )
        ).execution_options(include_deleted=True) # If supported or manual filter
        # Better: just select all and filter in python if unsure about model's soft-delete logic
        res = await session.execute(select(User))
        for u in res.scalars().all():
            if any(term in str(val).lower() for term in ["moongoory", "문구리"] for val in [u.email, u.name, u.kakao_id]):
                print(f"  User Found: ID={u.id} | Email={u.email} | Name={u.name} | Deleted={u.deleted_at}")

        # 2. Search Guardians
        print("\n[2] Guardians Table:")
        res = await session.execute(select(Guardian))
        for g in res.scalars().all():
             if any(term in str(val).lower() for term in ["moongoory", "문구리"] for val in [g.email, g.name]):
                print(f"  Guardian Found: ID={g.id} | Email={g.email} | Name={g.name}")

if __name__ == "__main__":
    asyncio.run(find_moongoory())
