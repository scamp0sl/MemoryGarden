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
from utils.logger import get_logger
from utils.exceptions import WorkflowError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
MAX_CONTEXT_TURNS = 10  # 최근 10턴 유지 (SPEC.md 기준)
SESSION_TTL = 86400  # 24시간 (초 단위)
CONTEXT_TTL = 3600  # 1시간 (초 단위)


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
        max_context_turns: int = MAX_CONTEXT_TURNS
    ):
        """
        DialogueManager 초기화

        Args:
            response_generator: 응답 생성기 (None이면 생성)
            prompt_builder: 프롬프트 빌더 (None이면 생성)
            max_context_turns: 컨텍스트 윈도우 크기
        """
        self.response_generator = response_generator or ResponseGenerator()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.max_context_turns = max_context_turns

        logger.info(
            "DialogueManager initialized",
            extra={"max_context_turns": max_context_turns}
        )

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
        emotion_intensity: Optional[float] = None
    ) -> str:
        """
        AI 응답 생성 (컨텍스트 자동 주입)

        Args:
            user_id: 사용자 ID
            user_message: 사용자 메시지
            next_question: 다음 질문 (선택)
            emotion: 감지된 감정 (선택)
            emotion_intensity: 감정 강도 (선택)

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
        # 세션 및 히스토리 가져오기
        session_data = await self.get_session(user_id)

        if not session_data:
            logger.warning(f"No active session for user {user_id}, creating new session")
            await self.start_session(user_id)
            session_data = await self.get_session(user_id)

        conversation_history = await self.get_conversation_history(user_id)
        user_context = session_data.get("context", {})

        # 감정 기반 응답 vs 일반 응답
        if emotion and emotion_intensity is not None:
            response = await self.response_generator.generate_empathetic_response(
                user_message=user_message,
                detected_emotion=emotion,
                emotion_intensity=emotion_intensity,
                conversation_history=conversation_history,
                user_context=user_context
            )
        else:
            response = await self.response_generator.generate(
                user_message=user_message,
                conversation_history=conversation_history,
                user_context=user_context,
                next_question=next_question
            )

        logger.info(
            "Response generated via DialogueManager",
            extra={
                "user_id": user_id,
                "with_emotion": emotion is not None,
                "response_length": len(response)
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
            "요즘 잠은 잘 주무시나요? 🌙"
        """
        logger.debug(f"Generating confound question for {user_id}")

        # 교란 변수 질문 풀 (순환)
        confound_questions = [
            "요즘 잠은 잘 주무시나요? 🌙",
            "기분이 어떠신가요? 평소와 다른 점은 없으신가요? 😊",
            "최근에 드시는 약이 바뀌셨거나 새로 추가된 건 없으신가요? 💊",
            "요즘 몸 어디 불편한 곳은 없으신가요? 🏥",
            "요즘 걱정되는 일이나 스트레스 받는 일이 있으신가요? 💭"
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
# 8. Export
# ============================================
__all__ = [
    "DialogueManager",
]

logger.info("Dialogue manager module loaded")
