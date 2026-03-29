#!/usr/bin/env python3
"""
친구톡 전송 테스트 스크립트

수집한 plusfriendUserKey로 실제 메시지를 전송합니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from services.kakao_client import KakaoClient
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_friend_talk():
    """친구톡 전송 테스트"""

    # 수집한 실제 user_key (softline 채널)
    user_key = "AkBzAKRCUoEn"

    # 테스트 메시지
    message = """안녕하세요! Memory Garden 🌱입니다.

친구톡 전송 테스트 메시지입니다.

오늘 점심은 무엇을 드셨나요?
가족이나 친구와 함께 드셨다면 어떤 이야기를 나누셨는지도 말씀해주세요.

- Memory Garden 팀 드림"""

    print("\n" + "="*60)
    print("📨 친구톡 전송 테스트")
    print("="*60)
    print(f"👤 user_key: {user_key}")
    print(f"💬 메시지 길이: {len(message)} 자")
    print("="*60)
    print("\n🚀 전송 중...\n")

    try:
        # KakaoClient 초기화 (실제 모드)
        client = KakaoClient(mock_mode=False)

        # 친구톡 전송
        result = await client.send_friend_talk(
            user_key=user_key,
            message=message
        )

        print("="*60)
        print("✅ 전송 성공!")
        print("="*60)
        print(f"결과: {result}")
        print("="*60)

        return result

    except Exception as e:
        print("="*60)
        print("❌ 전송 실패!")
        print("="*60)
        print(f"에러: {e}")
        print("="*60)

        logger.error(f"Friend talk test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # asyncio 실행
    result = asyncio.run(test_friend_talk())

    if result:
        print("\n✅ 테스트 완료! 카카오톡에서 메시지를 확인하세요.")
    else:
        print("\n❌ 테스트 실패! 로그를 확인하세요.")
