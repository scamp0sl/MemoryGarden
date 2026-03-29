"""
카카오톡 채널 통합 테스트

실제 카카오톡 채널과의 통합을 테스트합니다.
KAKAO_REST_API_KEY가 설정된 경우에만 실행됩니다.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

from services.kakao_client import KakaoClient
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# 카카오 설정이 없으면 테스트 Skip
pytestmark = pytest.mark.skipif(
    not hasattr(settings, 'KAKAO_REST_API_KEY') or not settings.KAKAO_REST_API_KEY,
    reason="KAKAO_REST_API_KEY not configured"
)


# ============================================
# 1. Mock 모드 테스트 (항상 실행 가능)
# ============================================

@pytest.mark.asyncio
async def test_kakao_mock_mode():
    """Mock 모드: 알림톡 전송 테스트"""
    # Arrange
    client = KakaoClient(mock_mode=True)

    # Act
    result = await client.send_alimtalk(
        phone="010-1234-5678",
        template_code="MEMORY_GARDEN_ALERT",
        variables={
            "urgency": "즉시 확인 필요",
            "user_name": "테스트사용자",
            "risk_level": "ORANGE",
            "mcdi_score": "65.5",
            "recommendation": "전문의 상담을 권장합니다."
        }
    )

    # Assert
    assert result["success"] is True
    assert "message_id" in result
    assert result["phone"] == "010-1234-5678"
    assert result["template_code"] == "MEMORY_GARDEN_ALERT"

    logger.info(f"✅ Mock alimtalk sent: {result['message_id']}")


@pytest.mark.asyncio
async def test_kakao_mock_multiple_messages():
    """Mock 모드: 여러 메시지 연속 전송"""
    # Arrange
    client = KakaoClient(mock_mode=True)
    phones = [
        "010-1111-1111",
        "010-2222-2222",
        "010-3333-3333"
    ]

    # Act
    results = []
    for phone in phones:
        result = await client.send_alimtalk(
            phone=phone,
            template_code="MEMORY_GARDEN_DAILY",
            variables={
                "user_name": "홍길동",
                "question": "오늘 점심은 무엇을 드셨나요?",
                "garden_status": "건강함 🌳"
            }
        )
        results.append(result)

    # Assert
    assert len(results) == 3
    assert all(r["success"] for r in results)

    logger.info(f"✅ Sent {len(results)} mock messages")


# ============================================
# 2. 실제 API 테스트 (선택적)
# ============================================

@pytest.mark.real_kakao
@pytest.mark.asyncio
async def test_kakao_real_mode():
    """실제 모드: 알림톡 전송 테스트

    주의: 실제 카카오톡 메시지가 전송됩니다!
    테스트용 전화번호를 사용하세요.
    """
    # Arrange
    client = KakaoClient(
        api_key=settings.KAKAO_REST_API_KEY,
        sender_key=settings.KAKAO_CHANNEL_ID,
        mock_mode=False
    )

    # TODO: 실제 테스트 전화번호로 변경
    test_phone = "010-0000-0000"  # ⚠️ 반드시 변경!

    # Act
    result = await client.send_alimtalk(
        phone=test_phone,
        template_code="MEMORY_GARDEN_ALERT",
        variables={
            "urgency": "테스트",
            "user_name": "테스트",
            "risk_level": "GREEN",
            "mcdi_score": "85.0",
            "recommendation": "통합 테스트 메시지입니다."
        }
    )

    # Assert
    assert result["success"] is True
    assert "message_id" in result

    logger.info(f"✅ Real alimtalk sent: {result['message_id']}")


# ============================================
# 3. 전체 워크플로우 통합 테스트
# ============================================

@pytest.mark.asyncio
async def test_full_conversation_workflow_with_kakao():
    """전체 워크플로우: 대화 → 분석 → 알림"""
    from core.workflow.message_processor import MessageProcessor
    from unittest.mock import AsyncMock, Mock

    # Mock dependencies
    mock_memory = AsyncMock()
    mock_analyzer = AsyncMock()
    mock_risk_evaluator = AsyncMock()
    mock_dialogue = AsyncMock()
    mock_notification = AsyncMock()

    # Mock 응답 설정
    mock_memory.retrieve_all.return_value = {
        "session": {"context": "test"},
        "episodic": [],
        "biographical": {},
        "analytical": []
    }

    mock_analyzer.analyze.return_value = {
        "mcdi_score": 45.0,  # 낮은 점수 (RED 레벨)
        "scores": {
            "LR": 40.0,
            "SD": 42.0,
            "NC": 48.0,
            "TO": 50.0,
            "ER": 38.0,
            "RT": 55.0
        }
    }

    mock_risk_evaluator.evaluate.return_value = {
        "risk_level": "RED",
        "alert_needed": True,
        "check_confounds": False
    }

    mock_dialogue.plan_next.return_value = {
        "category": "episodic_recall",
        "difficulty": "easy"
    }

    mock_dialogue.generate_response.return_value = "관심을 가져주셔서 감사합니다."

    # MessageProcessor 생성
    processor = MessageProcessor(
        memory_manager=mock_memory,
        analyzer=mock_analyzer,
        risk_evaluator=mock_risk_evaluator,
        dialogue_manager=mock_dialogue,
        notification_service=mock_notification
    )

    # Act
    response = await processor.process(
        user_id="test_user_123",
        message="기억이 잘 안나요"
    )

    # Assert
    assert response is not None
    mock_notification.send_guardian_alert.assert_called_once()

    logger.info("✅ Full workflow with Kakao notification executed")


# ============================================
# 4. 템플릿 검증 테스트
# ============================================

@pytest.mark.asyncio
async def test_kakao_template_variables():
    """템플릿 변수 검증"""
    client = KakaoClient(mock_mode=True)

    # 필수 변수 누락 시 에러
    with pytest.raises(ValueError):
        await client.send_alimtalk(
            phone="010-1234-5678",
            template_code="MEMORY_GARDEN_ALERT",
            variables={}  # 빈 변수
        )


@pytest.mark.asyncio
async def test_kakao_invalid_phone():
    """잘못된 전화번호 형식"""
    client = KakaoClient(mock_mode=True)

    # 잘못된 형식
    with pytest.raises(ValueError):
        await client.send_alimtalk(
            phone="invalid-phone",
            template_code="MEMORY_GARDEN_ALERT",
            variables={
                "urgency": "test",
                "user_name": "test",
                "risk_level": "GREEN",
                "mcdi_score": "85.0",
                "recommendation": "test"
            }
        )


# ============================================
# 5. 성능 테스트
# ============================================

@pytest.mark.asyncio
async def test_kakao_concurrent_messages():
    """동시 다발 메시지 전송 성능"""
    client = KakaoClient(mock_mode=True)

    # 100개 메시지 동시 전송
    tasks = []
    for i in range(100):
        task = client.send_alimtalk(
            phone=f"010-{i:04d}-{i:04d}",
            template_code="MEMORY_GARDEN_DAILY",
            variables={
                "user_name": f"User{i}",
                "question": "테스트 질문",
                "garden_status": "건강함"
            }
        )
        tasks.append(task)

    # Act
    start_time = asyncio.get_event_loop().time()
    results = await asyncio.gather(*tasks)
    elapsed = asyncio.get_event_loop().time() - start_time

    # Assert
    assert len(results) == 100
    assert all(r["success"] for r in results)
    assert elapsed < 5.0  # 5초 이내 완료

    logger.info(f"✅ 100 messages sent in {elapsed:.2f}s")


# ============================================
# 테스트 실행 방법
# ============================================

if __name__ == "__main__":
    """
    # Mock 모드 테스트 (항상 가능)
    pytest tests/integration/test_kakao_integration.py -v

    # 실제 카카오 API 테스트 (주의!)
    pytest tests/integration/test_kakao_integration.py -v -m real_kakao

    # 특정 테스트만
    pytest tests/integration/test_kakao_integration.py::test_kakao_mock_mode -v

    # 성능 테스트 포함
    pytest tests/integration/test_kakao_integration.py -v --durations=10
    """
    pass
