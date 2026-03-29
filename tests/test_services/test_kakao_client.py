"""
KakaoClient 테스트

알림톡 전송 및 Mock 모드 검증
"""

import pytest

from services.kakao_client import KakaoClient, get_kakao_client


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_client():
    """Mock 모드 KakaoClient"""
    return KakaoClient(mock_mode=True)


@pytest.fixture
def sample_variables():
    """테스트용 템플릿 변수"""
    return {
        "urgency": "⚠️ 즉시 확인 필요",
        "user_name": "홍길동",
        "risk_level": "RED",
        "mcdi_score": "45.0",
        "recommendation": "가능한 빨리 전문의 상담을 받으세요."
    }


# ============================================
# Test 1: send_alimtalk() - Mock 모드
# ============================================

@pytest.mark.asyncio
async def test_send_alimtalk_mock_success(mock_client, sample_variables):
    """정상 케이스: Mock 모드 알림톡 전송"""
    # Arrange
    phone = "010-1234-5678"
    template_code = "MEMORY_GARDEN_ALERT"

    # Act
    result = await mock_client.send_alimtalk(
        phone=phone,
        template_code=template_code,
        variables=sample_variables
    )

    # Assert
    assert result["success"] is True
    assert result["phone"] == phone
    assert result["template_code"] == template_code
    assert "message_id" in result
    assert result["message_id"].startswith("mock_")
    assert result["mode"] == "mock"

    print(f"✅ Mock alimtalk sent: {result['message_id']}")


@pytest.mark.asyncio
async def test_send_alimtalk_mock_different_phones(mock_client, sample_variables):
    """여러 전화번호로 전송"""
    # Arrange
    phones = ["010-1111-2222", "010-3333-4444", "010-5555-6666"]

    # Act & Assert
    for phone in phones:
        result = await mock_client.send_alimtalk(
            phone=phone,
            template_code="MEMORY_GARDEN_ALERT",
            variables=sample_variables
        )

        assert result["success"] is True
        assert result["phone"] == phone

    print(f"✅ Sent to {len(phones)} phones")


# ============================================
# Test 2: validate_template() - Mock 모드
# ============================================

@pytest.mark.asyncio
async def test_validate_template_mock(mock_client):
    """템플릿 검증 - Mock 모드"""
    # Act
    is_valid = await mock_client.validate_template("MEMORY_GARDEN_ALERT")

    # Assert
    assert is_valid is True

    print("✅ Template validated (mock)")


# ============================================
# Test 3: get_template_preview()
# ============================================

def test_get_template_preview(mock_client, sample_variables):
    """템플릿 미리보기 생성"""
    # Act
    preview = mock_client.get_template_preview(
        "MEMORY_GARDEN_ALERT",
        sample_variables
    )

    # Assert
    assert "[Memory Garden 알림]" in preview
    assert "⚠️ 즉시 확인 필요" in preview
    assert "홍길동" in preview
    assert "RED" in preview
    assert "45.0점" in preview

    print("✅ Template preview generated:")
    print(preview)


# ============================================
# Test 4: health_check() - Mock 모드
# ============================================

@pytest.mark.asyncio
async def test_health_check_mock(mock_client):
    """서버 상태 확인 - Mock 모드"""
    # Act
    is_healthy = await mock_client.health_check()

    # Assert
    assert is_healthy is True

    print("✅ Health check passed (mock)")


# ============================================
# Test 5: get_kakao_client() 싱글톤
# ============================================

def test_get_kakao_client_singleton():
    """싱글톤 패턴 검증"""
    # Act
    client1 = get_kakao_client(mock_mode=True)
    client2 = get_kakao_client(mock_mode=True)

    # Assert
    assert client1 is client2  # 같은 인스턴스

    print("✅ Singleton pattern verified")


# ============================================
# Test 6: 초기화 모드 검증
# ============================================

def test_kakao_client_mock_mode_flag():
    """Mock 모드 플래그 검증"""
    # Act
    mock_client = KakaoClient(mock_mode=True)
    # real_client = KakaoClient(mock_mode=False)  # 실제 API 키 없으면 주석 처리

    # Assert
    assert mock_client.mock_mode is True
    # assert real_client.mock_mode is False

    print("✅ Mock mode flag verified")


# ============================================
# Test 7: 여러 템플릿 변수 조합
# ============================================

@pytest.mark.asyncio
async def test_send_alimtalk_various_risk_levels(mock_client):
    """다양한 위험도 레벨 테스트"""
    # Arrange
    risk_levels = ["RED", "ORANGE", "YELLOW", "GREEN"]

    # Act & Assert
    for risk_level in risk_levels:
        variables = {
            "urgency": "테스트",
            "user_name": "테스트 사용자",
            "risk_level": risk_level,
            "mcdi_score": "70.0",
            "recommendation": "테스트 권장사항"
        }

        result = await mock_client.send_alimtalk(
            phone="010-0000-0000",
            template_code="MEMORY_GARDEN_ALERT",
            variables=variables
        )

        assert result["success"] is True

    print(f"✅ Tested {len(risk_levels)} risk levels")


# ============================================
# Test Summary
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("KakaoClient 테스트 시작")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])
