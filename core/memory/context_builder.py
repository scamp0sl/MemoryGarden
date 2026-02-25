"""
컨텍스트 구성기

기억 기반 대화 컨텍스트 구성.
관련 기억을 검색하여 프롬프트에 주입.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# ============================================
# 2. Third-Party Imports
# ============================================

# ============================================
# 3. Local Imports
# ============================================
from core.memory.memory_manager import MemoryManager
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
MAX_CONTEXT_MEMORIES = 5  # 프롬프트에 포함할 최대 기억 수
RECENCY_WEIGHT = 0.4      # 최신성 가중치
RELEVANCE_WEIGHT = 0.6    # 관련성 가중치


# ============================================
# 6. ContextBuilder 클래스
# ============================================

class ContextBuilder:
    """컨텍스트 구성기

    관련 기억을 검색하여 대화 프롬프트에 주입할 컨텍스트 구성.

    Attributes:
        memory_manager: 기억 관리자

    Example:
        >>> builder = ContextBuilder()
        >>> context = await builder.build_context(
        ...     user_id="user123",
        ...     query="점심",
        ...     current_emotion="joy"
        ... )
        >>> print(context["relevant_memories"])
    """

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """
        ContextBuilder 초기화

        Args:
            memory_manager: 기억 관리자 (None이면 생성)
        """
        self.memory_manager = memory_manager or MemoryManager()
        logger.info("ContextBuilder initialized")

    async def build_context(
        self,
        user_id: str,
        query: Optional[str] = None,
        current_emotion: Optional[str] = None,
        include_biographical: bool = True,
        include_recent: bool = True,
        max_memories: int = MAX_CONTEXT_MEMORIES
    ) -> Dict[str, Any]:
        """
        대화 컨텍스트 구성

        Args:
            user_id: 사용자 ID
            query: 검색 쿼리 (선택)
            current_emotion: 현재 감정 상태 (선택)
            include_biographical: 전기적 사실 포함 여부
            include_recent: 최근 기억 포함 여부
            max_memories: 최대 기억 수

        Returns:
            구성된 컨텍스트
            {
                "user_id": "user123",
                "relevant_memories": [...],
                "biographical_facts": {...},
                "recent_conversation": [...],
                "formatted_context": "..."
            }

        Example:
            >>> builder = ContextBuilder()
            >>> context = await builder.build_context(
            ...     user_id="user123",
            ...     query="딸",
            ...     current_emotion="joy",
            ...     max_memories=5
            ... )
        """
        logger.debug(
            f"Building context for user {user_id}",
            extra={"query": query, "emotion": current_emotion}
        )

        # 모든 기억 검색
        all_memories = await self.memory_manager.retrieve_all(
            user_id=user_id,
            query=query,
            limit=max_memories * 2  # 필터링 여유
        )

        # 관련 기억 선택 및 정렬
        relevant_memories = await self._select_relevant_memories(
            all_memories=all_memories,
            query=query,
            current_emotion=current_emotion,
            max_count=max_memories
        )

        # 전기적 사실 추출
        biographical_facts = {}
        if include_biographical:
            biographical_facts = all_memories.get("biographical", {})

        # 최근 대화 추출
        recent_conversation = []
        if include_recent:
            session_data = all_memories.get("session", {})
            recent_conversation = session_data.get("conversation_history", [])[-5:]

        # 포맷팅된 컨텍스트 문자열 생성
        formatted_context = self._format_context(
            relevant_memories=relevant_memories,
            biographical_facts=biographical_facts,
            recent_conversation=recent_conversation
        )

        context = {
            "user_id": user_id,
            "query": query,
            "current_emotion": current_emotion,
            "relevant_memories": relevant_memories,
            "biographical_facts": biographical_facts,
            "recent_conversation": recent_conversation,
            "formatted_context": formatted_context,
            "built_at": datetime.now().isoformat()
        }

        logger.info(
            "Context built successfully",
            extra={
                "user_id": user_id,
                "memories_count": len(relevant_memories),
                "biographical_count": len(biographical_facts)
            }
        )

        return context

    async def build_prompt_context(
        self,
        user_id: str,
        query: Optional[str] = None,
        current_emotion: Optional[str] = None
    ) -> str:
        """
        프롬프트에 주입할 컨텍스트 문자열 생성

        Args:
            user_id: 사용자 ID
            query: 검색 쿼리 (선택)
            current_emotion: 현재 감정 상태 (선택)

        Returns:
            프롬프트용 컨텍스트 문자열

        Example:
            >>> builder = ContextBuilder()
            >>> context_str = await builder.build_prompt_context(
            ...     user_id="user123",
            ...     query="점심"
            ... )
            >>> print(context_str)
            ## 사용자 정보
            - 이름: 홍길동
            - 딸 이름: 수진

            ## 관련 기억
            - 2025-02-09: 점심에 된장찌개 먹음
            - 2025-02-08: 딸과 함께 저녁 식사
        """
        context = await self.build_context(
            user_id=user_id,
            query=query,
            current_emotion=current_emotion
        )

        return context["formatted_context"]

    async def get_conversation_context(
        self,
        user_id: str,
        last_n_turns: int = 5
    ) -> List[Dict[str, str]]:
        """
        대화 히스토리 컨텍스트 조회 (ChatCompletion 형식)

        Args:
            user_id: 사용자 ID
            last_n_turns: 최근 N턴

        Returns:
            대화 히스토리
            [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]

        Example:
            >>> builder = ContextBuilder()
            >>> history = await builder.get_conversation_context(
            ...     user_id="user123",
            ...     last_n_turns=3
            ... )
        """
        memories = await self.memory_manager.retrieve_all(user_id)
        session_data = memories.get("session", {})
        conversation_history = session_data.get("conversation_history", [])

        # 최근 N턴만 추출
        recent_turns = conversation_history[-last_n_turns:]

        # ChatCompletion 형식으로 변환
        formatted_history = []
        for turn in recent_turns:
            formatted_history.append({
                "role": "user",
                "content": turn["user"]
            })
            formatted_history.append({
                "role": "assistant",
                "content": turn["assistant"]
            })

        return formatted_history

    # ============================================
    # Private Helper Methods
    # ============================================

    async def _select_relevant_memories(
        self,
        all_memories: Dict[str, Any],
        query: Optional[str],
        current_emotion: Optional[str],
        max_count: int
    ) -> List[Dict[str, Any]]:
        """관련성 높은 기억 선택 및 정렬"""
        episodic_memories = all_memories.get("episodic", [])

        if not episodic_memories:
            return []

        # 각 기억에 점수 부여
        scored_memories = []
        for memory in episodic_memories:
            score = self._calculate_relevance_score(
                memory=memory,
                query=query,
                current_emotion=current_emotion
            )
            scored_memories.append((memory, score))

        # 점수 순 정렬
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        # 상위 N개 선택
        selected_memories = [mem for mem, score in scored_memories[:max_count]]

        # 시간순 정렬 (오래된 것부터)
        selected_memories.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=False
        )

        return selected_memories

    def _calculate_relevance_score(
        self,
        memory: Dict[str, Any],
        query: Optional[str],
        current_emotion: Optional[str]
    ) -> float:
        """기억 관련성 점수 계산"""
        # 기본 점수 (confidence * importance)
        base_score = memory.get("confidence", 0.5) * memory.get("importance", 0.5)

        # 최신성 점수
        recency_score = self._calculate_recency_score(
            memory.get("timestamp", "")
        )

        # 관련성 점수
        relevance_score = 0.5  # 기본값

        if query:
            # 키워드 매칭
            content = memory.get("content", "").lower()
            if query.lower() in content:
                relevance_score = 1.0
            else:
                # 부분 매칭
                query_words = query.lower().split()
                match_count = sum(1 for word in query_words if word in content)
                relevance_score = match_count / len(query_words) if query_words else 0.5

        # 감정 매칭
        emotion_bonus = 0.0
        if current_emotion:
            memory_emotion = memory.get("metadata", {}).get("emotion")
            if memory_emotion == current_emotion:
                emotion_bonus = 0.2

        # 최종 점수
        final_score = (
            base_score * 0.3 +
            recency_score * RECENCY_WEIGHT +
            relevance_score * RELEVANCE_WEIGHT +
            emotion_bonus
        )

        return min(1.0, final_score)

    def _calculate_recency_score(self, timestamp_str: str) -> float:
        """최신성 점수 계산"""
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            hours_ago = (datetime.now() - timestamp).total_seconds() / 3600

            # 지수 감쇠
            # 1시간 전: 1.0, 24시간 전: 0.5, 7일 전: 0.2
            if hours_ago < 1:
                return 1.0
            elif hours_ago < 24:
                return 0.5 + 0.5 * (1 - hours_ago / 24)
            elif hours_ago < 168:  # 7일
                return 0.2 + 0.3 * (1 - (hours_ago - 24) / 144)
            else:
                return 0.2

        except:
            return 0.5  # 기본값

    def _format_context(
        self,
        relevant_memories: List[Dict[str, Any]],
        biographical_facts: Dict[str, Any],
        recent_conversation: List[Dict[str, Any]]
    ) -> str:
        """컨텍스트를 프롬프트용 문자열로 포맷팅"""
        context_parts = []

        # 1. 전기적 사실
        if biographical_facts:
            context_parts.append("## 사용자 정보")
            for entity, fact in biographical_facts.items():
                value = fact if isinstance(fact, str) else fact.get("value", "")
                readable_entity = self._format_entity_name(entity)
                context_parts.append(f"- {readable_entity}: {value}")
            context_parts.append("")

        # 2. 관련 기억 (시간순)
        if relevant_memories:
            context_parts.append("## 관련 기억")
            for memory in relevant_memories:
                timestamp = memory.get("timestamp", "")
                content = memory.get("content", "")

                # 날짜만 추출
                try:
                    date_str = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d")
                except:
                    date_str = "날짜 미상"

                context_parts.append(f"- {date_str}: {content}")
            context_parts.append("")

        # 3. 최근 대화 (선택적)
        if recent_conversation and len(recent_conversation) > 0:
            context_parts.append("## 최근 대화")
            for turn in recent_conversation[-3:]:  # 최근 3턴만
                user_msg = turn.get("user", "")
                assistant_msg = turn.get("assistant", "")
                context_parts.append(f"사용자: {user_msg}")
                context_parts.append(f"정원사: {assistant_msg}")
            context_parts.append("")

        return "\n".join(context_parts)

    def _format_entity_name(self, entity: str) -> str:
        """엔티티 이름을 읽기 쉬운 형태로 변환"""
        entity_mapping = {
            "daughter_name": "딸 이름",
            "son_name": "아들 이름",
            "grandchild_name": "손녀/손자 이름",
            "spouse_name": "배우자 이름",
            "hometown": "고향",
            "residence": "거주지",
            "favorite_food": "좋아하는 음식",
            "hobby": "취미",
            "occupation": "직업",
            "health_condition": "건강 상태",
        }
        return entity_mapping.get(entity, entity)

    async def build_enriched_context(
        self,
        user_id: str,
        user_message: str,
        current_emotion: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        사용자 메시지 기반 강화된 컨텍스트 구성

        메시지에서 키워드를 추출하여 더 관련성 높은 기억 검색.

        Args:
            user_id: 사용자 ID
            user_message: 사용자 메시지
            current_emotion: 현재 감정 상태 (선택)

        Returns:
            강화된 컨텍스트

        Example:
            >>> builder = ContextBuilder()
            >>> context = await builder.build_enriched_context(
            ...     user_id="user123",
            ...     user_message="오늘 점심에 딸이랑 같이 밥 먹었어요",
            ...     current_emotion="joy"
            ... )
        """
        # 메시지에서 키워드 추출 (간단한 방법)
        keywords = self._extract_keywords_simple(user_message)

        # 키워드 기반 검색
        query = " ".join(keywords[:3]) if keywords else None

        return await self.build_context(
            user_id=user_id,
            query=query,
            current_emotion=current_emotion
        )

    def _extract_keywords_simple(self, text: str) -> List[str]:
        """간단한 키워드 추출 (명사 우선)"""
        # TODO: 형태소 분석기 사용 (Kiwi)
        # 현재는 단순 단어 분리
        words = text.split()

        # 불용어 제거
        stopwords = {"은", "는", "이", "가", "을", "를", "에", "의", "로", "과", "와"}
        keywords = [w for w in words if w not in stopwords and len(w) > 1]

        return keywords[:5]  # 최대 5개


# ============================================
# 8. Export
# ============================================
__all__ = [
    "ContextBuilder",
]

logger.info("Context builder module loaded")
