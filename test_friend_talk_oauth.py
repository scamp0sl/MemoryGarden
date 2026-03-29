#!/usr/bin/env python3
"""
친구톡 OAuth 테스트 스크립트

OAuth 2.0 액세스 토큰을 사용하여 친구톡 전송 테스트.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from services.kakao_client import KakaoClient
from api.routes.kakao_oauth import get_access_token
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_friend_talk_with_oauth():
    """OAuth 액세스 토큰을 사용한 친구톡 전송 테스트"""

    # ============================================
    # 1. 사용자 ID 및 user_key 설정
    # ============================================
    user_id = "test_user"  # Memory Garden 사용자 ID
    user_key = "AkBzAKRCUoEn"  # softline 채널의 plusfriendUserKey

    # ============================================
    # 2. 액세스 토큰 가져오기
    # ============================================
    print(f"\n{'='*60}")
    print(f"🔑 액세스 토큰 조회")
    print(f"{'='*60}")
    print(f"👤 user_id: {user_id}")
    print(f"{'='*60}\n")

    access_token = get_access_token(user_id)

    if not access_token:
        print(f"❌ 액세스 토큰이 없습니다!")
        print(f"\n다음 단계를 먼저 진행하세요:")
        print(f"1. 브라우저에서 접속:")
        print(f"   https://n8n.softline.co.kr/kakao/oauth/login?user_id={user_id}")
        print(f"\n2. 카카오 로그인 및 권한 동의")
        print(f"\n3. 로그인 완료 후 다시 이 스크립트 실행")
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
        # KakaoClient 초기화 (실제 모드)
        client = KakaoClient(mock_mode=False)

        # 친구톡 전송 (OAuth 액세스 토큰 사용)
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
    print(f"\n{'='*60}")
    print(f"🧪 친구톡 OAuth 테스트 시작")
    print(f"{'='*60}\n")

    # asyncio 실행
    result = asyncio.run(test_friend_talk_with_oauth())

    if result:
        print(f"\n✅ 테스트 완료! 카카오톡에서 메시지를 확인하세요.")
    else:
        print(f"\n⚠️  먼저 OAuth 로그인을 진행하세요:")
        print(f"   https://n8n.softline.co.kr/kakao/oauth/login?user_id=test_user")
