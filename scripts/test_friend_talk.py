#!/usr/bin/env python3
"""
친구톡 (Friend Talk) 테스트 스크립트

템플릿 승인 없이 즉시 사용 가능한 친구톡 API 테스트.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.kakao_client import KakaoClient
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_friend_talk_mock():
    """Mock 모드: 친구톡 테스트"""
    print("\n" + "=" * 60)
    print("Test 1: 친구톡 전송 (Mock 모드)")
    print("=" * 60)

    client = KakaoClient(mock_mode=True)

    # 테스트 메시지
    message = """안녕하세요! Memory Garden 🌱

오늘의 정원 가꾸기 시간입니다.

어제 저녁은 무엇을 드셨나요?
가족이나 친구와 함께 드셨다면 어떤 이야기를 나누셨는지도 말씀해 주세요."""

    result = await client.send_friend_talk(
        user_key="test_user_abc123",
        message=message
    )

    print(f"\n✅ Success: {result['success']}")
    print(f"📨 Message ID: {result['message_id']}")
    print(f"📊 Message Length: {result['message_length']} characters")
    print(f"⏰ Timestamp: {result['timestamp']}")
    print(f"\n📝 Message Preview:")
    print("-" * 60)
    print(message)
    print("-" * 60)


async def test_friend_talk_real():
    """실제 API 모드: 친구톡 테스트"""
    print("\n" + "=" * 60)
    print("Test 2: 친구톡 전송 (Real API 모드)")
    print("=" * 60)

    # .env에서 API 키 읽기 필요
    print("\n⚠️  실제 API 테스트를 위해서는:")
    print("1. .env에 KAKAO_API_KEY 설정")
    print("2. 카카오 채널 친구 추가 완료")
    print("3. user_key 값 확인 (채팅방 ID)")
    print("\n현재는 Mock 모드로 대체합니다.")

    # 실제 사용 예시 (주석 처리)
    """
    client = KakaoClient(mock_mode=False)

    result = await client.send_friend_talk(
        user_key="실제_사용자_KEY",  # 카카오 채널 친구 ID
        message="안녕하세요! Memory Garden입니다."
    )

    print(f"Success: {result['success']}")
    print(f"Message ID: {result['message_id']}")
    """


async def test_friend_talk_scenarios():
    """다양한 시나리오 테스트"""
    print("\n" + "=" * 60)
    print("Test 3: 친구톡 다양한 시나리오")
    print("=" * 60)

    client = KakaoClient(mock_mode=True)

    scenarios = [
        {
            "name": "일일 대화 프롬프트",
            "message": """좋은 아침입니다! 🌅

오늘은 어떤 하루를 보내셨나요?
아침에 기억에 남는 일이 있으셨다면 들려주세요."""
        },
        {
            "name": "주간 회상 질문",
            "message": """이번 주를 되돌아봅니다 🌸

이번 주에 가장 기억에 남는 순간은 언제였나요?
그때 어떤 감정을 느끼셨는지도 함께 말씀해 주세요."""
        },
        {
            "name": "감정 체크",
            "message": """오늘의 기분은 어떠신가요? 😊

1. 매우 좋음
2. 좋음
3. 보통
4. 조금 우울함
5. 많이 우울함

숫자로 답해주세요."""
        },
        {
            "name": "기억 회상 (이미지 포함)",
            "message": """📷 사진과 함께 추억을 나눠주세요

최근에 찍은 사진 중 가장 마음에 드는 사진이 있나요?
그 사진을 찍었을 때의 상황도 함께 말씀해 주세요."""
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n▶ 시나리오 {i}: {scenario['name']}")
        print("-" * 60)

        result = await client.send_friend_talk(
            user_key=f"test_user_{i}",
            message=scenario['message']
        )

        print(f"✅ Success: {result['success']}")
        print(f"📨 Message ID: {result['message_id']}")
        print(f"📊 Length: {result['message_length']} chars")
        print("\n📝 Message:")
        print(scenario['message'])


async def compare_alimtalk_vs_friend_talk():
    """알림톡 vs 친구톡 비교"""
    print("\n" + "=" * 60)
    print("비교: 알림톡 vs 친구톡")
    print("=" * 60)

    comparison = """
┌─────────────────┬──────────────────┬──────────────────┐
│     항목        │   알림톡         │   친구톡         │
├─────────────────┼──────────────────┼──────────────────┤
│ 템플릿 승인     │ 필수 (3-5일)     │ 불필요 ✅        │
│ 친구 추가       │ 불필요           │ 필수             │
│ 메시지 형식     │ 고정 (템플릿)    │ 자유 형식 ✅     │
│ 발송 대상       │ 전화번호 있으면  │ 채널 친구만      │
│ 광고성 메시지   │ 불가             │ 불가             │
│ 즉시 사용       │ X                │ O ✅             │
│ MVP/테스트      │ 어려움           │ 적합 ✅          │
│ 정식 서비스     │ 적합 ✅          │ 제한적           │
└─────────────────┴──────────────────┴──────────────────┘

📌 권장 사용 전략:
1. Phase 1 (현재): 친구톡으로 개발/테스트
2. Phase 2 (베타): 친구톡 + 알림톡 병행
3. Phase 3 (정식): 알림톡 중심 + 친구톡 보조

💡 Memory Garden의 경우:
- 일일 대화 프롬프트: 친구톡으로 충분 ✅
- 위험 알림 (ORANGE/RED): 알림톡 필요 (보호자)
- 주간 리포트: 친구톡으로 가능 ✅
"""
    print(comparison)


async def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("🌱 Memory Garden - 친구톡 테스트")
    print("=" * 60)

    try:
        # Test 1: Mock 모드 테스트
        await test_friend_talk_mock()

        # Test 2: Real API 안내
        await test_friend_talk_real()

        # Test 3: 다양한 시나리오
        await test_friend_talk_scenarios()

        # Test 4: 비교표
        await compare_alimtalk_vs_friend_talk()

        print("\n" + "=" * 60)
        print("✅ 모든 친구톡 테스트 완료!")
        print("=" * 60)
        print("\n📚 다음 단계:")
        print("1. 카카오 채널에서 '친구 추가' 완료")
        print("2. .env에 KAKAO_API_KEY 설정")
        print("3. mock_mode=False로 실제 전송 테스트")
        print("4. 일일 대화 플로우에 친구톡 통합")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
