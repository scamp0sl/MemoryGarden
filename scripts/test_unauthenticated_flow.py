import asyncio
import os
import sys
import json
from unittest.mock import AsyncMock, MagicMock

# Add project root to sys.path
sys.path.append(os.getcwd())

from api.routes.kakao_webhook import kakao_webhook
from fastapi import BackgroundTasks, Request
from database.postgres import AsyncSessionLocal
from database.models import User
from sqlalchemy import select

async def test_unauthenticated_flow():
    # User key from audit: ch_PJEQmqlFZfJw
    user_key = "ch_PJEQmqlFZfJw"
    
    background_tasks = BackgroundTasks()
    
    async with AsyncSessionLocal() as db:
        # 1. Inspect DB before test
        result = await db.execute(select(User).where(User.kakao_id == user_key))
        user = result.scalar_one_or_none()
        if user:
            print(f"--- DB User Status (Before) ---")
            print(f"ID: {user.id}")
            print(f"Name: {user.name}")
            print(f"Kakao ID: {user.kakao_id}")
            print(f"Channel Key: {user.kakao_channel_user_key}")
            print(f"Has Token: {bool(user.kakao_access_token)}")
            print(f"Onboarding Day: {user.onboarding_day}")
        else:
            print(f"User with kakao_id {user_key} NOT found in DB.")

        # 2. Mock Webhook Request
        mock_payload = {
            "userRequest": {
                "user": {
                    "id": user_key,
                    "type": "accountId",
                    "properties": {
                        "plusfriendUserKey": user_key
                    }
                },
                "utterance": "안녕하세요",
                "callbackUrl": "http://localhost:8002/callback"
            }
        }
        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value=mock_payload)
        
        print("\n--- Running kakao_webhook() ---")
        response = await kakao_webhook(mock_request, background_tasks, db=db)
        
        print("\n--- Webhook Response ---")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        # 3. Verify Response
        outputs = response.get("template", {}).get("outputs", [])
        has_guidance = False
        for output in outputs:
            if "basicCard" in output:
                description = output["basicCard"].get("description", "")
                if "로그인 절차를 다시 한번 진행" in description:
                    has_guidance = True
                    print("\n✅ Success: Guidance message with button found in response.")
            elif "simpleText" in output:
                print(f"SimpleText found: {output['simpleText'].get('text')}")
        
        if not has_guidance:
            print("\n❌ Error: Guidance message NOT found in response.")

if __name__ == "__main__":
    asyncio.run(test_unauthenticated_flow())
