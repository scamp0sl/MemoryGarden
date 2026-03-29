"""
NotificationService 테스트

보호자 알림 전송 및 로그 기록 검증
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.notification_service import NotificationService, Guardian
from services.kakao_client import KakaoClient


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_kakao_client():
    """Mock KakaoClient"""
    client = KakaoClient(mock_mode=True)
    return client


@pytest.fixture
def notification_service(mock_kakao_client):
    """NotificationService (Mock 모드)"""
    return NotificationService(
        kakao_client=mock_kakao_client,
        mock_mode=True
    )


@pytest.fixture
def sample_analysis():
    """테스트용 분석 결과"""
    return {
        "scores": {
            "LR": 78.5,
            "SD": 82.3,
            "NC": 75.0,
            "TO": 80.0,
            "ER": 72.5,
            "RT": 70.0
        },
        "mcdi_score": 76.5,
        "failed_metrics": []
    }


@pytest.fixture
def sample_guardian():
    """테스트용 보호자 정보"""
    return Guardian(
        id="test_guardian_id",
        name="홍길동",
        phone="010-1234-5678",
        relationship="아들",
        email="hong@example.com"
    )


# ============================================
# Test 1: send_guardian_alert() - 성공 케이스
# ============================================

@pytest.mark.asyncio
async def test_send_guardian_alert_success(
    notification_service,
    sample_analysis,
    sample_guardian
):
    """정상 케이스: 보호자 알림 전송 성공"""
    # Arrange
    user_id = "test_user"
    risk_level = "ORANGE"
    mcdi_score = 55.0

    # Mock _get_guardian_contact
    with patch.object(
        notification_service,
        '_get_guardian_contact',
        return_value=sample_guardian
    ):
        # Mock _log_notification
        with patch.object(
            notification_service,
            '_log_notification',
            return_value=None
        ) as mock_log:
            # Act
            result = await notification_service.send_guardian_alert(
                user_id=user_id,
                risk_level=risk_level,
                mcdi_score=mcdi_score,
                analysis=sample_analysis
            )

            # Assert
            assert result["alert_sent"] is True
            assert result["channel"] == "kakao"
            assert "message_id" in result
            assert result["guardian"]["name"] == "홍길동"
            assert result["guardian"]["phone"] == "010-1234-5678"
            assert result["mode"] == "mock"

            # 로그 기록 확인
            mock_log.assert_called_once()

    print(f"✅ Guardian alert sent: {result['message_id']}")


@pytest.mark.asyncio
async def test_send_guardian_alert_red_level(
    notification_service,
    sample_analysis,
    sample_guardian
):
    """RED 위험도 케이스"""
    # Arrange
    user_id = "test_user"
    risk_level = "RED"
    mcdi_score = 35.0

    # Mock
    with patch.object(
        notification_service,
        '_get_guardian_contact',
        return_value=sample_guardian
    ):
        with patch.object(
            notification_service,
            '_log_notification',
            return_value=None
        ):
            # Act
            result = await notification_service.send_guardian_alert(
                user_id=user_id,
                risk_level=risk_level,
                mcdi_score=mcdi_score,
                analysis=sample_analysis
            )

            # Assert
            assert result["alert_sent"] is True

    print(f"✅ RED level alert sent")


# ============================================
# Test 2: send_guardian_alert() - 보호자 없음
# ============================================

@pytest.mark.asyncio
async def test_send_guardian_alert_no_guardian(
    notification_service,
    sample_analysis
):
    """엣지 케이스: 보호자 없음"""
    # Arrange
    user_id = "user_without_guardian"
    risk_level = "ORANGE"
    mcdi_score = 55.0

    # Mock _get_guardian_contact to return None
    with patch.object(
        notification_service,
        '_get_guardian_contact',
        return_value=None
    ):
        # Act
        result = await notification_service.send_guardian_alert(
            user_id=user_id,
            risk_level=risk_level,
            mcdi_score=mcdi_score,
            analysis=sample_analysis
        )

        # Assert
        assert result["alert_sent"] is False
        assert result["reason"] == "no_guardian"

    print("✅ No guardian case handled")


# ============================================
# Test 3: send_guardian_alert() - 전송 실패
# ============================================

@pytest.mark.asyncio
async def test_send_guardian_alert_kakao_failure(
    notification_service,
    sample_analysis,
    sample_guardian
):
    """에러 케이스: 카카오 전송 실패"""
    # Arrange
    user_id = "test_user"
    risk_level = "ORANGE"
    mcdi_score = 55.0

    # Mock _get_guardian_contact
    with patch.object(
        notification_service,
        '_get_guardian_contact',
        return_value=sample_guardian
    ):
        # Mock kakao_client.send_alimtalk to raise exception
        with patch.object(
            notification_service.kakao_client,
            'send_alimtalk',
            side_effect=Exception("Kakao API Error")
        ):
            # Mock _log_notification
            with patch.object(
                notification_service,
                '_log_notification',
                return_value=None
            ) as mock_log:
                # Act
                result = await notification_service.send_guardian_alert(
                    user_id=user_id,
                    risk_level=risk_level,
                    mcdi_score=mcdi_score,
                    analysis=sample_analysis
                )

                # Assert
                assert result["alert_sent"] is False
                assert "error" in result

                # 실패 로그 기록 확인
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args.kwargs["success"] is False

    print("✅ Kakao failure handled")


# ============================================
# Test 4: _get_recommendation()
# ============================================

def test_get_recommendation(notification_service):
    """권장 사항 생성"""
    # Act
    rec_red = notification_service._get_recommendation("RED")
    rec_orange = notification_service._get_recommendation("ORANGE")
    rec_yellow = notification_service._get_recommendation("YELLOW")
    rec_green = notification_service._get_recommendation("GREEN")

    # Assert
    assert "빨리" in rec_red
    assert "2주" in rec_orange
    assert "1개월" in rec_yellow
    assert "정상" in rec_green

    print("✅ Recommendations generated")


# ============================================
# Test 5: _get_urgency()
# ============================================

def test_get_urgency(notification_service):
    """긴급도 메시지 생성"""
    # Act
    urgency_red = notification_service._get_urgency("RED")
    urgency_orange = notification_service._get_urgency("ORANGE")

    # Assert
    assert "즉시" in urgency_red
    assert "주의" in urgency_orange

    print("✅ Urgency messages generated")


# ============================================
# Test 6: _prepare_message_variables()
# ============================================

def test_prepare_message_variables(notification_service, sample_guardian):
    """템플릿 변수 준비"""
    # Arrange
    risk_level = "RED"
    mcdi_score = 45.0
    analysis = {"scores": {}}

    # Act
    variables = notification_service._prepare_message_variables(
        guardian=sample_guardian,
        risk_level=risk_level,
        mcdi_score=mcdi_score,
        analysis=analysis
    )

    # Assert
    assert "urgency" in variables
    assert "user_name" in variables
    assert "risk_level" in variables
    assert "mcdi_score" in variables
    assert "recommendation" in variables

    assert variables["user_name"] == "홍길동"
    assert variables["risk_level"] == "RED"
    assert variables["mcdi_score"] == "45.0"

    print("✅ Message variables prepared")


# ============================================
# Test 7: get_alert_preview()
# ============================================

def test_get_alert_preview(notification_service):
    """알림 미리보기 생성"""
    # Act
    preview = notification_service.get_alert_preview(
        risk_level="RED",
        mcdi_score=45.0,
        guardian_name="홍길동"
    )

    # Assert
    assert "[Memory Garden 알림]" in preview
    assert "RED" in preview
    assert "45.0" in preview
    assert "홍길동" in preview

    print("✅ Alert preview generated:")
    print(preview)


# ============================================
# Test 8: 여러 위험도 레벨 테스트
# ============================================

@pytest.mark.asyncio
async def test_send_alert_various_risk_levels(
    notification_service,
    sample_analysis,
    sample_guardian
):
    """다양한 위험도 레벨"""
    # Arrange
    risk_levels = ["RED", "ORANGE", "YELLOW"]

    # Mock
    with patch.object(
        notification_service,
        '_get_guardian_contact',
        return_value=sample_guardian
    ):
        with patch.object(
            notification_service,
            '_log_notification',
            return_value=None
        ):
            # Act & Assert
            for risk_level in risk_levels:
                result = await notification_service.send_guardian_alert(
                    user_id="test_user",
                    risk_level=risk_level,
                    mcdi_score=50.0,
                    analysis=sample_analysis
                )

                assert result["alert_sent"] is True

    print(f"✅ Tested {len(risk_levels)} risk levels")


# ============================================
# Test Summary
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("NotificationService 테스트 시작")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])
