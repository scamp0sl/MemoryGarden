"""
ImageAnalysisService 통합 테스트

OpenAI GPT-4o Vision API 연동 검증
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import base64
from datetime import datetime

from services.image_analysis_service import (
    ImageAnalysisService,
    get_image_analysis_service,
    VISION_MODEL,
    ANALYSIS_PROMPTS
)
from utils.exceptions import ExternalServiceError


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_image_base64():
    """테스트용 Base64 이미지 (1x1 투명 PNG)"""
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API 응답"""
    mock_response = MagicMock()

    # choices[0].message.content
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """{
    "foods": ["밥", "김치찌개", "반찬"],
    "meal_time": "점심",
    "category": "한식",
    "notes": "건강한 식단"
}"""

    # usage
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150

    return mock_response


# ============================================
# Test 1: 서비스 초기화
# ============================================

def test_service_initialization():
    """정상 케이스: 서비스 초기화"""
    # Act
    service = ImageAnalysisService()

    # Assert
    assert service.api_key is not None
    assert service.client is not None

    print("✅ ImageAnalysisService initialized successfully")


def test_singleton_pattern():
    """싱글톤 패턴 검증"""
    # Act
    service1 = get_image_analysis_service()
    service2 = get_image_analysis_service()

    # Assert
    assert service1 is service2  # 동일한 인스턴스

    print("✅ Singleton pattern working correctly")


# ============================================
# Test 2: 이미지 분석 (Base64)
# ============================================

@pytest.mark.asyncio
async def test_analyze_image_with_base64(sample_image_base64, mock_openai_response):
    """정상 케이스: Base64 이미지 분석"""
    # Arrange
    service = ImageAnalysisService()

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(return_value=mock_openai_response)):
        # Act
        result = await service.analyze_image(
            image_base64=sample_image_base64,
            analysis_type="meal"
        )

        # Assert
        assert "analysis" in result
        assert "raw_response" in result
        assert "analysis_type" in result
        assert "timestamp" in result
        assert "model" in result
        assert "usage" in result

        # 분석 결과 검증
        analysis = result["analysis"]
        assert "foods" in analysis
        assert analysis["foods"] == ["밥", "김치찌개", "반찬"]
        assert analysis["meal_time"] == "점심"
        assert analysis["category"] == "한식"

        # 메타데이터 검증
        assert result["analysis_type"] == "meal"
        assert result["model"] == VISION_MODEL
        assert result["usage"]["total_tokens"] == 150

        print(f"✅ Image analyzed successfully: {analysis['foods']}")


# ============================================
# Test 3: 이미지 분석 (URL)
# ============================================

@pytest.mark.asyncio
async def test_analyze_image_with_url(mock_openai_response):
    """정상 케이스: URL 이미지 분석"""
    # Arrange
    service = ImageAnalysisService()
    image_url = "https://example.com/meal.jpg"

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(return_value=mock_openai_response)):
        # Act
        result = await service.analyze_image(
            image_url=image_url,
            analysis_type="meal"
        )

        # Assert
        assert result["analysis"]["foods"] == ["밥", "김치찌개", "반찬"]

        print(f"✅ URL image analyzed successfully")


# ============================================
# Test 4: 다양한 분석 타입
# ============================================

@pytest.mark.asyncio
async def test_analyze_different_types(sample_image_base64):
    """다양한 분석 타입 테스트"""
    # Arrange
    service = ImageAnalysisService()
    analysis_types = ["meal", "place", "person", "object", "memory"]

    for analysis_type in analysis_types:
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "test"}'
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        with patch.object(service.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await service.analyze_image(
                image_base64=sample_image_base64,
                analysis_type=analysis_type
            )

            # Assert
            assert result["analysis_type"] == analysis_type
            assert "analysis" in result

            print(f"✅ Analysis type '{analysis_type}' working")


# ============================================
# Test 5: 커스텀 프롬프트
# ============================================

@pytest.mark.asyncio
async def test_analyze_with_custom_prompt(sample_image_base64, mock_openai_response):
    """커스텀 프롬프트 사용"""
    # Arrange
    service = ImageAnalysisService()
    custom_prompt = "이 이미지에서 음식의 양을 평가해주세요."

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(return_value=mock_openai_response)) as mock_create:
        # Act
        result = await service.analyze_image(
            image_base64=sample_image_base64,
            custom_prompt=custom_prompt
        )

        # Assert
        assert "analysis" in result

        # 커스텀 프롬프트가 사용되었는지 확인
        call_args = mock_create.call_args
        messages = call_args.kwargs["messages"]
        assert custom_prompt in messages[0]["content"][0]["text"]

        print("✅ Custom prompt working correctly")


