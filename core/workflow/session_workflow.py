"""
세션 워크플로우 - 메인 메시지 처리 파이프라인

전체 8단계 워크플로우를 통합 관리 (CLAUDE.md 기반):
1. 컨텍스트 생성
2. 메모리 검색 (4계층 병렬)
3. 응답 분석 (6개 지표 병렬)
4. 위험도 평가
5. 조건부 알림
6. 교란 변수 처리
7. 다음 상호작용 계획
8. 응답 생성 및 메모리 저장

Author: Memory Garden Team
Created: 2025-02-11
Updated: 2025-02-11 (CLAUDE.md 워크플로우 기반으로 전면 개편)
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import time
from typing import Optional, Dict, Any
from datetime import datetime

# ============================================
# 2. Third-Party Imports
# ============================================

# ============================================
# 3. Local Imports
# ============================================
from core.workflow.context import ProcessingContext
from core.memory.memory_manager import MemoryManager
from core.analysis.analyzer import Analyzer
from core.analysis.risk_evaluator import RiskEvaluator
from core.dialogue.dialogue_manager import DialogueManager
from services.notification_service import NotificationService
from utils.logger import get_logger
from utils.exceptions import WorkflowError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
# 알림 트리거 레벨
ALERT_RISK_LEVELS = ["ORANGE", "RED"]

# 교란 변수 체크 트리거 임계값
CONFOUND_CHECK_THRESHOLD = -1.5  # z-score threshold


# ============================================
# 6. SessionWorkflow 클래스
# ============================================


class SessionWorkflow:
    """세션 워크플로우 메인 클래스

    사용자 메시지를 받아 전체 처리 파이프라인을 실행하고 응답을 반환.

    Workflow Steps (CLAUDE.md 기반):
        1. Context Creation: 요청 정보를 ProcessingContext로 캡슐화
        2. Memory Retrieval: 4계층 메모리에서 관련 데이터 병렬 검색
        3. Response Analysis: 6개 MCDI 지표 병렬 분석
        4. Risk Evaluation: Baseline 대비 위험도 평가
        5. Alert Notification: ORANGE/RED 레벨 시 보호자 알림
        6. Confound Check: 점수 하락 시 교란 변수 확인
        7. Next Interaction Planning: weakest metric 기반 다음 질문 계획
        8. Response Generation & Memory Storage: 응답 생성 및 4계층 저장

    Attributes:
        memory_manager: 4계층 메모리 관리자
        analyzer: MCDI 분석기
        risk_evaluator: 위험도 평가기
        dialogue_manager: 대화 관리자
        notification_service: 알림 서비스

    Example:
        >>> workflow = SessionWorkflow(
        ...     memory_manager=memory_manager,
        ...     analyzer=analyzer,
        ...     risk_evaluator=risk_evaluator,
        ...     dialogue_manager=dialogue_manager,
        ...     notification_service=notification_service
        ... )
        >>> response = await workflow.process_message(
        ...     user_id="user123",
        ...     message="봄에 엄마와 쑥을 뜯으러 갔어요"
        ... )
    """

    def __init__(
        self,
        memory_manager: MemoryManager,
        analyzer: Analyzer,
        risk_evaluator: RiskEvaluator,
        dialogue_manager: DialogueManager,
        notification_service: NotificationService
    ):
        """
        SessionWorkflow 초기화

        Args:
            memory_manager: 4계층 메모리 시스템
            analyzer: 6개 지표 분석기
            risk_evaluator: 위험도 평가기
            dialogue_manager: 대화 흐름 관리자
            notification_service: 보호자 알림 서비스
        """
        self.memory_manager = memory_manager
        self.analyzer = analyzer
        self.risk_evaluator = risk_evaluator
        self.dialogue_manager = dialogue_manager
        self.notification_service = notification_service

        logger.info(
            "SessionWorkflow initialized",
            extra={"components": "all"}
        )

    async def process_message(
        self,
        user_id: str,
        message: str,
        message_type: str = "text",
        image_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingContext:
        """
        메시지 처리 메인 엔트리포인트

        전체 8단계 워크플로우를 실행하여 처리 결과를 반환합니다.

        Args:
            user_id: 사용자 고유 ID
            message: 사용자 메시지
            message_type: 메시지 타입 (text/image/selection)
            image_url: 이미지 URL (image 타입일 때)
            metadata: 추가 메타데이터 (response_latency 등)

        Returns:
            ProcessingContext 객체 (응답, MCDI 점수, 위험도 등 포함)

        Raises:
            WorkflowError: 처리 중 복구 불가능한 오류 발생 시

        Example:
            >>> workflow = SessionWorkflow(...)
            >>> ctx = await workflow.process_message(
            ...     user_id="user123",
            ...     message="오늘 아침에 뭐 드셨어요?",
            ...     metadata={"response_latency": 2.5}
            ... )
            >>> print(ctx.response)
            "밥이랑 된장찌개요 🍚"
            >>> print(ctx.mcdi_score)
            78.5
        """
        start_time = time.time()

        logger.info(
            "▶️ Starting message processing",
            extra={
                "user_id": user_id,
                "message_type": message_type,
                "message_length": len(message)
            }
        )

        # ============================================
        # Step 1: 컨텍스트 생성
        # ============================================
        ctx = ProcessingContext(
            user_id=user_id,
            message=message,
            message_type=message_type,
            image_url=image_url,
            timestamp=datetime.now()
        )

        # 메타데이터 병합
        if metadata:
            for key, value in metadata.items():
                setattr(ctx, key, value)

        try:
            # ============================================
            # Step 2: 메모리 검색 (4계층 병렬)
            # ============================================
            ctx = await self._step_retrieve_memory(ctx)

            # ============================================
            # Step 3: 응답 분석 (6개 지표 병렬)
            # ============================================
            ctx = await self._step_analyze_response(ctx)

            # ============================================
            # Step 4: 위험도 평가
            # ============================================
            ctx = await self._step_evaluate_risk(ctx)

            # ============================================
            # Step 5: 조건부 알림 (분기)
            # ============================================
            if ctx.risk_level in ALERT_RISK_LEVELS:
                await self._step_send_alert(ctx)

            # ============================================
            # Step 6: 교란 변수 처리 (분기)
            # ============================================
            if ctx.should_check_confounds:
                ctx = await self._step_handle_confounds(ctx)

            # ============================================
            # Step 7: 다음 상호작용 계획
            # ============================================
            ctx = await self._step_plan_next_interaction(ctx)

            # ============================================
            # Step 8: 응답 생성 및 메모리 저장
            # ============================================
            ctx = await self._step_generate_and_store(ctx)

            # 처리 시간 기록
            ctx.processing_time_ms = (time.time() - start_time) * 1000

            logger.info(
                "✅ Message processing completed successfully",
                extra={
                    "user_id": ctx.user_id,
                    "mcdi_score": ctx.mcdi_score,
                    "risk_level": ctx.risk_level,
                    "processing_time_ms": ctx.processing_time_ms,
                    "response_length": len(ctx.response) if ctx.response else 0
                }
            )

            return ctx

        except Exception as e:
            # 에러 기록
            ctx.error = str(e)
            ctx.processing_time_ms = (time.time() - start_time) * 1000

            logger.error(
                f"❌ Workflow failed: {e}",
                extra={
                    "user_id": ctx.user_id,
                    "error": str(e),
                    "processing_time_ms": ctx.processing_time_ms
                },
                exc_info=True
            )

            # Fallback 응답 생성 및 반환
            ctx = await self._generate_fallback_response(ctx)
            return ctx

    # ============================================
    # Step 2: 메모리 검색
    # ============================================

    async def _step_retrieve_memory(
        self,
        ctx: ProcessingContext
    ) -> ProcessingContext:
        """
        Step 2: 4계층 메모리 검색 (병렬)

        - Session Memory (Redis): 최근 대화 히스토리
        - Episodic Memory (Qdrant): 유사 일화 기억
        - Biographical Memory (Qdrant+PostgreSQL): 전기적 사실
        - Analytical Memory (TimescaleDB): 과거 분석 점수

        Args:
            ctx: 처리 컨텍스트

        Returns:
            메모리가 추가된 컨텍스트
        """
        logger.debug(f"📚 Step 2: Retrieving memory for user {ctx.user_id}")

        try:
            memory_data = await self.memory_manager.retrieve_all(
                user_id=ctx.user_id,
                query=ctx.message,
                limit=10
            )

            ctx.memory = memory_data

            logger.debug(
                "Memory retrieved successfully",
                extra={
                    "user_id": ctx.user_id,
                    "episodic_count": len(memory_data.get("episodic", [])),
                    "biographical_count": len(memory_data.get("biographical", [])),
                    "session_turns": len(memory_data.get("session", {}).get("conversation_history", []))
                }
            )

        except Exception as e:
            logger.warning(
                f"Memory retrieval failed, continuing without memory: {e}",
                exc_info=True
            )
            ctx.memory = {
                "session": {},
                "episodic": [],
                "biographical": [],
                "analytical": []
            }

        return ctx

    # ============================================
    # Step 3: 응답 분석
    # ============================================

    async def _step_analyze_response(
        self,
        ctx: ProcessingContext
    ) -> ProcessingContext:
        """
        Step 3: 6개 지표 분석 (병렬)

        - LR (Lexical Richness): 어휘 풍부도
        - SD (Semantic Drift): 의미적 표류
        - NC (Narrative Coherence): 서사 일관성
        - TO (Temporal Orientation): 시간적 지남력
        - ER (Episodic Recall): 일화 기억
        - RT (Response Time): 반응 시간

        MCDI = 0.20·LR + 0.20·SD + 0.15·NC + 0.15·TO + 0.20·ER + 0.10·RT

        Args:
            ctx: 처리 컨텍스트

        Returns:
            분석 결과가 추가된 컨텍스트
        """
        logger.debug(f"🔬 Step 3: Analyzing response for user {ctx.user_id}")

        try:
            analysis_result = await self.analyzer.analyze(
                message=ctx.message,
                memory=ctx.memory,
                message_type=ctx.message_type,
                image_url=ctx.image_url
            )

            ctx.analysis = analysis_result
            ctx.mcdi_score = analysis_result["mcdi_score"]

            logger.debug(
                "Analysis completed",
                extra={
                    "user_id": ctx.user_id,
                    "mcdi_score": ctx.mcdi_score,
                    "scores": analysis_result.get("scores", {}),
                    "failed_metrics": analysis_result.get("failed_metrics", [])
                }
            )

        except Exception as e:
            logger.error(
                f"Analysis failed: {e}",
                exc_info=True
            )
            raise WorkflowError(f"Analysis step failed: {e}") from e

        return ctx

    # ============================================
    # Step 4: 위험도 평가
    # ============================================

    async def _step_evaluate_risk(
        self,
        ctx: ProcessingContext
    ) -> ProcessingContext:
        """
        Step 4: 위험도 평가

        - Baseline 계산 (첫 2주 평균/표준편차)
        - Z-score 계산: (current - baseline_mean) / baseline_std
        - 4주 기울기 계산 (선형 회귀)
        - GREEN/YELLOW/ORANGE/RED 판정
        - 교란 변수 체크 필요 여부 판단

        Args:
            ctx: 처리 컨텍스트

        Returns:
            위험도 정보가 추가된 컨텍스트
        """
        logger.debug(f"⚠️ Step 4: Evaluating risk for user {ctx.user_id}")

        try:
            risk_evaluation = await self.risk_evaluator.evaluate(
                user_id=ctx.user_id,
                current_score=ctx.mcdi_score,
                analysis=ctx.analysis
            )

            ctx.risk_level = risk_evaluation.risk_level
            ctx.alert_needed = risk_evaluation.alert_needed
            ctx.should_check_confounds = risk_evaluation.check_confounds

            logger.info(
                "Risk evaluation completed",
                extra={
                    "user_id": ctx.user_id,
                    "risk_level": ctx.risk_level,
                    "z_score": risk_evaluation.z_score,
                    "slope": risk_evaluation.slope,
                    "alert_needed": ctx.alert_needed,
                    "check_confounds": ctx.should_check_confounds
                }
            )

        except Exception as e:
            logger.error(
                f"Risk evaluation failed: {e}",
                exc_info=True
            )
            # 기본값 설정 (보수적으로 YELLOW)
            ctx.risk_level = "YELLOW"
            ctx.alert_needed = False
            ctx.should_check_confounds = False

        return ctx

    # ============================================
    # Step 5: 조건부 알림
    # ============================================

    async def _step_send_alert(
        self,
        ctx: ProcessingContext
    ) -> None:
        """
        Step 5: 보호자 알림 전송 (조건부)

        ORANGE 또는 RED 레벨일 때만 실행.

        Args:
            ctx: 처리 컨텍스트
        """
        logger.warning(
            f"🚨 Step 5: Sending alert for risk level {ctx.risk_level}",
            extra={
                "user_id": ctx.user_id,
                "risk_level": ctx.risk_level,
                "mcdi_score": ctx.mcdi_score
            }
        )

        try:
            await self.notification_service.send_guardian_alert(
                user_id=ctx.user_id,
                risk_level=ctx.risk_level,
                mcdi_score=ctx.mcdi_score,
                analysis=ctx.analysis
            )

            logger.info(
                "Alert sent successfully",
                extra={"user_id": ctx.user_id}
            )

        except Exception as e:
            logger.error(
                f"Alert sending failed: {e}",
                exc_info=True
            )
            # 알림 실패는 워크플로우 중단하지 않음

    # ============================================
    # Step 6: 교란 변수 처리
    # ============================================

    async def _step_handle_confounds(
        self,
        ctx: ProcessingContext
    ) -> ProcessingContext:
        """
        Step 6: 교란 변수 처리 (조건부)

        점수 하락 시 수면/우울/약물/질병/스트레스 확인 질문 스케줄.

        Args:
            ctx: 처리 컨텍스트

        Returns:
            교란 변수 질문이 추가된 컨텍스트
        """
        logger.info(
            f"🔍 Step 6: Scheduling confound check for user {ctx.user_id}",
            extra={"user_id": ctx.user_id}
        )

        try:
            confound_question = await self.dialogue_manager.generate_confound_question(
                user_id=ctx.user_id
            )

            ctx.confound_question_scheduled = confound_question

            logger.debug(
                "Confound question scheduled",
                extra={
                    "user_id": ctx.user_id,
                    "question": confound_question[:50] + "..."
                }
            )

        except Exception as e:
            logger.warning(
                f"Confound question generation failed: {e}",
                exc_info=True
            )
            # 실패 시 기본 질문
            ctx.confound_question_scheduled = "요즘 컨디션은 어떠세요? 😊"

        return ctx

    # ============================================
    # Step 7: 다음 상호작용 계획
    # ============================================

    async def _step_plan_next_interaction(
        self,
        ctx: ProcessingContext
    ) -> ProcessingContext:
        """
        Step 7: 다음 상호작용 계획

        - Weakest metric 찾기 (6개 중 최저 점수)
        - 카테고리 선택 (LR→lexical_richness, ER→episodic_recall 등)
        - 난이도 조정 (RED→easy, GREEN→hard)

        Args:
            ctx: 처리 컨텍스트

        Returns:
            다음 계획이 추가된 컨텍스트
        """
        logger.debug(f"📋 Step 7: Planning next interaction for user {ctx.user_id}")

        try:
            next_plan = await self.dialogue_manager.plan_next(
                user_id=ctx.user_id,
                current_analysis=ctx.analysis,
                risk_level=ctx.risk_level
            )

            ctx.next_category = next_plan["category"]
            ctx.next_difficulty = next_plan["difficulty"]

            logger.debug(
                "Next interaction planned",
                extra={
                    "user_id": ctx.user_id,
                    "category": ctx.next_category,
                    "difficulty": ctx.next_difficulty
                }
            )

        except Exception as e:
            logger.warning(
                f"Next interaction planning failed: {e}",
                exc_info=True
            )
            # 기본값
            ctx.next_category = "general"
            ctx.next_difficulty = "medium"

        return ctx

    # ============================================
    # Step 8: 응답 생성 및 메모리 저장
    # ============================================

    async def _step_generate_and_store(
        self,
        ctx: ProcessingContext
    ) -> ProcessingContext:
        """
        Step 8: 응답 생성 및 메모리 저장

        - 공감 반응 생성 (정원 메타포 사용)
        - 다음 질문 생성 (category + difficulty 기반)
        - 4계층 메모리 저장 (병렬)

        Args:
            ctx: 처리 컨텍스트

        Returns:
            응답이 추가된 컨텍스트
        """
        logger.debug(f"💬 Step 8: Generating response for user {ctx.user_id}")

        # 8-1. 응답 생성
        try:
            # 교란 변수 질문이 스케줄되어 있으면 그것을 다음 질문으로 사용
            if ctx.confound_question_scheduled:
                next_question = ctx.confound_question_scheduled
            else:
                # 아니면 계획된 카테고리/난이도로 질문 생성
                next_question = await self.dialogue_manager.generate_next_question(
                    user_id=ctx.user_id,
                    category=ctx.next_category,
                    difficulty=ctx.next_difficulty,
                    question_type="open_ended"
                )

            # 응답 생성 (공감 + 다음 질문)
            response = await self.dialogue_manager.generate_response(
                user_id=ctx.user_id,
                user_message=ctx.message,
                next_question=next_question
            )

            ctx.response = response

            logger.debug(
                "Response generated",
                extra={
                    "user_id": ctx.user_id,
                    "response_length": len(response)
                }
            )

        except Exception as e:
            logger.error(
                f"Response generation failed: {e}",
                exc_info=True
            )
            ctx.response = "잠시 생각을 정리하는 중이에요. 조금만 기다려주세요! 🌱"

        # 8-2. 메모리 저장 (4계층 병렬)
        try:
            await self.memory_manager.store_all(
                user_id=ctx.user_id,
                message=ctx.message,
                response=ctx.response,
                analysis=ctx.analysis
            )

            logger.debug(
                "Memory stored successfully",
                extra={"user_id": ctx.user_id}
            )

        except Exception as e:
            logger.warning(
                f"Memory storage failed: {e}",
                exc_info=True
            )
            # 저장 실패는 응답 반환에 영향 없음

        return ctx

    # ============================================
    # Fallback 응답 생성
    # ============================================

    async def _generate_fallback_response(
        self,
        ctx: ProcessingContext
    ) -> ProcessingContext:
        """
        에러 발생 시 Fallback 응답 생성

        Args:
            ctx: 처리 컨텍스트 (에러 정보 포함)

        Returns:
            Fallback 응답이 설정된 ProcessingContext
        """
        logger.warning(
            f"Generating fallback response for user {ctx.user_id}",
            extra={
                "user_id": ctx.user_id,
                "error": ctx.error
            }
        )

        # 단계별 부분 성공 여부에 따라 다른 응답
        if not ctx.response:
            if ctx.memory:
                # 메모리 검색까지는 성공
                ctx.response = "좋은 이야기네요! 😊 오늘은 여기까지 하고, 다음에 또 이야기 나눠요."
            else:
                # 완전 실패
                ctx.response = (
                    "앗, 잠시 정원을 가꾸는데 문제가 생겼어요 🌱\n"
                    "조금 후에 다시 이야기 나눠요!"
                )

        return ctx


# ============================================
# 7. Export
# ============================================
__all__ = [
    "SessionWorkflow",
]

logger.info("Session workflow module loaded")
