#!/usr/bin/env python3
"""
카카오톡 채널 E2E 테스트 스크립트

실제 사용자 시나리오를 시뮬레이션합니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.kakao_client import KakaoClient
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_scenario_1_daily_conversation():
    """시나리오 1: 일상 대화"""
    print("\n" + "="*60)
    print("📱 시나리오 1: 일상 대화 알림")
    print("="*60)

    client = KakaoClient(mock_mode=True)

    # 아침 인사 메시지
    result = await client.send_alimtalk(
        phone="010-1234-5678",
        template_code="MEMORY_GARDEN_DAILY",
        variables={
            "user_name": "홍길동",
            "question": "오늘 아침은 무엇을 드셨나요?",
            "garden_status": "건강하게 자라고 있어요 🌳"
        }
    )

    print(f"✅ 메시지 전송 성공")
    print(f"   - Message ID: {result['message_id']}")
    print(f"   - 수신자: {result['phone']}")
    print(f"   - 시간: {result['timestamp']}")


async def test_scenario_2_risk_alert():
    """시나리오 2: 위험 알림 (보호자)"""
    print("\n" + "="*60)
    print("🚨 시나리오 2: 보호자 위험 알림")
    print("="*60)

    client = KakaoClient(mock_mode=True)

    # ORANGE 레벨 알림
    result = await client.send_alimtalk(
        phone="010-9999-9999",  # 보호자 전화번호
        template_code="MEMORY_GARDEN_ALERT",
        variables={
            "urgency": "주의 필요",
            "user_name": "홍길동",
            "risk_level": "ORANGE",
            "mcdi_score": "58.5",
            "recommendation": "최근 2주간 인지 기능 저하가 관찰되었습니다. 전문의 상담을 권장합니다."
        }
    )

    print(f"✅ 보호자 알림 전송 성공")
    print(f"   - Message ID: {result['message_id']}")
    print(f"   - 수신자: {result['phone']}")
    print(f"   - 위험도: ORANGE")


async def test_scenario_3_weekly_report():
    """시나리오 3: 주간 리포트"""
    print("\n" + "="*60)
    print("📊 시나리오 3: 주간 리포트")
    print("="*60)

    client = KakaoClient(mock_mode=True)

    # 주간 요약
    result = await client.send_alimtalk(
        phone="010-1234-5678",
        template_code="MEMORY_GARDEN_WEEKLY",
        variables={
            "user_name": "홍길동",
            "week_range": "2월 10일 ~ 2월 16일",
            "avg_mcdi": "78.5",
            "conversation_count": "14",
            "garden_growth": "정원이 건강하게 자라고 있어요!",
            "highlight": "이번 주는 특히 일화 기억(ER) 점수가 우수했습니다."
        }
    )

    print(f"✅ 주간 리포트 전송 성공")
    print(f"   - Message ID: {result['message_id']}")
    print(f"   - 기간: 2월 10일 ~ 2월 16일")
    print(f"   - 평균 MCDI: 78.5")


async def test_scenario_4_image_analysis():
    """시나리오 4: 이미지 분석 결과"""
    print("\n" + "="*60)
    print("🖼️  시나리오 4: 이미지 분석 완료 알림")
    print("="*60)

    client = KakaoClient(mock_mode=True)

    # 식사 이미지 분석 완료
    result = await client.send_alimtalk(
        phone="010-1234-5678",
        template_code="MEMORY_GARDEN_IMAGE",
        variables={
            "user_name": "홍길동",
            "analysis_type": "식사",
            "detected_items": "김치찌개, 밥, 계란후라이",
            "feedback": "영양 균형이 좋습니다! 맛있게 드셨나요?"
        }
    )

    print(f"✅ 이미지 분석 결과 전송 성공")
    print(f"   - Message ID: {result['message_id']}")
    print(f"   - 분석 유형: 식사")


async def test_scenario_5_multiple_users():
    """시나리오 5: 다중 사용자 동시 처리"""
    print("\n" + "="*60)
    print("👥 시나리오 5: 다중 사용자 동시 알림")
    print("="*60)

    client = KakaoClient(mock_mode=True)

    users = [
        ("010-1111-1111", "김철수", "GREEN"),
        ("010-2222-2222", "이영희", "YELLOW"),
        ("010-3333-3333", "박민수", "ORANGE"),
        ("010-4444-4444", "정수진", "GREEN"),
        ("010-5555-5555", "최동욱", "YELLOW"),
    ]

    tasks = []
    for phone, name, risk in users:
        task = client.send_alimtalk(
            phone=phone,
            template_code="MEMORY_GARDEN_DAILY",
            variables={
                "user_name": name,
                "question": "오늘 하루는 어떠셨나요?",
                "garden_status": f"상태: {risk}"
            }
        )
        tasks.append(task)

    # 동시 전송
    results = await asyncio.gather(*tasks)

    print(f"✅ {len(results)}명에게 동시 전송 완료")
    for i, (phone, name, risk) in enumerate(users):
        print(f"   - {name} ({phone}): {results[i]['message_id']}")


async def test_real_kakao_api():
    """실제 카카오 API 테스트 (주의!)"""
    print("\n" + "="*60)
    print("⚠️  실제 카카오 API 테스트")
    print("="*60)

    # 환경 변수 확인
    if not hasattr(settings, 'KAKAO_REST_API_KEY') or not settings.KAKAO_REST_API_KEY:
        print("❌ KAKAO_REST_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에서 설정해주세요:")
        print("   KAKAO_REST_API_KEY=your_api_key")
        print("   KAKAO_CHANNEL_ID=your_channel_id")
        return

    print("⚠️  주의: 실제 카카오톡 메시지가 전송됩니다!")
    print("계속하시려면 'yes'를 입력하세요: ", end="")

    # 실제 전송은 주석 처리
    # user_input = input()
    # if user_input.lower() != 'yes':
    #     print("취소되었습니다.")
    #     return

    print("\n(실제 전송은 주석 처리되어 있습니다)")
    print("실제 테스트를 하려면 스크립트를 수정하세요.")


async def main():
    """메인 실행"""
    print("\n" + "🌳 " + "="*58)
    print("  Memory Garden - 카카오톡 채널 E2E 테스트")
    print("="*60 + "\n")

    try:
        # Mock 모드 테스트들
        await test_scenario_1_daily_conversation()
        await asyncio.sleep(0.5)

        await test_scenario_2_risk_alert()
        await asyncio.sleep(0.5)

        await test_scenario_3_weekly_report()
        await asyncio.sleep(0.5)

        await test_scenario_4_image_analysis()
        await asyncio.sleep(0.5)

        await test_scenario_5_multiple_users()
        await asyncio.sleep(0.5)

        # 실제 API 테스트 (선택)
        await test_real_kakao_api()

        print("\n" + "="*60)
        print("✅ 모든 E2E 테스트 완료!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