# ============================================
# Test 6: 컨텍스트 추가
# ============================================

@pytest.mark.asyncio
async def test_analyze_with_context(sample_image_base64, mock_openai_response):
    """추가 컨텍스트 정보 제공"""
    # Arrange
    service = ImageAnalysisService()
    context = "사용자가 당뇨병 환자입니다"

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(return_value=mock_openai_response)) as mock_create:
        # Act
        result = await service.analyze_image(
            image_base64=sample_image_base64,
            analysis_type="meal",
            context=context
        )

        # Assert
        call_args = mock_create.call_args
        messages = call_args.kwargs["messages"]
        prompt_text = messages[0]["content"][0]["text"]

        assert context in prompt_text

        print("✅ Context added to prompt successfully")


# ============================================
# Test 7: 에러 처리
# ============================================

@pytest.mark.asyncio
async def test_analyze_without_image():
    """에러 케이스: 이미지 없음"""
    # Arrange
    service = ImageAnalysisService()

    # Act & Assert
    # ValueError가 ExternalServiceError로 감싸져서 발생
    with pytest.raises(ExternalServiceError, match="Either image_url or image_base64 must be provided"):
        await service.analyze_image()

    print("✅ Error handling: no image")


@pytest.mark.asyncio
async def test_analyze_openai_failure(sample_image_base64):
    """에러 케이스: OpenAI API 실패"""
    # Arrange
    service = ImageAnalysisService()

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(side_effect=Exception("API Error"))):
        # Act & Assert
        with pytest.raises(ExternalServiceError, match="Image analysis failed"):
            await service.analyze_image(image_base64=sample_image_base64)

    print("✅ Error handling: OpenAI API failure")


# ============================================
# Test 8: JSON 파싱
# ============================================

@pytest.mark.asyncio
async def test_analyze_json_parsing_with_markdown(sample_image_base64):
    """JSON 파싱: 마크다운 코드 블록 처리"""
    # Arrange
    service = ImageAnalysisService()

    # Mock 응답 (마크다운 코드 블록 포함)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """```json
{
    "foods": ["김치", "밥"],
    "meal_time": "저녁"
}
```"""
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)):
        # Act
        result = await service.analyze_image(image_base64=sample_image_base64)

        # Assert
        analysis = result["analysis"]
        assert analysis["foods"] == ["김치", "밥"]
        assert analysis["meal_time"] == "저녁"

        print("✅ JSON parsing with markdown code block successful")


@pytest.mark.asyncio
async def test_analyze_json_parsing_failure(sample_image_base64):
    """JSON 파싱 실패 시 raw_text 사용"""
    # Arrange
    service = ImageAnalysisService()

    # Mock 응답 (잘못된 JSON)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is not JSON format"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)):
        # Act
        result = await service.analyze_image(image_base64=sample_image_base64)

        # Assert
        analysis = result["analysis"]
        assert "raw_text" in analysis
        assert analysis["raw_text"] == "This is not JSON format"

        print("✅ JSON parsing failure handled gracefully")


# ============================================
# Test 9: analyze_meal_image() 편의 메서드
# ============================================

@pytest.mark.asyncio
async def test_analyze_meal_image_convenience_method(sample_image_base64, mock_openai_response):
    """편의 메서드: analyze_meal_image()"""
    # Arrange
    service = ImageAnalysisService()

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(return_value=mock_openai_response)):
        # Act
        result = await service.analyze_meal_image(
            image_base64=sample_image_base64,
            meal_time="점심"
        )

        # Assert
        assert result["analysis_type"] == "meal"
        assert result["analysis"]["meal_time"] == "점심"

        print("✅ analyze_meal_image() convenience method working")


# ============================================
# Test 10: health_check()
# ============================================

@pytest.mark.asyncio
async def test_health_check_success():
    """헬스 체크: 성공"""
    # Arrange
    service = ImageAnalysisService()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello"

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)):
        # Act
        result = await service.health_check()

        # Assert
        assert result is True

        print("✅ Health check passed")


@pytest.mark.asyncio
async def test_health_check_failure():
    """헬스 체크: 실패"""
    # Arrange
    service = ImageAnalysisService()

    with patch.object(service.client.chat.completions, 'create', new=AsyncMock(side_effect=Exception("API Down"))):
        # Act
        result = await service.health_check()

        # Assert
        assert result is False

        print("✅ Health check failure detected")


# ============================================
# Test Summary
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ImageAnalysisService 통합 테스트 시작")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])
