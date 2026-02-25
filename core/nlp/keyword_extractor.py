"""
키워드 추출기

OpenAI API를 사용한 핵심 키워드 및 주제 추출.
대화에서 중요한 개념과 엔티티 파악.

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
from config.prompts import KEYWORD_EXTRACTION_PROMPT
from utils.logger import get_logger
from utils.exceptions import AnalysisError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)


# ============================================
# 5. 키워드 카테고리 정의
# ============================================

class KeywordCategory(str, Enum):
    """키워드 카테고리"""
    PERSON = "person"       # 인물
    PLACE = "place"         # 장소
    FOOD = "food"           # 음식
    EVENT = "event"         # 사건
    TIME = "time"           # 시간
    EMOTION = "emotion"     # 감정
    ACTIVITY = "activity"   # 활동
    OBJECT = "object"       # 사물
    CONCEPT = "concept"     # 개념
    OTHER = "other"         # 기타


# ============================================
# 6. 응답 모델
# ============================================

class Keyword(BaseModel):
    """
    추출된 키워드

    Attributes:
        word: 키워드
        importance: 중요도 (0.0~1.0)
        category: 카테고리
        context: 문맥/설명
    """
    word: str = Field(..., description="키워드")
    importance: float = Field(..., ge=0.0, le=1.0, description="중요도 (0.0~1.0)")
    category: KeywordCategory = Field(default=KeywordCategory.OTHER, description="카테고리")
    context: str = Field(default="", description="문맥/설명")


class KeywordExtractionResult(BaseModel):
    """
    키워드 추출 결과

    Attributes:
        keywords: 추출된 키워드 리스트
        main_topic: 주요 주제
        sub_topics: 하위 주제들
    """
    keywords: List[Keyword] = Field(default_factory=list, description="추출된 키워드")
    main_topic: str = Field(default="", description="주요 주제")
    sub_topics: List[str] = Field(default_factory=list, description="하위 주제들")


# ============================================
# 7. 키워드 추출기 클래스
# ============================================

class KeywordExtractor:
    """
    키워드 추출기

    OpenAI API를 사용하여 텍스트에서 핵심 키워드와 주제 추출.

    Attributes:
        llm_service: LLM 서비스 인스턴스
        max_keywords: 최대 키워드 개수

    Example:
        >>> extractor = KeywordExtractor()
        >>> result = await extractor.extract("오늘 점심에 된장찌개 먹었어요")
        >>> print(result.keywords[0].word)
        "된장찌개"
        >>> print(result.main_topic)
        "식사"
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        max_keywords: int = 10
    ):
        """
        KeywordExtractor 초기화

        Args:
            llm_service: LLM 서비스 (None이면 기본 인스턴스 사용)
            max_keywords: 최대 키워드 개수
        """
        self.llm_service = llm_service or default_llm_service
        self.max_keywords = max_keywords

        logger.info(
            f"KeywordExtractor initialized",
            extra={"max_keywords": max_keywords}
        )

    async def extract(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> KeywordExtractionResult:
        """
        텍스트에서 키워드 추출

        Args:
            text: 분석할 텍스트
            context: 추가 컨텍스트 정보 (선택)

        Returns:
            KeywordExtractionResult: 키워드 추출 결과

        Raises:
            AnalysisError: 추출 실패 시

        Example:
            >>> extractor = KeywordExtractor()
            >>> result = await extractor.extract(
            ...     "어제 딸이 집에 와서 김치찌개 끓여줬어요. 정말 맛있었어요."
            ... )
            >>> print(result.keywords[0].word)
            "딸"
            >>> print(result.keywords[0].category)
            KeywordCategory.PERSON
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for keyword extraction")
                return KeywordExtractionResult()

            logger.debug(f"Extracting keywords from text: {text[:100]}...")

            # 프롬프트 생성
            prompt = KEYWORD_EXTRACTION_PROMPT.format(text=text)

            # LLM 호출 (JSON 모드)
            response = await self.llm_service.call_json(
                prompt=prompt,
                system_prompt="당신은 텍스트 분석 전문가입니다. 한국어 텍스트에서 핵심 키워드를 정확하게 추출합니다.",
                temperature=0.3,  # 낮은 온도로 일관성 유지
                max_tokens=800
            )

            # 응답 파싱
            result = self._parse_response(response)

            logger.info(
                f"Keywords extracted: {len(result.keywords)} keywords",
                extra={
                    "text_length": len(text),
                    "keyword_count": len(result.keywords),
                    "main_topic": result.main_topic,
                    "top_keywords": [kw.word for kw in result.keywords[:3]]
                }
            )

            return result

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to extract keywords: {e}") from e

    def _parse_response(self, response: Dict[str, Any]) -> KeywordExtractionResult:
        """
        LLM 응답 파싱

        Args:
            response: LLM JSON 응답

        Returns:
            KeywordExtractionResult: 파싱된 결과

        Raises:
            ValueError: 파싱 실패 시
        """
        try:
            # Keywords
            keywords = []
            for kw in response.get("keywords", []):
                # 카테고리 파싱 (잘못된 값은 OTHER로)
                try:
                    category = KeywordCategory(kw.get("category", "other"))
                except ValueError:
                    category = KeywordCategory.OTHER

                keywords.append(
                    Keyword(
                        word=kw["word"],
                        importance=float(kw.get("importance", 0.5)),
                        category=category,
                        context=kw.get("context", "")
                    )
                )

            # 중요도 순으로 정렬
            keywords.sort(key=lambda x: x.importance, reverse=True)

            # 최대 개수 제한
            keywords = keywords[:self.max_keywords]

            # Main topic & sub topics
            main_topic = response.get("main_topic", "")
            sub_topics = response.get("sub_topics", [])

            return KeywordExtractionResult(
                keywords=keywords,
                main_topic=main_topic,
                sub_topics=sub_topics
            )

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse keyword response: {e}", exc_info=True)
            logger.error(f"Raw response: {response}")
            raise ValueError(f"Invalid keyword response format: {e}") from e

    async def extract_batch(
        self,
        texts: List[str]
    ) -> List[KeywordExtractionResult]:
        """
        여러 텍스트에서 키워드를 동시에 추출

        Args:
            texts: 분석할 텍스트 리스트

        Returns:
            List[KeywordExtractionResult]: 키워드 추출 결과 리스트

        Example:
            >>> extractor = KeywordExtractor()
            >>> texts = [
            ...     "오늘 딸과 함께 밥 먹었어요",
            ...     "손녀가 학교에서 상 받았대요"
            ... ]
            >>> results = await extractor.extract_batch(texts)
            >>> print(len(results))
            2
        """
        import asyncio

        tasks = [self.extract(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 에러 처리
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch keyword extraction failed for text {i}: {result}")
                # Fallback to empty result
                final_results.append(KeywordExtractionResult())
            else:
                final_results.append(result)

        return final_results

    def get_keywords_by_category(
        self,
        result: KeywordExtractionResult,
        category: KeywordCategory
    ) -> List[Keyword]:
        """
        특정 카테고리의 키워드만 필터링

        Args:
            result: 키워드 추출 결과
            category: 필터링할 카테고리

        Returns:
            List[Keyword]: 필터링된 키워드 리스트

        Example:
            >>> extractor = KeywordExtractor()
            >>> result = await extractor.extract("딸과 함께 뒷산에 갔어요")
            >>> people = extractor.get_keywords_by_category(
            ...     result,
            ...     KeywordCategory.PERSON
            ... )
            >>> print(people[0].word)
            "딸"
        """
        return [kw for kw in result.keywords if kw.category == category]

    def get_top_keywords(
        self,
        result: KeywordExtractionResult,
        n: int = 5
    ) -> List[Keyword]:
        """
        상위 N개 키워드 반환

        Args:
            result: 키워드 추출 결과
            n: 반환할 키워드 개수

        Returns:
            List[Keyword]: 상위 N개 키워드

        Example:
            >>> extractor = KeywordExtractor()
            >>> result = await extractor.extract("긴 텍스트...")
            >>> top_5 = extractor.get_top_keywords(result, n=5)
            >>> print([kw.word for kw in top_5])
            ['키워드1', '키워드2', '키워드3', '키워드4', '키워드5']
        """
        return result.keywords[:n]

    def get_category_label_kr(self, category: KeywordCategory) -> str:
        """
        키워드 카테고리의 한국어 레이블 반환

        Args:
            category: 키워드 카테고리

        Returns:
            str: 한국어 레이블

        Example:
            >>> extractor = KeywordExtractor()
            >>> label = extractor.get_category_label_kr(KeywordCategory.PERSON)
            >>> print(label)
            "인물"
        """
        labels = {
            KeywordCategory.PERSON: "인물",
            KeywordCategory.PLACE: "장소",
            KeywordCategory.FOOD: "음식",
            KeywordCategory.EVENT: "사건",
            KeywordCategory.TIME: "시간",
            KeywordCategory.EMOTION: "감정",
            KeywordCategory.ACTIVITY: "활동",
            KeywordCategory.OBJECT: "사물",
            KeywordCategory.CONCEPT: "개념",
            KeywordCategory.OTHER: "기타"
        }
        return labels.get(category, "알 수 없음")


# ============================================
# 8. Export
# ============================================
__all__ = [
    "KeywordExtractor",
    "KeywordExtractionResult",
    "Keyword",
    "KeywordCategory",
]


logger.info("Keyword extractor module loaded")
