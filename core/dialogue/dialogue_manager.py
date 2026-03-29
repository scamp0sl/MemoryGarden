"""
대화 흐름 관리자

세션 시작/종료, 대화 턴 관리, 컨텍스트 윈도우 관리.
Redis Session Memory를 활용하여 최근 N턴 유지.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

# ============================================
# 2. Third-Party Imports
# ============================================

# ============================================
# 3. Local Imports
# ============================================
from database.redis_client import redis_client
from core.dialogue.response_generator import ResponseGenerator
from core.dialogue.prompt_builder import PromptBuilder
from core.dialogue.time_aware import TimeAwareDialogue  # B4-1
from core.dialogue.response_validator import ResponseValidator  # C3: 출력 검증기
from utils.logger import get_logger
from utils.exceptions import WorkflowError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
MAX_CONTEXT_TURNS = 20  # 최근 20턴 유지 (점심+저녁 대화 맥락 보존)
SESSION_TTL = 86400  # 24시간 (초 단위)
CONTEXT_TTL = 3600  # 1시간 (초 단위)

# 대화 피로도 방지 (1시간 윈도우 기반)
TURN_WINDOW_SECONDS = 3600      # 1시간 윈도우 (초)
MAX_TURNS_PER_WINDOW = 5        # 윈도우 내 연속 턴 수 (5턴 이상 시 피로도 방지 발동)

# 감정 벡터 매핑 테이블 (B2-1~3)
# valence: 긍정(+)/부정(-), arousal: 활성화(+)/진정(-)
EMOTION_VECTOR_MAP = {
    # 긍정 + 고활성
    "기쁨": (0.8, 0.6, 0.1),
    "행복": (0.7, 0.4, 0.1),
    "즐거움": (0.9, 0.7, 0.1),
    "설렘": (0.7, 0.7, 0.1),
    # 긍정 + 진정
    "평온": (0.1, -0.3, 0.0),
    "만족": (0.6, -0.2, 0.1),
    # 부정 + 고활성
    "불안": (-0.5, 0.5, -0.1),
    "짜증": (-0.4, 0.6, -0.1),
    "스트레스": (-0.5, 0.4, 0.0),
    "분노": (-0.7, 0.8, -0.2),
    # 부정 + 진정
    "우울": (-0.8, -0.6, 0.0),
    "슬픔": (-0.7, -0.4, 0.0),
    "피곤": (-0.3, -0.8, 0.0),
    "무기력": (-0.6, -0.7, 0.0),
    # 중립
    "중립": (0.0, 0.0, 0.0),
}
MAX_DELTA_PER_TURN = 0.25  # 한 턴 최대 변화량 (B2-4)


# ============================================
# 6. DialogueManager 클래스
# ============================================


class DialogueManager:
    """대화 흐름 관리자

    세션 생명주기 관리, 대화 턴 추가/조회, 컨텍스트 윈도우 관리.

    Attributes:
        response_generator: AI 응답 생성기
        prompt_builder: 프롬프트 빌더
        max_context_turns: 컨텍스트 윈도우 크기 (최근 N턴)

    Example:
        >>> manager = DialogueManager()
        >>> session_id = await manager.start_session(user_id="user123")
        >>> await manager.add_turn(
        ...     user_id="user123",
        ...     user_message="오늘 점심 뭐 먹었어요",
        ...     assistant_message="된장찌개요"
        ... )
        >>> history = await manager.get_conversation_history("user123")
    """

    def __init__(
        self,
        response_generator: Optional[ResponseGenerator] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        max_context_turns: int = MAX_CONTEXT_TURNS,
        memory_manager = None  # 4계층 메모리 매니저 (선택)
    ):
        """
        DialogueManager 초기화

        Args:
            response_generator: 응답 생성기 (None이면 생성)
            prompt_builder: 프롬프트 빌더 (None이면 생성)
            max_context_turns: 컨텍스트 윈도우 크기
            memory_manager: 4계층 메모리 매니저 (None이면 지연 생성)
        """
        self.response_generator = response_generator or ResponseGenerator()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.max_context_turns = max_context_turns
        self.time_aware = TimeAwareDialogue()  # B4-1: 시간 인식형 대화
        self.response_validator = ResponseValidator()  # C3: 출력 검증기
        self._memory_manager = memory_manager  # 4계층 메모리 (지연 로딩)

        logger.info(
            "DialogueManager initialized",
            extra={"max_context_turns": max_context_turns}
        )

    @property
    def memory_manager(self):
        """4계층 메모리 매니저 (지연 초기화)"""
        if self._memory_manager is None:
            from core.memory.memory_manager import MemoryManager
            from core.nlp.embedder import Embedder
            self._memory_manager = MemoryManager(embedder=Embedder())
            logger.debug("MemoryManager initialized lazily")
        return self._memory_manager

    async def start_session(
        self,
        user_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        대화 세션 시작

        Args:
            user_id: 사용자 ID
            initial_context: 초기 컨텍스트 (선택)
                {
                    "user_name": "홍길동",
                    "garden_name": "행복한 정원",
                    ...
                }

        Returns:
            session_id: 세션 고유 ID

        Example:
            >>> manager = DialogueManager()
            >>> session_id = await manager.start_session(
            ...     user_id="user123",
            ...     initial_context={"user_name": "홍길동"}
            ... )
        """
        session_id = str(uuid4())

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "started_at": datetime.now().isoformat(),
            "last_updated_at": datetime.now().isoformat(),
            "turn_count": 0,
            "context": initial_context or {},
            "conversation_history": []
        }

        # Redis에 저장 (24시간 TTL)
        await redis_client.set_session(
            user_id=user_id,
            session_data=session_data,
            ttl=SESSION_TTL
        )

        logger.info(
            "Session started",
            extra={
                "user_id": user_id,
                "session_id": session_id
            }
        )

        return session_id

    async def end_session(self, user_id: str) -> None:
        """
        대화 세션 종료

        Args:
            user_id: 사용자 ID

        Example:
            >>> manager = DialogueManager()
            >>> await manager.end_session("user123")
        """
        await redis_client.delete_session(user_id)

        logger.info("Session ended", extra={"user_id": user_id})

    async def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 데이터 조회

        Args:
            user_id: 사용자 ID

        Returns:
            세션 데이터 또는 None (세션 없음)

        Example:
            >>> manager = DialogueManager()
            >>> session = await manager.get_session("user123")
            >>> print(session["turn_count"])
        """
        session_data = await redis_client.get_session(user_id)

        if session_data:
            logger.debug(
                "Session retrieved",
                extra={
                    "user_id": user_id,
                    "turn_count": session_data.get("turn_count", 0)
                }
            )

        return session_data

    async def add_turn(
        self,
        user_id: str,
        user_message: str,
        assistant_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        대화 턴 추가

        Args:
            user_id: 사용자 ID
            user_message: 사용자 메시지
            assistant_message: AI 응답
            metadata: 추가 메타데이터 (감정, 분석 결과 등)

        Example:
            >>> manager = DialogueManager()
            >>> await manager.add_turn(
            ...     user_id="user123",
            ...     user_message="오늘 점심 뭐 먹었어요",
            ...     assistant_message="된장찌개요",
            ...     metadata={"emotion": "neutral", "mcdi_score": 78.5}
            ... )
        """
        # 세션 가져오기
        session_data = await self.get_session(user_id)

        if not session_data:
            logger.warning(f"No active session for user {user_id}, creating new session")
            await self.start_session(user_id)
            session_data = await self.get_session(user_id)

        # 대화 턴 추가
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "assistant": assistant_message,
            "metadata": metadata or {}
        }

        session_data["conversation_history"].append(turn)
        session_data["turn_count"] += 1
        session_data["last_updated_at"] = datetime.now().isoformat()

        # 컨텍스트 윈도우 크기 제한 (최근 N턴만 유지)
        if len(session_data["conversation_history"]) > self.max_context_turns:
            # 오래된 턴 제거
            removed_count = len(session_data["conversation_history"]) - self.max_context_turns
            session_data["conversation_history"] = session_data["conversation_history"][removed_count:]

            logger.debug(
                f"Conversation history trimmed: removed {removed_count} old turns",
                extra={"user_id": user_id, "removed_count": removed_count}
            )

        # Redis에 업데이트
        await redis_client.set_session(
            user_id=user_id,
            session_data=session_data,
            ttl=SESSION_TTL
        )

        logger.info(
            "Turn added",
            extra={
                "user_id": user_id,
                "turn_count": session_data["turn_count"],
                "history_length": len(session_data["conversation_history"])
            }
        )

    async def get_conversation_history(
        self,
        user_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        대화 히스토리 조회 (ChatCompletion 형식)

        Args:
            user_id: 사용자 ID
            limit: 최근 N턴만 가져오기 (None이면 전체)

        Returns:
            대화 히스토리
            [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."},
                ...
            ]

        Example:
            >>> manager = DialogueManager()
            >>> history = await manager.get_conversation_history("user123", limit=5)
            >>> print(len(history))  # 최근 5턴 = 10개 메시지 (user + assistant)
        """
        session_data = await self.get_session(user_id)

        if not session_data:
            return []

        conversation_history = session_data.get("conversation_history", [])

        # limit 적용
        if limit:
            conversation_history = conversation_history[-limit:]

        # ChatCompletion 형식으로 변환
        formatted_history = []
        for turn in conversation_history:
            formatted_history.append({
                "role": "user",
                "content": turn["user"]
            })
            formatted_history.append({
                "role": "assistant",
                "content": turn["assistant"]
            })

        logger.debug(
            "Conversation history retrieved",
            extra={
                "user_id": user_id,
                "total_messages": len(formatted_history),
                "turns": len(conversation_history)
            }
        )

        return formatted_history

    async def update_context(
        self,
        user_id: str,
        context_updates: Dict[str, Any]
    ) -> None:
        """
        세션 컨텍스트 업데이트

        Args:
            user_id: 사용자 ID
            context_updates: 업데이트할 컨텍스트
                {
                    "recent_emotion": "기쁨",
                    "biographical_facts": {...}
                }

        Example:
            >>> manager = DialogueManager()
            >>> await manager.update_context(
            ...     user_id="user123",
            ...     context_updates={"recent_emotion": "기쁨"}
            ... )
        """
        session_data = await self.get_session(user_id)

        if not session_data:
            logger.warning(f"No active session for user {user_id}, cannot update context")
            return

        # 컨텍스트 업데이트 (기존 값 유지하며 병합)
        session_data["context"].update(context_updates)
        session_data["last_updated_at"] = datetime.now().isoformat()

        # Redis에 저장
        await redis_client.set_session(
            user_id=user_id,
            session_data=session_data,
            ttl=SESSION_TTL
        )

        logger.debug(
            "Context updated",
            extra={
                "user_id": user_id,
                "updated_keys": list(context_updates.keys())
            }
        )

    async def generate_response(
        self,
        user_id: str,
        user_message: str,
        next_question: Optional[str] = None,
        emotion: Optional[str] = None,
        emotion_intensity: Optional[float] = None,
        mcdi_context: Optional[Dict[str, Any]] = None,  # B3-3: 신규 추가
        relationship_stage: Optional[int] = None  # B1-3: 신규 추가
    ) -> str:
        """
        AI 응답 생성 (컨텍스트 자동 주입)

        Args:
            user_id: 사용자 ID
            user_message: 사용자 메시지
            next_question: 다음 질문 (선택)
            emotion: 감지된 감정 (선택)
            emotion_intensity: 감정 강도 (선택)
            mcdi_context: MCDI 분석 컨텍스트 (선택, B3-3)
            relationship_stage: 관계 Stage 0~4 (선택, B1-3)

        Returns:
            생성된 응답 메시지

        Example:
            >>> manager = DialogueManager()
            >>> response = await manager.generate_response(
            ...     user_id="user123",
            ...     user_message="오늘 점심은 된장찌개요",
            ...     next_question="어떤 반찬과 함께 드셨어요?"
            ... )
        """
        # ========== R-1 수정: 감정 감지를 Stage 업데이트보다 먼저 ==========
        # [R-1] webhook에서 emotion을 전달하지 않으므로 내부에서 감지
        # effective_emotion을 _update_relationship_stage에 전달하여 Stage 진급 정상화
        effective_emotion = emotion or await self._detect_emotion(user_message)
        updated_vector = await self._update_emotion_vector(user_id, effective_emotion)
        # =====================================================

        # B1-2: 관계 Stage 업데이트 (감정 기반)
        if relationship_stage is None:
            relationship_stage = await self._update_relationship_stage(user_id, effective_emotion)
        else:
            # 외부에서 Stage를 받은 경우에도 턴 수는 업데이트
            await self._update_relationship_stage(user_id, effective_emotion)

        # B4-1: 마지막 상호작용 시간 업데이트
        await self.update_last_interaction(user_id)

        # 세션 및 히스토리 가져오기
        session_data = await self.get_session(user_id)

        if not session_data:
            logger.warning(f"No active session for user {user_id}, creating new session")
            await self.start_session(user_id)
            session_data = await self.get_session(user_id)

        conversation_history = await self.get_conversation_history(user_id)
        user_context = session_data.get("context", {})

        # ============================================
        # 4계층 메모리 검색 (Episodic + Biographical)
        # ============================================
        try:
            # 사용자 메시지를 쿼리로 하여 관련 에피소드 기억 검색
            retrieved_memory = await self.memory_manager.retrieve_all(
                user_id=str(user_id),
                query=user_message,
                limit=5  # 최근 5개 에피소드 기억
            )

            # Episodic Memory → user_context에 추가
            episodic_memories = retrieved_memory.get("episodic", [])
            if episodic_memories:
                # 에피소드 기억을 텍스트로 변환 (가장 최근 3개)
                episodic_summary = "\n".join([
                    f"- {mem.get('content', '')[:100]}..."  # 각 기억을 100자로 제한
                    for mem in episodic_memories[:3]
                ])
                user_context["episodic_memories"] = episodic_summary
                logger.debug(
                    f"Retrieved {len(episodic_memories)} episodic memories",
                    extra={"user_id": user_id}
                )

            # Biographical Facts → user_context에 추가
            biographical_facts = retrieved_memory.get("biographical", {})
            if biographical_facts:
                # 기존 biographical_facts와 병합
                existing_facts = user_context.get("biographical_facts", {})
                existing_facts.update(biographical_facts)
                user_context["biographical_facts"] = existing_facts
                logger.debug(
                    f"Retrieved {len(biographical_facts)} biographical facts",
                    extra={"user_id": user_id, "facts": list(biographical_facts.keys())}
                )

        except Exception as me:
            logger.warning(f"Memory retrieval failed (continuing without memories): {me}")
            # 메모리 검색 실패해도 대화는 계속 진행

        # 최근 대화 언급 내용 추출 (맥락 연속성 — LLM이 이전 대화 주제를 자연스럽게 참조하도록)
        if session_data and session_data.get("conversation_history"):
            recent_mentions = [
                turn.get("user", "") for turn in session_data["conversation_history"]
                if turn.get("user") and turn.get("user").strip()
            ]
            if recent_mentions:
                user_context["recent_mentions"] = recent_mentions

        # 대화 피로도 방지 (최근 1시간 내 MAX_TURNS_PER_WINDOW 이상 진행 시 질문 중단)
        recent_turn_count = self._count_recent_turns(session_data, TURN_WINDOW_SECONDS)
        if recent_turn_count >= MAX_TURNS_PER_WINDOW:
            user_context["suppress_questions"] = True
            user_context.pop("story_topic", None)
            next_question = None
            logger.info(
                f"Conversation reached {recent_turn_count} turns in last 1 hour window, "
                f"suppressing further questions for {user_id}"
            )

        # 감정 기반 응답 vs 일반 응답 (B3-3: mcdi_context, B1-3: relationship_stage 전달)
        if emotion and emotion_intensity is not None:
            response = await self.response_generator.generate_empathetic_response(
                user_message=user_message,
                detected_emotion=emotion,
                emotion_intensity=emotion_intensity,
                conversation_history=conversation_history,
                user_context=user_context,
                user_id=user_id,  # B3-4: 쿨다운용 user_id 전달
                mcdi_context=mcdi_context,  # B3-3
                relationship_stage=relationship_stage,  # B1-3
                emotion_vector=updated_vector  # B2-6: 갱신된 벡터 전달 [결함 #11 수정]
            )
        else:
            response = await self.response_generator.generate(
                user_message=user_message,
                conversation_history=conversation_history,
                user_context=user_context,
                next_question=next_question,
                user_id=user_id,  # B3-4: 쿨다운용 user_id 전달
                mcdi_context=mcdi_context,  # B3-3
                relationship_stage=relationship_stage,  # B1-3
                emotion_vector=updated_vector  # B2-6: 갱신된 벡터 전달 [결함 #11 수정]
            )

        # C3: 응답 검증 (부정적 표현 완화, 길이 제한, 중복 방지)
        validation_result = await self.response_validator.validate(
            user_id=user_id,
            response=response,
            user_message=user_message
        )
        response = validation_result["modified"]

        if validation_result["issues"]:
            logger.warning(
                f"Response validation issues for {user_id}: {validation_result['issues']}",
                extra={"user_id": user_id, "issues": validation_result["issues"]}
            )
        if validation_result["warnings"]:
            logger.info(
                f"Response validation warnings for {user_id}: {validation_result['warnings']}",
                extra={"user_id": user_id, "warnings": validation_result["warnings"]}
            )

        logger.info(
            "Response generated via DialogueManager",
            extra={
                "user_id": user_id,
                "with_emotion": emotion is not None,
                "response_length": len(response),
                "has_mcdi_context": mcdi_context is not None  # B3-3
            }
        )

        return response

    async def get_session_stats(self, user_id: str) -> Dict[str, Any]:
        """
        세션 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            세션 통계
            {
                "session_id": "...",
                "turn_count": 15,
                "started_at": "2025-02-10T10:00:00",
                "last_updated_at": "2025-02-10T15:30:00",
                "context_keys": ["user_name", "garden_name", ...]
            }

        Example:
            >>> manager = DialogueManager()
            >>> stats = await manager.get_session_stats("user123")
            >>> print(stats["turn_count"])
        """
        session_data = await self.get_session(user_id)

        if not session_data:
            return {}

        return {
            "session_id": session_data.get("session_id"),
            "turn_count": session_data.get("turn_count", 0),
            "started_at": session_data.get("started_at"),
            "last_updated_at": session_data.get("last_updated_at"),
            "context_keys": list(session_data.get("context", {}).keys()),
            "history_length": len(session_data.get("conversation_history", []))
        }

    # ============================================
    # 워크플로우 통합 메서드 (CLAUDE.md 기반)
    # ============================================

    async def plan_next(
        self,
        user_id: str,
        current_analysis: Dict[str, Any],
        risk_level: str
    ) -> Dict[str, Any]:
        """
        다음 상호작용 계획

        weakest metric 우선 + risk_level 기반 난이도 조정

        Args:
            user_id: 사용자 ID
            current_analysis: 현재 분석 결과
                {
                    "scores": {"LR": 75, "SD": 80, ...},
                    "mcdi_score": 78.5
                }
            risk_level: 위험도 (GREEN/YELLOW/ORANGE/RED)

        Returns:
            다음 계획
            {
                "category": "episodic_recall",
                "difficulty": "medium",
                "question_type": "free_recall"
            }

        Example:
            >>> manager = DialogueManager()
            >>> plan = await manager.plan_next(
            ...     user_id="user123",
            ...     current_analysis={"scores": {"LR": 75, ...}},
            ...     risk_level="YELLOW"
            ... )
            >>> print(plan["category"])
            "episodic_recall"
        """
        logger.debug(f"Planning next interaction for {user_id}")

        # 1. Weakest Metric 찾기
        scores = current_analysis.get("scores", {})
        if not scores:
            # 기본값
            category = "general"
            question_type = "open_ended"
        else:
            # 최저 점수 지표 선택
            min_metric = min(scores.items(), key=lambda x: x[1] if x[1] is not None else 100)
            metric_name, metric_score = min_metric

            # 지표명 → 카테고리 매핑
            category_mapping = {
                "LR": "lexical_richness",
                "SD": "semantic_focus",
                "NC": "narrative",
                "TO": "temporal_orientation",
                "ER": "episodic_recall",
                "RT": "response_speed"
            }
            category = category_mapping.get(metric_name, "general")

            # 질문 유형 결정
            question_type = self._determine_question_type(metric_name, metric_score)

        # 2. 난이도 조정 (risk_level 기반)
        difficulty = self._determine_difficulty(risk_level, scores.get(min_metric[0], 80) if scores else 80)

        # 3. 세션에 계획 저장
        await self.update_context(
            user_id=user_id,
            context_updates={
                "next_category": category,
                "next_difficulty": difficulty,
                "next_question_type": question_type
            }
        )

        plan = {
            "category": category,
            "difficulty": difficulty,
            "question_type": question_type
        }

        logger.info(
            "Next interaction planned",
            extra={
                "user_id": user_id,
                "plan": plan
            }
        )

        return plan

    def _determine_question_type(self, metric_name: str, score: float) -> str:
        """질문 유형 결정"""
        if metric_name == "ER":
            return "free_recall" if score < 70 else "cued_recall"
        elif metric_name == "TO":
            return "time_orientation"
        elif metric_name == "NC":
            return "narrative"
        elif metric_name == "LR":
            return "descriptive"
        elif metric_name == "SD":
            return "focused"
        else:
            return "open_ended"

    def _determine_difficulty(self, risk_level: str, current_score: float) -> str:
        """난이도 결정"""
        # risk_level 기반
        if risk_level == "RED":
            return "easy"
        elif risk_level == "ORANGE":
            return "easy" if current_score < 50 else "medium"
        elif risk_level == "YELLOW":
            return "medium"
        else:  # GREEN
            return "medium" if current_score > 80 else "hard"

    async def generate_confound_question(
        self,
        user_id: str
    ) -> str:
        """
        교란 변수 확인 질문 생성

        점수 하락 시 수면/우울/약물 등 확인

        Args:
            user_id: 사용자 ID

        Returns:
            교란 변수 질문

        Example:
            >>> manager = DialogueManager()
            >>> question = await manager.generate_confound_question("user123")
            >>> print(question)
            "요즘 잠은 잘 주무시나요?"
        """
        logger.debug(f"Generating confound question for {user_id}")

        # 교란 변수 질문 풀 (순환)
        confound_questions = [
            "요즘 잠은 잘 주무시나요?",
            "기분이 어떠신가요? 평소와 다른 점은 없으신가요?",
            "최근에 드시는 약이 바뀌셨거나 새로 추가된 건 없으신가요?",
            "요즘 몸 어디 불편한 곳은 없으신가요?",
            "요즘 걱정되는 일이나 스트레스 받는 일이 있으신가요?"
        ]

        # 세션에서 마지막 사용한 인덱스 가져오기
        session_data = await self.get_session(user_id)
        last_confound_index = session_data.get("context", {}).get("last_confound_index", -1) if session_data else -1

        # 다음 질문 선택 (순환)
        next_index = (last_confound_index + 1) % len(confound_questions)
        question = confound_questions[next_index]

        # 인덱스 저장
        await self.update_context(
            user_id=user_id,
            context_updates={"last_confound_index": next_index}
        )

        logger.info(
            "Confound question generated",
            extra={
                "user_id": user_id,
                "question_index": next_index
            }
        )

        return question

    async def generate_next_question(
        self,
        user_id: str,
        category: str,
        difficulty: str,
        question_type: str
    ) -> str:
        """
        다음 질문 생성

        카테고리, 난이도, 질문 유형에 맞는 질문 생성

        Args:
            user_id: 사용자 ID
            category: 질문 카테고리
            difficulty: 난이도 (easy/medium/hard)
            question_type: 질문 유형

        Returns:
            생성된 질문

        Example:
            >>> manager = DialogueManager()
            >>> question = await manager.generate_next_question(
            ...     user_id="user123",
            ...     category="episodic_recall",
            ...     difficulty="medium",
            ...     question_type="free_recall"
            ... )
        """
        logger.debug(
            f"Generating next question",
            extra={
                "category": category,
                "difficulty": difficulty,
                "question_type": question_type
            }
        )

        # 프롬프트 빌더를 사용하여 질문 생성
        question = await self.prompt_builder.build_question(
            category=category,
            difficulty=difficulty,
            question_type=question_type
        )

        logger.info(
            "Next question generated",
            extra={
                "user_id": user_id,
                "question_length": len(question)
            }
        )

        return question


# ============================================
# 7. Relationship Stage Methods (B1-1, B1-2)
# ============================================

    async def _get_or_init_relationship(self, user_id: str) -> Dict[str, Any]:
        """관계 데이터 조회 또는 초기화 (B1-1)

        Redis 키: relationship:{user_id} (TTL 없음, 영구 보존)

        Args:
            user_id: 사용자 ID

        Returns:
            관계 데이터 딕셔너리
            {
                "stage": 0,
                "total_turns": 0,
                "total_days": 0,
                "first_interaction": "2025-02-10T10:00:00",
                "last_interaction": "2025-02-10T15:30:00",
                "positive_events": 0,
                "conflict_events": 0,
                "recovery_events": 0
            }
        """
        key = f"relationship:{user_id}"
        data = await redis_client.get_json(key)

        if not data:
            # 초기 관계 데이터 생성
            now_iso = datetime.now().isoformat()
            data = {
                "stage": 0,
                "total_turns": 0,
                "total_days": 0,
                "first_interaction": now_iso,
                "last_interaction": now_iso,
                "positive_events": 0,
                "conflict_events": 0,
                "recovery_events": 0
            }
            await redis_client.set_json(key, data)
            logger.info(f"Relationship data initialized for user {user_id}")

        return data

    async def _update_relationship_stage(
        self,
        user_id: str,
        emotion: Optional[str] = None
    ) -> int:
        """관계 Stage 업데이트 (B1-2)

        Args:
            user_id: 사용자 ID
            emotion: 감지된 감정 (선택)

        Returns:
            업데이트된 Stage (0~4)
        """
        rel = await self._get_or_init_relationship(user_id)

        # 턴 수 증가
        rel["total_turns"] += 1
        rel["last_interaction"] = datetime.now().isoformat()

        # 대화 일수 계산
        first_dt = datetime.fromisoformat(rel["first_interaction"])
        rel["total_days"] = (datetime.now() - first_dt).days

        # 감정 이벤트 기록
        positive_emotions = ["기쁨", "행복", "감동", "설렘", "만족", "즐거움"]
        negative_emotions = ["우울", "슬픔", "불안", "짜증", "스트레스", "분노"]

        # 갈등 상태 추적 변수 초기화
        rel["_was_negative"] = rel.get("_was_negative", False)

        if emotion:
            if any(e in emotion for e in positive_emotions):
                rel["positive_events"] += 1
                # ========== B1 수정: 갈등 후 긍정 전환 감지 ==========
                if rel["_was_negative"]:
                    rel["recovery_events"] += 1
                    rel["_was_negative"] = False
                    logger.info(
                        f"Recovery event detected for {user_id}",
                        extra={"recovery_count": rel["recovery_events"]}
                    )
                # ===============================================
            elif any(e in emotion for e in negative_emotions):
                rel["conflict_events"] += 1
                rel["_was_negative"] = True  # 갈등 상태 표시

        # Stage 진급 조건
        current_stage = rel["stage"]
        new_stage = current_stage

        if current_stage == 0:
            # Stage 0 → 1: 3일 이상 또는 20턴 이상
            if rel["total_days"] >= 3 or rel["total_turns"] >= 20:
                new_stage = 1
        elif current_stage == 1:
            # Stage 1 → 2: 7일 이상 + 긍정 3회 이상
            if rel["total_days"] >= 7 and rel["positive_events"] >= 3:
                new_stage = 2
        elif current_stage == 2:
            # Stage 2 → 3: 14일 이상 + 긍정 10회 이상
            if rel["total_days"] >= 14 and rel["positive_events"] >= 10:
                new_stage = 3
        elif current_stage == 3:
            # Stage 3 → 4: 30일 이상 + 회복 1회 이상
            # (회복: 갈등 후 긍정 전환)
            if rel["total_days"] >= 30 and rel["recovery_events"] >= 1:
                new_stage = 4

        # Stage 변경 시 로그
        if new_stage != current_stage:
            logger.info(
                f"Relationship stage upgraded: {current_stage} → {new_stage}",
                extra={
                    "user_id": user_id,
                    "total_turns": rel["total_turns"],
                    "total_days": rel["total_days"]
                }
            )
            rel["stage"] = new_stage

        # 저장
        key = f"relationship:{user_id}"
        await redis_client.set_json(key, rel)

        return new_stage

    async def get_relationship_stage(self, user_id: str) -> int:
        """현재 관계 Stage 조회

        Args:
            user_id: 사용자 ID

        Returns:
            현재 Stage (0~4)
        """
        rel = await self._get_or_init_relationship(user_id)
        return rel.get("stage", 0)

    async def get_last_conversation_mode(self, user_id: str) -> str:
        """
        마지막 대화 모드 조회

        Args:
            user_id: 사용자 ID

        Returns:
            대화 모드 ("normal", "sd_focused", 등)
            현재는 항상 "normal" 반환
        """
        # TODO: 추세 지향(Semantic Drift) 강화 모드 등 추가 가능
        return "normal"


# ============================================
# 7. Emotion Vector Methods (B2-1~6)
# ============================================

    async def _detect_emotion(self, text: str) -> str:
        """간단 감정 인식 (B2-7)

        [결함 #1 수정] EMOTION_VECTOR_MAP의 키와 일치하는 한국어 감정 라벨 반환
        [결함 #14] webhook에서 emotion을 전달하지 않을 때의 내부 fallback

        Args:
            text: 사용자 메시지

        Returns:
            "기쁨", "우울", "분노", "불안", "피곤", "중립" 중 하나
        """
        emotion_keywords = {
            "기쁨": ["기쁘", "좋아", "행복", "즐겁", "신나", "ㅋㅋ", "ㅎㅎ", "대박"],
            "우울": ["슬프", "우울", "쓸쓸", "외롭", "ㅠㅠ", "ㅜㅜ"],
            "분노": ["화나", "짜증", "속상", "억울", "미치"],
            "불안": ["무섭", "두렵", "걱정"],
            "피곤": ["피곤", "힘들", "지치"],
        }

        for emotion, keywords in emotion_keywords.items():
            if any(keyword in text for keyword in keywords):
                return emotion

        return "중립"

    async def _update_emotion_vector(
        self,
        user_id: str,
        emotion_label: str
    ) -> Dict[str, float]:
        """감정 벡터 업데이트 (B2-4~5)

        Args:
            user_id: 사용자 ID
            emotion_label: 감정 레이블 (예: "기쁨", "우울")

        Returns:
            업데이트된 벡터 {"v": valence, "a": arousal, "i": intimacy}
        """
        key = f"emotion_vector:{user_id}"
        current = await redis_client.get_json(key)

        if not current:
            # 초기 벡터 (중립, 약간 친박함)
            current = {"v": 0.0, "a": 0.0, "i": 0.5}
            await redis_client.set_json(key, current, ttl=86400)  # 24시간 TTL

        # 목표 벡터 가져오기
        target = EMOTION_VECTOR_MAP.get(emotion_label, (0.0, 0.0, 0.0))
        target_v, target_a, target_i_delta = target

        # 한 턴 최대 변화량 제한 (clamp_delta 함수)
        def clamp_delta(current_val: float, target_val: float) -> float:
            delta = target_val - current_val
            delta = max(-MAX_DELTA_PER_TURN, min(MAX_DELTA_PER_TURN, delta))
            return max(-1.0, min(1.0, current_val + delta))

        new_vector = {
            "v": clamp_delta(current["v"], target_v),
            "a": clamp_delta(current["a"], target_a),
            "i": clamp_delta(current["i"], current["i"] + target_i_delta)
        }

        await redis_client.set_json(key, new_vector, ttl=86400)

        logger.debug(
            f"Emotion vector updated: {current} → {new_vector}",
            extra={
                "user_id": user_id,
                "emotion": emotion_label,
                "delta": f"v={new_vector['v']-current['v']:.2f}, "
                       f"a={new_vector['a']-current['a']:.2f}, "
                       f"i={new_vector['i']-current['i']:.2f}"
            }
        )

        return new_vector

    async def get_emotion_vector(self, user_id: str) -> Dict[str, float]:
        """감정 벡터 조회

        Args:
            user_id: 사용자 ID

        Returns:
            현재 감정 벡터 {"v": valence, "a": arousal, "i": intimacy}
        """
        key = f"emotion_vector:{user_id}"
        vector = await redis_client.get_json(key)

        if not vector:
            # 초기 벡터 반환
            return {"v": 0.0, "a": 0.0, "i": 0.5}

        return vector


# ============================================
# 9. Time-Aware Dialogue Methods (B4-1~3)
# ============================================

    async def update_last_interaction(self, user_id: str) -> None:
        """마지막 상호작용 시간 업데이트 (B4-1)

        Redis 키: last_interaction:{user_id} (TTL 없음)

        Args:
            user_id: 사용자 ID
        """
        key = f"last_interaction:{user_id}"
        now_iso = datetime.now().isoformat()
        await redis_client.set(key, now_iso)
        logger.debug(f"Last interaction updated for {user_id}: {now_iso}")

    async def get_last_interaction(self, user_id: str) -> Optional[datetime]:
        """마지막 상호작용 시간 조회 (B4-1)

        Args:
            user_id: 사용자 ID

        Returns:
            마지막 상호작용 시간 또는 None
        """
        key = f"last_interaction:{user_id}"
        last_str = await redis_client.get(key)

        if not last_str:
            return None

        try:
            return datetime.fromisoformat(last_str)
        except (ValueError, TypeError):
            return None

    async def get_hours_since_last_interaction(
        self,
        user_id: str
    ) -> Optional[float]:
        """마지막 상호작용 경과 시간 (시간 단위) (B4-2)

        Args:
            user_id: 사용자 ID

        Returns:
            경과 시간 (시간) 또는 None (첫 상호작용인 경우)
        """
        last_interaction = await self.get_last_interaction(user_id)

        if not last_interaction:
            return None

        now = datetime.now()
        delta = now - last_interaction
        return delta.total_seconds() / 3600  # 시간 단위 변환

    async def generate_gap_message(
        self,
        user_id: str,
        include_time_greeting: bool = True
    ) -> Optional[str]:
        """경과 시간 기반 Gap 메시지 생성 (B4-3)

        Args:
            user_id: 사용자 ID
            include_time_greeting: 시간대별 인사 포함 여부

        Returns:
            Gap 메시지 또는 None (첫 상호작용인 경우)

        Example:
            >>> manager = DialogueManager()
            >>> msg = await manager.generate_gap_message("user123")
            >>> print(msg)
            "저녁 식사는 맛있게 하셨나요? 정원이 노을빛으로 물들고 있어요.

            정말 오랜만이에요 정원의 식물들이 보고 싶어 했어요."
        """
        hours = await self.get_hours_since_last_interaction(user_id)

        if hours is None:
            # 첫 상호작용
            return None

        # 시간대별 인사 생성
        time_msg = ""
        if include_time_greeting:
            time_of_day = self.time_aware.get_time_of_day()
            time_msg = self.time_aware.generate_time_greeting(time_of_day)

        # Gap 메시지 생성
        gap_msg = self.time_aware.generate_gap_message(hours)

        # 결합
        if time_msg:
            return f"{time_msg}\n\n{gap_msg}"
        return gap_msg

    def _count_recent_turns(
        self,
        session_data: Dict[str, Any],
        window_seconds: int = TURN_WINDOW_SECONDS
    ) -> int:
        """최근 N초 내 발생한 대화 턴 수 계산 (슬라이딩 윈도우)

        대화 피로도 방지를 위해 최근 1시간 내 턴 수를 계산합니다.
        1시간 이상 쉬고 돌아오면 카운터가 리셋되어 다시 대화 가능.

        Args:
            session_data: 세션 데이터 (conversation_history 포함)
            window_seconds: 시간 윈도우 (기본: 1시간 = 3600초)

        Returns:
            최근 윈도우 내 턴 수
        """
        from datetime import timedelta

        history = session_data.get("conversation_history", [])
        if not history:
            return 0

        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)

        recent_count = 0
        for turn in history:
            turn_time_str = turn.get("timestamp", "")
            if turn_time_str:
                try:
                    turn_time = datetime.fromisoformat(turn_time_str)
                    if turn_time >= cutoff_time:
                        recent_count += 1
                except (ValueError, TypeError):
                    pass

        return recent_count


# ============================================
# 10. Export
# ============================================
__all__ = [
    "DialogueManager",
]

logger.info("Dialogue manager module loaded")
