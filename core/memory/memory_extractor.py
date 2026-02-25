"""
기억 추출기

대화에서 기억할 만한 내용(사건, 감정, 사람, 장소 등)을 추출.
OpenAI API를 사용하여 중요 정보를 구조화.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

# ============================================
# 2. Third-Party Imports
# ============================================
from pydantic import BaseModel, Field

# ============================================
# 3. Local Imports
# ============================================
from services.llm_service import LLMService, default_llm_service
from config.prompts import FACT_EXTRACTION_PROMPT
from utils.logger import get_logger
from utils.exceptions import AnalysisError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)


# ============================================
# 5. 상수 및 Enum 정의
# ============================================

class MemoryType(str, Enum):
    """기억 유형"""
    EPISODIC = "episodic"          # 일화적 기억 (사건, 경험)
    BIOGRAPHICAL = "biographical"   # 전기적 사실 (불변/반불변)
    EMOTIONAL = "emotional"         # 감정 기억
    PROCEDURAL = "procedural"       # 절차 기억 (습관, 루틴)


class FactType(str, Enum):
    """사실 유형"""
    IMMUTABLE = "immutable"         # 불변 (이름, 생년월일)
    SEMI_IMMUTABLE = "semi_immutable"  # 반불변 (거주지, 직업)
    PREFERENCE = "preference"       # 선호도 (음식, 취미)
    TEMPORARY = "temporary"         # 일시적 (오늘 먹은 음식)


class EntityCategory(str, Enum):
    """엔티티 카테고리"""
    PERSON = "person"         # 인물
    PLACE = "place"          # 장소
    FOOD = "food"            # 음식
    EVENT = "event"          # 사건
    TIME = "time"            # 시간
    EMOTION = "emotion"      # 감정
    ACTIVITY = "activity"    # 활동
    OBJECT = "object"        # 사물
    HEALTH = "health"        # 건강 상태


# ============================================
# 6. 응답 모델
# ============================================

class ExtractedFact(BaseModel):
    """추출된 사실"""
    entity: str = Field(..., description="엔티티 이름 (예: daughter_name)")
    value: str = Field(..., description="값 (예: 수진)")
    category: EntityCategory = Field(..., description="카테고리")
    fact_type: FactType = Field(..., description="사실 유형")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도 (0.0~1.0)")
    context: str = Field(default="", description="문맥 설명")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ExtractedMemory(BaseModel):
    """추출된 기억"""
    memory_type: MemoryType = Field(..., description="기억 유형")
    content: str = Field(..., description="기억 내용")
    category: EntityCategory = Field(..., description="카테고리")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도")
    importance: float = Field(..., ge=0.0, le=1.0, description="중요도")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


class MemoryExtractionResult(BaseModel):
    """기억 추출 결과"""
    episodic_memories: List[ExtractedMemory] = Field(default_factory=list)
    biographical_facts: List[ExtractedFact] = Field(default_factory=list)
    emotional_memories: List[ExtractedMemory] = Field(default_factory=list)
    key_entities: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = Field(default="", description="대화 요약")


# ============================================
# 7. MemoryExtractor 클래스
# ============================================

class MemoryExtractor:
    """기억 추출기

    대화에서 기억할 만한 내용을 OpenAI API로 분석하여 추출.

    Attributes:
        llm_service: LLM 서비스 인스턴스

    Example:
        >>> extractor = MemoryExtractor()
        >>> result = await extractor.extract(
        ...     conversation_history=[
        ...         {"role": "user", "content": "딸 이름은 수진이에요"},
        ...         {"role": "assistant", "content": "수진 씨 멋진 이름이네요!"}
        ...     ]
        ... )
        >>> print(result.biographical_facts[0].value)
        "수진"
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        MemoryExtractor 초기화

        Args:
            llm_service: LLM 서비스 (None이면 기본 인스턴스 사용)
        """
        self.llm_service = llm_service or default_llm_service
        logger.info("MemoryExtractor initialized")

    async def extract(
        self,
        conversation_history: List[Dict[str, str]],
        current_emotion: Optional[str] = None,
        current_datetime: Optional[datetime] = None
    ) -> MemoryExtractionResult:
        """
        대화에서 기억 추출

        Args:
            conversation_history: 대화 히스토리
                [
                    {"role": "user", "content": "..."},
                    {"role": "assistant", "content": "..."}
                ]
            current_emotion: 현재 감정 상태 (선택)
            current_datetime: 현재 날짜/시간 (선택, 기본: 현재 시간)

        Returns:
            MemoryExtractionResult: 추출된 기억들

        Raises:
            AnalysisError: 추출 실패 시

        Example:
            >>> extractor = MemoryExtractor()
            >>> result = await extractor.extract(
            ...     conversation_history=[
            ...         {"role": "user", "content": "오늘 점심에 된장찌개 먹었어요"},
            ...         {"role": "assistant", "content": "맛있게 드셨나요?"},
            ...         {"role": "user", "content": "네, 딸이 끓여줬어요"}
            ...     ],
            ...     current_emotion="joy"
            ... )
        """
        try:
            logger.debug(
                "Extracting memories from conversation",
                extra={"turns": len(conversation_history)}
            )

            if not conversation_history:
                logger.warning("Empty conversation history")
                return MemoryExtractionResult()

            current_datetime = current_datetime or datetime.now()

            # 대화 히스토리를 텍스트로 변환
            formatted_history = self._format_conversation(conversation_history)

            # LLM 호출하여 사실 추출
            prompt = FACT_EXTRACTION_PROMPT.format(
                conversation_history=formatted_history
            )

            response = await self.llm_service.call_json(
                prompt=prompt,
                system_prompt="당신은 대화에서 중요한 사실과 기억을 추출하는 전문가입니다.",
                temperature=0.3,
                max_tokens=1000
            )

            # 응답 파싱
            result = self._parse_extraction_response(
                response,
                current_emotion,
                current_datetime
            )

            logger.info(
                "Memories extracted successfully",
                extra={
                    "episodic_count": len(result.episodic_memories),
                    "biographical_count": len(result.biographical_facts),
                    "emotional_count": len(result.emotional_memories)
                }
            )

            return result

        except Exception as e:
            logger.error(f"Memory extraction failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to extract memories: {e}") from e

    async def extract_from_message(
        self,
        user_message: str,
        assistant_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MemoryExtractionResult:
        """
        단일 메시지 쌍에서 기억 추출

        Args:
            user_message: 사용자 메시지
            assistant_message: AI 응답
            context: 추가 컨텍스트 (감정, 날짜 등)

        Returns:
            MemoryExtractionResult: 추출된 기억들

        Example:
            >>> extractor = MemoryExtractor()
            >>> result = await extractor.extract_from_message(
            ...     user_message="딸 이름은 수진이에요",
            ...     assistant_message="수진 씨 멋진 이름이네요!",
            ...     context={"emotion": "neutral"}
            ... )
        """
        conversation_history = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message}
        ]

        context = context or {}
        current_emotion = context.get("emotion")
        current_datetime = context.get("datetime", datetime.now())

        return await self.extract(
            conversation_history=conversation_history,
            current_emotion=current_emotion,
            current_datetime=current_datetime
        )

    def calculate_importance(
        self,
        memory: ExtractedMemory,
        recency_weight: float = 0.3,
        emotion_weight: float = 0.3,
        novelty_weight: float = 0.4
    ) -> float:
        """
        기억 중요도 점수 계산

        Args:
            memory: 추출된 기억
            recency_weight: 최신성 가중치
            emotion_weight: 감정 강도 가중치
            novelty_weight: 새로움 가중치

        Returns:
            중요도 점수 (0.0~1.0)

        Example:
            >>> extractor = MemoryExtractor()
            >>> memory = ExtractedMemory(
            ...     memory_type=MemoryType.EPISODIC,
            ...     content="딸과 함께 저녁 먹음",
            ...     category=EntityCategory.EVENT,
            ...     confidence=0.9,
            ...     importance=0.8
            ... )
            >>> importance = extractor.calculate_importance(memory)
            >>> print(importance)
            0.85
        """
        # 기본 중요도 (confidence * importance)
        base_importance = memory.confidence * memory.importance

        # 최신성 점수 (최근 1시간 내면 1.0, 24시간 지나면 0.5)
        try:
            timestamp = datetime.fromisoformat(memory.timestamp)
            hours_ago = (datetime.now() - timestamp).total_seconds() / 3600
            recency_score = max(0.5, 1.0 - (hours_ago / 24))
        except:
            recency_score = 0.7  # 기본값

        # 감정 점수 (감정 관련 기억은 더 중요)
        emotion_score = 1.0 if memory.memory_type == MemoryType.EMOTIONAL else 0.7

        # 새로움 점수 (메타데이터에서 추출, 없으면 기본값)
        novelty_score = memory.metadata.get("novelty", 0.7)

        # 가중 평균
        final_importance = (
            base_importance * 0.4 +
            recency_score * recency_weight +
            emotion_score * emotion_weight +
            novelty_score * novelty_weight
        )

        return round(min(1.0, final_importance), 3)

    # ============================================
    # Private Helper Methods
    # ============================================

    def _format_conversation(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """대화 히스토리를 텍스트로 변환"""
        formatted_lines = []
        for turn in conversation_history:
            role = "사용자" if turn["role"] == "user" else "정원사"
            content = turn["content"]
            formatted_lines.append(f"{role}: {content}")
        return "\n".join(formatted_lines)

    def _parse_extraction_response(
        self,
        response: Dict[str, Any],
        current_emotion: Optional[str],
        current_datetime: datetime
    ) -> MemoryExtractionResult:
        """LLM 응답 파싱"""
        try:
            # Biographical facts 파싱
            biographical_facts = []
            for fact in response.get("biographical_facts", []):
                biographical_facts.append(
                    ExtractedFact(
                        entity=fact["entity"],
                        value=fact["value"],
                        category=self._map_to_entity_category(fact.get("entity")),
                        fact_type=FactType(fact.get("fact_type", "preference")),
                        confidence=float(fact.get("confidence", 0.8)),
                        context=fact.get("context", ""),
                        timestamp=current_datetime.isoformat()
                    )
                )

            # Episodic facts 파싱
            episodic_memories = []
            for episode in response.get("episodic_facts", []):
                # timestamp 안전하게 처리
                raw_timestamp = episode.get("timestamp")
                if raw_timestamp and isinstance(raw_timestamp, str) and raw_timestamp.strip():
                    timestamp_value = raw_timestamp
                else:
                    timestamp_value = current_datetime.isoformat()

                episodic_memories.append(
                    ExtractedMemory(
                        memory_type=MemoryType.EPISODIC,
                        content=episode["content"],
                        category=self._normalize_category(episode.get("category", "event")),
                        confidence=float(episode.get("confidence", 0.8)),
                        importance=0.7,  # 기본값
                        timestamp=timestamp_value,
                        metadata={
                            "original_timestamp": raw_timestamp
                        }
                    )
                )

            # 감정 기억 추가 (감정이 있는 경우)
            emotional_memories = []
            if current_emotion and current_emotion != "neutral":
                # episodic_memories 중에서 감정이 포함된 것들을 emotional_memories로 복사
                for memory in episodic_memories:
                    if "감정" in memory.content or "기분" in memory.content:
                        emotional_memories.append(
                            ExtractedMemory(
                                memory_type=MemoryType.EMOTIONAL,
                                content=memory.content,
                                category=EntityCategory.EMOTION,
                                confidence=memory.confidence,
                                importance=0.8,  # 감정 기억은 중요도 높게
                                timestamp=memory.timestamp,
                                metadata={"emotion": current_emotion}
                            )
                        )

            # 주요 엔티티 추출
            key_entities = self._extract_key_entities(
                biographical_facts,
                episodic_memories
            )

            # 요약 생성 (선택)
            summary = self._generate_summary(episodic_memories, biographical_facts)

            return MemoryExtractionResult(
                episodic_memories=episodic_memories,
                biographical_facts=biographical_facts,
                emotional_memories=emotional_memories,
                key_entities=key_entities,
                summary=summary
            )

        except Exception as e:
            logger.error(f"Failed to parse extraction response: {e}", exc_info=True)
            logger.error(f"Raw response: {response}")
            raise ValueError(f"Invalid extraction response format: {e}") from e

    def _normalize_category(self, category_str: str) -> EntityCategory:
        """
        카테고리 문자열을 EntityCategory enum으로 안전하게 변환

        LLM이 잘못된 카테고리를 반환할 경우 유사한 카테고리로 매핑.

        Args:
            category_str: 카테고리 문자열

        Returns:
            EntityCategory enum 값
        """
        # 소문자로 정규화
        category_lower = category_str.lower().strip()

        # 직접 매핑 (정확한 이름)
        try:
            return EntityCategory(category_lower)
        except ValueError:
            pass

        # Fallback 매핑 (유사 단어 처리)
        fallback_mapping = {
            "meal": EntityCategory.FOOD,
            "dish": EntityCategory.FOOD,
            "eating": EntityCategory.FOOD,
            "dining": EntityCategory.FOOD,
            "location": EntityCategory.PLACE,
            "area": EntityCategory.PLACE,
            "human": EntityCategory.PERSON,
            "people": EntityCategory.PERSON,
            "feeling": EntityCategory.EMOTION,
            "mood": EntityCategory.EMOTION,
            "task": EntityCategory.ACTIVITY,
            "action": EntityCategory.ACTIVITY,
            "item": EntityCategory.OBJECT,
            "thing": EntityCategory.OBJECT,
        }

        if category_lower in fallback_mapping:
            logger.warning(
                f"Unknown category '{category_str}' mapped to {fallback_mapping[category_lower].value}"
            )
            return fallback_mapping[category_lower]

        # 최종 fallback: event
        logger.warning(
            f"Unknown category '{category_str}' defaulting to 'event'"
        )
        return EntityCategory.EVENT

    def _map_to_entity_category(self, entity: str) -> EntityCategory:
        """엔티티 이름을 카테고리로 매핑"""
        entity_mapping = {
            "daughter_name": EntityCategory.PERSON,
            "son_name": EntityCategory.PERSON,
            "grandchild_name": EntityCategory.PERSON,
            "spouse_name": EntityCategory.PERSON,
            "hometown": EntityCategory.PLACE,
            "residence": EntityCategory.PLACE,
            "favorite_food": EntityCategory.FOOD,
            "meal": EntityCategory.FOOD,
            "hobby": EntityCategory.ACTIVITY,
            "occupation": EntityCategory.ACTIVITY,
            "health_condition": EntityCategory.HEALTH,
        }
        return entity_mapping.get(entity, EntityCategory.OBJECT)

    def _extract_key_entities(
        self,
        biographical_facts: List[ExtractedFact],
        episodic_memories: List[ExtractedMemory]
    ) -> List[Dict[str, Any]]:
        """주요 엔티티 추출"""
        key_entities = []

        # 전기적 사실에서 추출
        for fact in biographical_facts:
            key_entities.append({
                "type": "biographical",
                "category": fact.category.value,
                "entity": fact.entity,
                "value": fact.value,
                "confidence": fact.confidence
            })

        # 일화 기억에서 추출 (카테고리별 상위 항목)
        category_counts = {}
        for memory in episodic_memories:
            cat = memory.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            key_entities.append({
                "type": "episodic",
                "category": category,
                "count": count
            })

        return key_entities

    def _generate_summary(
        self,
        episodic_memories: List[ExtractedMemory],
        biographical_facts: List[ExtractedFact]
    ) -> str:
        """대화 요약 생성"""
        summary_parts = []

        if biographical_facts:
            summary_parts.append(
                f"전기적 사실 {len(biographical_facts)}개 추출"
            )

        if episodic_memories:
            summary_parts.append(
                f"일화 기억 {len(episodic_memories)}개 추출"
            )

        return ", ".join(summary_parts) if summary_parts else "추출된 기억 없음"


# ============================================
# 8. Export
# ============================================
__all__ = [
    "MemoryExtractor",
    "MemoryExtractionResult",
    "ExtractedMemory",
    "ExtractedFact",
    "MemoryType",
    "FactType",
    "EntityCategory",
]

logger.info("Memory extractor module loaded")
