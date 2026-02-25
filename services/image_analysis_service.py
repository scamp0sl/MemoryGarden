"""
이미지 분석 서비스

OpenAI GPT-4o Vision API를 사용하여 이미지를 분석합니다.
주요 사용 사례: 음식 사진 분석, 메모리 단서 추출

Author: Memory Garden Team
Created: 2026-02-11
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, Any, Optional, List
from datetime import datetime
import base64
import asyncio

# ============================================
# 2. Third-Party Imports
# ============================================
import httpx
from openai import AsyncOpenAI

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import ExternalServiceError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)


# ============================================
# 5. 상수 정의
# ============================================

# OpenAI Vision 모델
VISION_MODEL = "gpt-4o"  # GPT-4o with vision
MAX_TOKENS = 500  # 분석 응답 최대 토큰
TEMPERATURE = 0.3  # 일관성을 위한 낮은 temperature

# 이미지 분석 타입
IMAGE_ANALYSIS_TYPES = {
    "meal": "음식 사진 분석 (음식 종류, 영양, 식사 시간 추정)",
    "place": "장소 사진 분석 (위치, 환경, 활동)",
    "person": "사람 사진 분석 (얼굴 인식 제외, 상황 이해)",
    "object": "사물 사진 분석 (물건 식별, 용도)",
    "memory": "기억 단서 분석 (전반적인 시각 정보)"
}

# 분석 프롬프트 템플릿
ANALYSIS_PROMPTS = {
    "meal": """
이 이미지는 음식 사진입니다. 다음 정보를 분석해주세요:

1. 음식 종류 (최대 3개)
2. 추정 식사 시간 (아침/점심/저녁/간식)
3. 음식 카테고리 (한식/중식/일식/양식/기타)
4. 특기사항 (색상, 양, 특이 재료 등)

JSON 형식으로 응답하세요:
{
    "foods": ["음식1", "음식2"],
    "meal_time": "점심",
    "category": "한식",
    "notes": "특기사항"
}
""",
    "place": """
이 이미지는 장소 사진입니다. 다음 정보를 분석해주세요:

1. 장소 유형 (집/식당/공원/병원/기타)
2. 실내/실외
3. 추정 활동 (식사/산책/운동/휴식)
4. 환경 특징

JSON 형식으로 응답하세요:
{
    "place_type": "공원",
    "indoor_outdoor": "실외",
    "activity": "산책",
    "features": "환경 특징"
}
""",
    "memory": """
이 이미지에서 기억에 도움이 될 만한 정보를 추출해주세요:

1. 주요 객체 (최대 5개)
2. 색상 (주요 색상 2-3개)
3. 시간대 (추정)
4. 전체적인 분위기

JSON 형식으로 응답하세요:
{
    "main_objects": ["객체1", "객체2"],
    "colors": ["색상1", "색상2"],
    "time_of_day": "오후",
    "mood": "분위기"
}
"""
}


# ============================================
# 6. 클래스 정의
# ============================================

class ImageAnalysisService:
    """
    이미지 분석 서비스

    OpenAI GPT-4o Vision API를 사용하여 이미지를 분석합니다.

    Attributes:
        client: AsyncOpenAI 클라이언트
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.OPENAI_API_KEY)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info("ImageAnalysisService initialized")

    async def analyze_image(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        analysis_type: str = "memory",
        custom_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        이미지 분석

        Args:
            image_url: 이미지 URL (HTTP/HTTPS)
            image_base64: Base64 인코딩된 이미지 데이터
            analysis_type: 분석 타입 (meal/place/person/object/memory)
            custom_prompt: 커스텀 프롬프트 (선택)
            context: 추가 컨텍스트 정보

        Returns:
            {
                "analysis": {분석 결과 JSON},
                "raw_response": "원본 응답",
                "analysis_type": "meal",
                "timestamp": "2026-02-11T16:00:00Z",
                "model": "gpt-4o"
            }

        Raises:
            ExternalServiceError: OpenAI API 호출 실패
            ValueError: 이미지 URL과 Base64 모두 없음

        Example:
            >>> service = ImageAnalysisService()
            >>> result = await service.analyze_image(
            ...     image_url="https://example.com/meal.jpg",
            ...     analysis_type="meal"
            ... )
            >>> print(result["analysis"]["foods"])
            ["밥", "김치찌개", "반찬"]
        """
        try:
            # 이미지 소스 확인
            if not image_url and not image_base64:
                raise ValueError("Either image_url or image_base64 must be provided")

            # 프롬프트 선택
            if custom_prompt:
                prompt = custom_prompt
            elif analysis_type in ANALYSIS_PROMPTS:
                prompt = ANALYSIS_PROMPTS[analysis_type]
            else:
                prompt = ANALYSIS_PROMPTS["memory"]

            # 컨텍스트 추가
            if context:
                prompt += f"\n\n추가 정보: {context}"

            # 이미지 URL 구성
            if image_url:
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": image_url}
                }
            else:
                # Base64 이미지
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                }

            logger.info(
                f"Analyzing image with GPT-4o Vision",
                extra={
                    "analysis_type": analysis_type,
                    "has_url": bool(image_url),
                    "has_base64": bool(image_base64)
                }
            )

            # OpenAI Vision API 호출
            response = await self.client.chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            image_content
                        ]
                    }
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )

            # 응답 추출
            raw_response = response.choices[0].message.content

            # JSON 파싱 시도
            import json
            try:
                # 마크다운 코드 블록 제거
                if "```json" in raw_response:
                    json_str = raw_response.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_response:
                    json_str = raw_response.split("```")[1].split("```")[0].strip()
                else:
                    json_str = raw_response.strip()

                analysis_result = json.loads(json_str)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 원본 응답 사용
                logger.warning(f"Failed to parse JSON response, using raw text")
                analysis_result = {"raw_text": raw_response}

            result = {
                "analysis": analysis_result,
                "raw_response": raw_response,
                "analysis_type": analysis_type,
                "timestamp": datetime.now().isoformat(),
                "model": VISION_MODEL,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

            logger.info(
                f"Image analysis completed",
                extra={
                    "analysis_type": analysis_type,
                    "tokens_used": response.usage.total_tokens
                }
            )

            return result

        except Exception as e:
            logger.error(
                f"Image analysis failed: {e}",
                exc_info=True
            )
            raise ExternalServiceError(f"Image analysis failed: {e}") from e

    async def analyze_meal_image(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        meal_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        음식 이미지 분석 (편의 메서드)

        Args:
            image_url: 이미지 URL
            image_base64: Base64 이미지
            meal_time: 식사 시간 힌트 (선택)

        Returns:
            음식 분석 결과
        """
        context = f"식사 시간: {meal_time}" if meal_time else None

        result = await self.analyze_image(
            image_url=image_url,
            image_base64=image_base64,
            analysis_type="meal",
            context=context
        )

        return result

    async def health_check(self) -> bool:
        """
        OpenAI API 연결 테스트

        Returns:
            True if healthy
        """
        try:
            # 간단한 텍스트 completion으로 테스트
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# ============================================
# 7. 싱글톤 인스턴스
# ============================================

_image_analysis_service: Optional[ImageAnalysisService] = None


def get_image_analysis_service() -> ImageAnalysisService:
    """
    ImageAnalysisService 싱글톤 인스턴스 반환

    Returns:
        ImageAnalysisService 인스턴스
    """
    global _image_analysis_service

    if _image_analysis_service is None:
        _image_analysis_service = ImageAnalysisService()

    return _image_analysis_service
