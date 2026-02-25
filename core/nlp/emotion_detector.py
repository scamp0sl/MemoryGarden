"""
감정 분석기

OpenAI API를 사용한 텍스트 감정 분석.
사용자 메시지의 감정 상태 파악 및 강도 측정.

Author: Memory Garden Team
Created: 2025-01-15
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, Any, List, Optional
from enum import Enum

# ============================================
# 2. Third-Party Imports
# ============================================
from pydantic import BaseModel, Field

# ============================================
# 3. Local Imports
# ============================================
from services.llm_service import LLMService, default_llm_service
from config.prompts import EMOTION_DETECTION_PROMPT
from utils.logger import get_logger
from utils.exceptions import AnalysisError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)


# ============================================
# 5. 감정 카테고리 정의
# ============================================

class EmotionCategory(str, Enum):
    """감정 카테고리"""
    JOY = "joy"           # 기쁨
    SADNESS = "sadness"   # 슬픔
    ANGER = "anger"       # 분노
    FEAR = "fear"         # 두려움
    SURPRISE = "surprise" # 놀람
    NEUTRAL = "neutral"   # 중립


# ============================================
# 6. 응답 모델
# ============================================

class SecondaryEmotion(BaseModel):
    """부차적 감정"""
    emotion: EmotionCategory = Field(..., description="감정 카테고리")
    intensity: float = Field(..., ge=0.0, le=1.0, description="강도 (0.0~1.0)")


class EmotionResult(BaseModel):
    """
    감정 분석 결과

    Attributes:
        primary_emotion: 주요 감정
        intensity: 주요 감정 강도 (0.0~1.0)
        secondary_emotions: 부차적 감정들
        keywords: 감정 관련 키워드
        rationale: 분석 근거
    """
    primary_emotion: EmotionCategory = Field(..., description="주요 감정")
    intensity: float = Field(..., ge=0.0, le=1.0, description="강도 (0.0~1.0)")
    secondary_emotions: List[SecondaryEmotion] = Field(
        default_factory=list,
        description="부차적 감정들"
    )
    keywords: List[str] = Field(default_factory=list, description="감정 키워드")
    rationale: str = Field(default="", description="분석 근거")


# ============================================
# 7. 감정 분석기 클래스
# ============================================

class EmotionDetector:
    """
    감정 분석기

    OpenAI API를 사용하여 텍스트의 감정을 분석.

    Attributes:
        llm_service: LLM 서비스 인스턴스

    Example:
        >>> detector = EmotionDetector()
        >>> result = await detector.detect("오늘 딸이 전화해서 기분 좋아요!")
        >>> print(result.primary_emotion)
        EmotionCategory.JOY
        >>> print(result.intensity)
        0.85
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        EmotionDetector 초기화

        Args:
            llm_service: LLM 서비스 (None이면 기본 인스턴스 사용)
        """
        self.llm_service = llm_service or default_llm_service

        logger.info("EmotionDetector initialized")

    async def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EmotionResult:
        """
        텍스트에서 감정 감지

        Args:
            text: 분석할 텍스트
            context: 추가 컨텍스트 정보 (선택)

        Returns:
            EmotionResult: 감정 분석 결과

        Raises:
            AnalysisError: 분석 실패 시

        Example:
            >>> detector = EmotionDetector()
            >>> result = await detector.detect("오늘은 슬픈 날이에요")
            >>> print(result.primary_emotion)
            EmotionCategory.SADNESS
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for emotion detection")
                return EmotionResult(
                    primary_emotion=EmotionCategory.NEUTRAL,
                    intensity=0.0,
                    rationale="Empty input"
                )

            logger.debug(f"Detecting emotion for text: {text[:100]}...")

            # 프롬프트 생성
            prompt = EMOTION_DETECTION_PROMPT.format(text=text)

            # LLM 호출 (JSON 모드)
            response = await self.llm_service.call_json(
                prompt=prompt,
                system_prompt="당신은 텍스트 감정 분석 전문가입니다. 한국어 감정 표현에 능숙합니다.",
                temperature=0.3,  # 낮은 온도로 일관성 유지
                max_tokens=500
            )

            # 응답 파싱
            result = self._parse_response(response)

            logger.info(
                f"Emotion detected: {result.primary_emotion.value} (intensity: {result.intensity})",
                extra={
                    "text_length": len(text),
                    "primary_emotion": result.primary_emotion.value,
                    "intensity": result.intensity,
                    "keywords": result.keywords
                }
            )

            return result

        except Exception as e:
            logger.error(f"Emotion detection failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to detect emotion: {e}") from e

    def _parse_response(self, response: Dict[str, Any]) -> EmotionResult:
        """
        LLM 응답 파싱

        Args:
            response: LLM JSON 응답

        Returns:
            EmotionResult: 파싱된 결과

        Raises:
            ValueError: 파싱 실패 시
        """
        try:
            # Primary emotion
            primary_emotion = EmotionCategory(response["primary_emotion"])
            intensity = float(response["intensity"])

            # Secondary emotions
            secondary_emotions = []
            for sec in response.get("secondary_emotions", []):
                secondary_emotions.append(
                    SecondaryEmotion(
                        emotion=EmotionCategory(sec["emotion"]),
                        intensity=float(sec["intensity"])
                    )
                )

            # Keywords
            keywords = response.get("keywords", [])

            # Rationale
            rationale = response.get("rationale", "")

            return EmotionResult(
                primary_emotion=primary_emotion,
                intensity=intensity,
                secondary_emotions=secondary_emotions,
                keywords=keywords,
                rationale=rationale
            )

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse emotion response: {e}", exc_info=True)
            logger.error(f"Raw response: {response}")
            raise ValueError(f"Invalid emotion response format: {e}") from e

    async def detect_batch(
        self,
        texts: List[str]
    ) -> List[EmotionResult]:
        """
        여러 텍스트의 감정을 동시에 분석

        Args:
            texts: 분석할 텍스트 리스트

        Returns:
            List[EmotionResult]: 감정 분석 결과 리스트

        Example:
            >>> detector = EmotionDetector()
            >>> texts = ["기뻐요", "슬퍼요", "화나요"]
            >>> results = await detector.detect_batch(texts)
            >>> print([r.primary_emotion for r in results])
            [EmotionCategory.JOY, EmotionCategory.SADNESS, EmotionCategory.ANGER]
        """
        import asyncio

        tasks = [self.detect(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 에러 처리
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch emotion detection failed for text {i}: {result}")
                # Fallback to neutral
                final_results.append(
                    EmotionResult(
                        primary_emotion=EmotionCategory.NEUTRAL,
                        intensity=0.0,
                        rationale=f"Error: {result}"
                    )
                )
            else:
                final_results.append(result)

        return final_results

    def get_emotion_label_kr(self, emotion: EmotionCategory) -> str:
        """
        감정 카테고리의 한국어 레이블 반환

        Args:
            emotion: 감정 카테고리

        Returns:
            str: 한국어 레이블

        Example:
            >>> detector = EmotionDetector()
            >>> label = detector.get_emotion_label_kr(EmotionCategory.JOY)
            >>> print(label)
            "기쁨"
        """
        labels = {
            EmotionCategory.JOY: "기쁨",
            EmotionCategory.SADNESS: "슬픔",
            EmotionCategory.ANGER: "분노",
            EmotionCategory.FEAR: "두려움",
            EmotionCategory.SURPRISE: "놀람",
            EmotionCategory.NEUTRAL: "중립"
        }
        return labels.get(emotion, "알 수 없음")


# ============================================
# 8. Export
# ============================================
__all__ = [
    "EmotionDetector",
    "EmotionResult",
    "EmotionCategory",
    "SecondaryEmotion",
]


logger.info("Emotion detector module loaded")
