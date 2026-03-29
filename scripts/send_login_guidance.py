import asyncio
import os
import sys
import argparse

# Add project root to sys.path
sys.path.append(os.getcwd())

from database.postgres import AsyncSessionLocal
from database.models import User
from database.redis_client import redis_client
from services.kakao_client import KakaoClient
from config.settings import settings
from sqlalchemy import select
from utils.logger import get_logger

logger = get_logger(__name__)

async def send_guidance():
    async with AsyncSessionLocal() as db:
        # 1. Get all users who have channel key but NO OAuth token
        result = await db.execute(
            select(User).where(
                User.kakao_channel_user_key != None,
                User.kakao_access_token == None
            )
        )
        users = result.scalars().all()
        
        print(f"Target unauthenticated users found: {len(users)}")
        
        kakao = KakaoClient(mock_mode=False) # Set to False for real sending if configured
        
        success_count = 0
        fail_count = 0
        
        for user in users:
            try:
                channel_key = user.kakao_channel_user_key
                # Construct guidance message
                message = (
                    "🔔 [기억의 정원] 서비스 이용 안내\n\n"
                    "안녕하세요! 정원지기입니다 🌱\n"
                    "더 좋은 서비스를 위해 로그인 절차를 다시 한번 진행 바랍니다.\n\n"
                    "로그인을 완료하시면 매일 정해진 안부 인사와 함께 "
                    "정원을 더욱 풍성하게 가꾸실 수 있습니다."
                )
                
                # Button URL with state for linking
                base_url = settings.KAKAO_REDIRECT_URI.replace("/api/v1/auth/kakao/callback", "")
                login_url = f"{base_url}/api/v1/auth/kakao/login?plus_friend_user_key={channel_key}"
                
                print(f"Sending guidance to {user.name} ({user.id})...")
                
                # Using send_channel_message which internally uses bizmessage_ft
                res = await kakao.send_channel_message(
                    channel_user_key=channel_key,
                    message=message,
                    link_url=login_url,
                    button_title="로그인하고 대화 이어가기 🔐"
                )
                
                if res.get("success"):
                    print(f"✅ Sent successfully to {user.name}")
                    success_count += 1
                else:
                    print(f"❌ Failed to send to {user.name}: {res.get('reason', 'Unknown error')}")
                    fail_count += 1
                    
            except Exception as e:
                print(f"❌ Error sending to {user.name}: {e}")
                fail_count += 1

        print(f"\n--- Results ---")
        print(f"Success: {success_count}")
        print(f"Failure: {fail_count}")

if __name__ == "__main__":
    asyncio.run(send_guidance())
