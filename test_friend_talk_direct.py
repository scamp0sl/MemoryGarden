#!/usr/bin/env python3
"""
친구톡 직접 테스트 (API 사용)

저장된 액세스 토큰을 API를 통해 가져와서 친구톡 전송.
"""

import asyncio
import sys
import httpx
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from services.kakao_client import KakaoClient
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_friend_talk():
    """API를 통해 토큰을 가져와서 친구톡 전송"""

    user_id = "test_user"
    user_key = "AkBzAKRCUoEn"  # softline 채널

    print(f"\n{'='*60}")
    print(f"🔑 액세스 토큰 조회 (API)")
    print(f"{'='*60}\n")

    # ============================================
    # 1. API를 통해 액세스 토큰 가져오기
    # ============================================
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/kakao/oauth/token/{user_id}",
            timeout=10.0
        )

        if response.status_code != 200:
            print(f"❌ 토큰 조회 실패: {response.text}")
            return None

        token_data = response.json()
        # API는 앞부분만 표시하므로, 전체 토큰을 다시 가져와야 함

    # ============================================
    # 2. 메모리에서 직접 토큰 가져오기
    # ============================================
    from api.routes.kakao_oauth import get_access_token
    access_token = get_access_token(user_id)

    if not access_token:
        print(f"❌ 액세스 토큰을 찾을 수 없습니다!")
        return None

    print(f"✅ 액세스 토큰 확인: {access_token[:20]}...\n")

    # ============================================
    # 3. 친구톡 전송
    # ============================================
    message = """안녕하세요! Memory Garden 🌱입니다.

OAuth 인증 후 친구톡 전송 테스트입니다.

오늘 점심은 무엇을 드셨나요?
가족이나 친구와 함께 드셨다면 어떤 이야기를 나누셨는지도 말씀해주세요.

- Memory Garden 팀 드림"""

    print(f"{'='*60}")
    print(f"📨 친구톡 전송 테스트")
    print(f"{'='*60}")
    print(f"👤 user_key: {user_key}")
    print(f"💬 메시지 길이: {len(message)} 자")
    print(f"{'='*60}\n")
    print(f"🚀 전송 중...\n")

    try:
        client = KakaoClient(mock_mode=False)

        result = await client.send_friend_talk(
            user_key=user_key,
            message=message,
            access_token=access_token
        )

        print(f"{'='*60}")
        print(f"✅ 전송 성공!")
        print(f"{'='*60}")
        print(f"결과: {result}")
        print(f"{'='*60}\n")

        return result

    except Exception as e:
        print(f"{'='*60}")
        print(f"❌ 전송 실패!")
        print(f"{'='*60}")
        print(f"에러: {e}")
        print(f"{'='*60}\n")

        logger.error(f"Friend talk test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    result = asyncio.run(test_friend_talk())

    if result:
        print(f"\n✅ 테스트 완료! 카카오톡에서 메시지를 확인하세요.")
