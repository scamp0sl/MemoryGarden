"""
API 의존성 주입 (Dependency Injection)

FastAPI Depends를 통해 주입되는 공통 의존성들을 정의합니다.

Author: Memory Garden Team
Created: 2025-02-12
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Optional
from functools import lru_cache

# ============================================
# 2. Third-Party Imports
# ============================================
from fastapi import Depends

# ============================================
# 3. Local Imports
# ============================================
from core.workflow.session_workflow import SessionWorkflow
from core.memory.memory_manager import MemoryManager
from core.analysis.analyzer import Analyzer
from core.analysis.risk_evaluator import RiskEvaluator
from core.dialogue.dialogue_manager import DialogueManager
from services.notification_service import NotificationService
from services.llm_service import LLMService
from core.nlp.embedder import Embedder
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)


# ============================================
# 5. 싱글톤 의존성 (애플리케이션 생명주기 동안 1개만 생성)
# ============================================

_session_workflow: Optional[SessionWorkflow] = None


def get_session_workflow() -> SessionWorkflow:
    """
    SessionWorkflow 싱글톤 인스턴스 반환

    애플리케이션 시작 시 한 번만 초기화되고, 이후 요청에서는
    동일한 인스턴스를 재사용합니다.

    Returns:
        SessionWorkflow 인스턴스

    Example:
        >>> from fastapi import Depends
        >>> @router.post("/messages")
        >>> async def send_message(
        ...     workflow: SessionWorkflow = Depends(get_session_workflow)
        ... ):
        ...     response = await workflow.process_message(...)
    """
    global _session_workflow

    if _session_workflow is None:
        logger.info("🏗️ Initializing SessionWorkflow singleton...")

        try:
            # ============================================
            # Step 1: LLM 서비스 초기화
            # ============================================
            llm_service = LLMService()
            logger.debug("✅ LLMService initialized")

            # ============================================
            # Step 2: Embedder 초기화
            # ============================================
            embedder = Embedder()
            logger.debug("✅ Embedder initialized")

            # ============================================
            # Step 3: MemoryManager 초기화
            # ============================================
            memory_manager = MemoryManager()
            logger.debug("✅ MemoryManager initialized")

            # ============================================
            # Step 4: Analyzer 초기화 (6개 지표)
            # ============================================
            analyzer = Analyzer(
                llm_service=llm_service,
                embedder=embedder
            )
            logger.debug("✅ Analyzer initialized (6 metrics)")

            # ============================================
            # Step 5: RiskEvaluator 초기화
            # ============================================
            risk_evaluator = RiskEvaluator()
            logger.debug("✅ RiskEvaluator initialized")

            # ============================================
            # Step 6: DialogueManager 초기화
            # ============================================
            # DialogueManager는 내부적으로 ResponseGenerator와 PromptBuilder를 생성
            dialogue_manager = DialogueManager()
            logger.debug("✅ DialogueManager initialized")

            # ============================================
            # Step 7: NotificationService 초기화
            # ============================================
            notification_service = NotificationService()
            logger.debug("✅ NotificationService initialized")

            # ============================================
            # Step 8: SessionWorkflow 초기화
            # ============================================
            _session_workflow = SessionWorkflow(
                memory_manager=memory_manager,
                analyzer=analyzer,
                risk_evaluator=risk_evaluator,
                dialogue_manager=dialogue_manager,
                notification_service=notification_service
            )

            logger.info(
                "✅ SessionWorkflow singleton initialized successfully",
                extra={"components": 7}
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to initialize SessionWorkflow: {e}",
                exc_info=True
            )
            raise RuntimeError(f"SessionWorkflow initialization failed: {e}") from e

    return _session_workflow


# ============================================
# 6. 기타 의존성
# ============================================

async def get_current_user(token: str = None):
    """
    현재 사용자 인증 (향후 구현)

    Args:
        token: JWT 토큰 또는 API 키

    Returns:
        User 객체

    Note:
        현재는 인증 없이 모든 요청 허용
        향후 JWT 또는 OAuth 인증 추가 예정
    """
    # TODO: JWT 토큰 검증
    # TODO: 사용자 정보 조회
    return None
