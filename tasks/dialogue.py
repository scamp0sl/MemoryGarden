"""
대화 처리 비동기 태스크

대화 후 백그라운드 처리 및 배치 분석 태스크를 관리합니다.
FastAPI BackgroundTasks와 Redis를 활용하여 비동기 작업을 처리합니다.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

# ============================================
# 2. Third-Party Imports
# ============================================
from fastapi import BackgroundTasks

# ============================================
# 3. Local Imports
# ============================================
from database.redis_client import redis_client
from database.postgres import AsyncSessionLocal
from utils.logger import get_logger
from utils.exceptions import MemoryGardenError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)


# ============================================
# 5. 상수 정의
# ============================================

# Redis 큐 키
TASK_QUEUE_KEY = "tasks:dialogue:queue"
TASK_STATUS_KEY_PREFIX = "tasks:dialogue:status:"
TASK_RESULT_KEY_PREFIX = "tasks:dialogue:result:"

# 태스크 타입
TASK_TYPE_MEMORY_EXTRACTION = "memory_extraction"
TASK_TYPE_ANALYSIS_UPDATE = "analysis_update"
TASK_TYPE_GARDEN_UPDATE = "garden_update"
TASK_TYPE_WEEKLY_REPORT = "weekly_report"
TASK_TYPE_MONTHLY_REPORT = "monthly_report"
TASK_TYPE_SESSION_CLEANUP = "session_cleanup"

# 태스크 상태
TASK_STATUS_PENDING = "pending"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

# 타임아웃
TASK_TIMEOUT_SECONDS = 300  # 5분


# ============================================
# 6. 예외 클래스
# ============================================

class TaskError(MemoryGardenError):
    """태스크 실행 에러"""
    pass


# ============================================
# 7. 태스크 관리 클래스
# ============================================

class DialogueTaskManager:
    """대화 처리 태스크 매니저

    대화 후 비동기 처리 및 배치 분석 태스크를 관리합니다.
    FastAPI BackgroundTasks와 Redis 큐를 활용합니다.

    Attributes:
        redis_client: Redis 클라이언트
    """

    def __init__(self):
        """초기화"""
        self.redis = redis_client
        logger.info("DialogueTaskManager initialized")

    async def enqueue_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        태스크 큐에 추가

        Args:
            task_type: 태스크 타입
            task_data: 태스크 데이터
            priority: 우선순위 (0: 낮음, 1: 보통, 2: 높음)

        Returns:
            태스크 ID

        Raises:
            TaskError: 큐 추가 실패
        """
        try:
            # 태스크 ID 생성
            task_id = f"{task_type}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

            # 태스크 데이터 구성
            task = {
                "task_id": task_id,
                "task_type": task_type,
                "task_data": task_data,
                "priority": priority,
                "created_at": datetime.now().isoformat(),
                "status": TASK_STATUS_PENDING
            }

            # Redis 큐에 추가
            await self.redis.lpush(TASK_QUEUE_KEY, json.dumps(task))

            # 태스크 상태 저장
            status_key = f"{TASK_STATUS_KEY_PREFIX}{task_id}"
            await self.redis.setex(
                status_key,
                TASK_TIMEOUT_SECONDS,
                TASK_STATUS_PENDING
            )

            logger.info(
                f"Task enqueued: {task_id}",
                extra={"task_type": task_type, "priority": priority}
            )

            return task_id

        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}", exc_info=True)
            raise TaskError(f"Task enqueue failed: {e}") from e

    async def get_task_status(self, task_id: str) -> Optional[str]:
        """
        태스크 상태 조회

        Args:
            task_id: 태스크 ID

        Returns:
            태스크 상태 (pending/processing/completed/failed/None)
        """
        try:
            status_key = f"{TASK_STATUS_KEY_PREFIX}{task_id}"
            status = await self.redis.get(status_key)

            if status:
                return status.decode('utf-8') if isinstance(status, bytes) else status

            return None

        except Exception as e:
            logger.error(f"Failed to get task status: {e}", exc_info=True)
            return None

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        태스크 상태 업데이트

        Args:
            task_id: 태스크 ID
            status: 새로운 상태
            result: 실행 결과 (선택)
        """
        try:
            # 상태 업데이트
            status_key = f"{TASK_STATUS_KEY_PREFIX}{task_id}"
            await self.redis.setex(
                status_key,
                TASK_TIMEOUT_SECONDS,
                status
            )

            # 결과 저장
            if result:
                result_key = f"{TASK_RESULT_KEY_PREFIX}{task_id}"
                await self.redis.setex(
                    result_key,
                    TASK_TIMEOUT_SECONDS,
                    json.dumps(result)
                )

            logger.debug(f"Task status updated: {task_id} -> {status}")

        except Exception as e:
            logger.error(f"Failed to update task status: {e}", exc_info=True)


# ============================================
# 8. 대화 후 처리 태스크
# ============================================

async def extract_and_store_memories(
    user_id: str,
    session_id: str,
    message: str,
    response: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    대화에서 기억 추출 및 저장

    사실(fact) 추출 후 4계층 메모리에 저장:
    - Session Memory (Redis)
    - Episodic Memory (Qdrant)
    - Biographical Memory (Qdrant + PostgreSQL)
    - Analytical Memory (TimescaleDB)

    Args:
        user_id: 사용자 ID
        session_id: 세션 ID
        message: 사용자 메시지
        response: AI 응답
        context: 컨텍스트 정보

    Returns:
        {
            "extracted_facts": 추출된 사실 개수,
            "stored_memories": 저장된 메모리 개수,
            "processing_time_ms": 처리 시간
        }

    Example:
        >>> result = await extract_and_store_memories(
        ...     user_id="user123",
        ...     session_id="session456",
        ...     message="오늘 점심에 김치찌개를 먹었어요",
        ...     response="김치찌개 맛있게 드셨군요!",
        ...     context={}
        ... )
        >>> print(result["extracted_facts"])
        3
    """
    start_time = datetime.now()

    try:
        logger.info(
            f"Extracting and storing memories",
            extra={"user_id": user_id, "session_id": session_id}
        )

        # TODO: MemoryManager 통합
        # from core.memory.memory_manager import MemoryManager
        # memory_manager = MemoryManager()

        # 1. 사실 추출 (LLM 사용)
        # facts = await memory_manager.extract_facts(message, response, context)

        # 2. 4계층 메모리 저장
        # await memory_manager.store_all(user_id, message, response, facts, context)

        # Mock implementation
        extracted_facts = 3
        stored_memories = 3

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        result = {
            "extracted_facts": extracted_facts,
            "stored_memories": stored_memories,
            "processing_time_ms": processing_time
        }

        logger.info(
            f"Memory extraction completed",
            extra={
                "user_id": user_id,
                "extracted_facts": extracted_facts,
                "processing_time_ms": processing_time
            }
        )

        return result

    except Exception as e:
        logger.error(
            f"Memory extraction failed: {e}",
            extra={"user_id": user_id, "session_id": session_id},
            exc_info=True
        )
        raise TaskError(f"Memory extraction failed: {e}") from e


async def update_analysis_data(
    user_id: str,
    session_id: str,
    analysis_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    분석 데이터 업데이트

    MCDI 점수, 개별 지표, 위험도를 TimescaleDB에 저장하고
    통계 데이터를 업데이트합니다.

    Args:
        user_id: 사용자 ID
        session_id: 세션 ID
        analysis_result: 분석 결과

    Returns:
        {
            "updated": True/False,
            "mcdi_score": MCDI 점수,
            "risk_level": 위험도
        }
    """
    try:
        logger.info(
            f"Updating analysis data",
            extra={"user_id": user_id, "mcdi_score": analysis_result.get("mcdi_score")}
        )

        # TODO: 분석 데이터 저장 구현
        # async with AsyncSessionLocal() as db:
        #     # MCDI 점수 저장
        #     # 개별 지표 저장
        #     # 위험도 저장
        #     await db.commit()

        result = {
            "updated": True,
            "mcdi_score": analysis_result.get("mcdi_score"),
            "risk_level": analysis_result.get("risk_level", "GREEN")
        }

        logger.info(
            f"Analysis data updated",
            extra={"user_id": user_id, "mcdi_score": result["mcdi_score"]}
        )

        return result

    except Exception as e:
        logger.error(f"Analysis update failed: {e}", exc_info=True)
        raise TaskError(f"Analysis update failed: {e}") from e


async def update_garden_status(
    user_id: str,
    session_id: str,
    conversation_count: int
) -> Dict[str, Any]:
    """
    정원 상태 업데이트

    게이미피케이션 로직:
    - 1대화 = 1꽃
    - 3일 연속 = 1나비
    - 7일 연속 = 레벨업
    - 30일 = 계절 뱃지

    Args:
        user_id: 사용자 ID
        session_id: 세션 ID
        conversation_count: 총 대화 수

    Returns:
        {
            "flowers_added": 추가된 꽃 수,
            "butterflies_added": 추가된 나비 수,
            "level_up": 레벨업 여부,
            "badges_earned": 획득한 뱃지
        }
    """
    try:
        logger.info(
            f"Updating garden status",
            extra={"user_id": user_id, "conversation_count": conversation_count}
        )

        # TODO: GardenManager 통합
        # from core.garden.garden_manager import GardenManager
        # garden_manager = GardenManager()

        # 1. 꽃 추가 (1대화 = 1꽃)
        flowers_added = 1

        # 2. 연속 일수 체크
        # consecutive_days = await garden_manager.get_consecutive_days(user_id)
        consecutive_days = 5  # Mock

        # 3. 나비 추가 (3일 연속)
        butterflies_added = 1 if consecutive_days % 3 == 0 else 0

        # 4. 레벨업 (7일 연속)
        level_up = consecutive_days % 7 == 0

        # 5. 계절 뱃지 (30일)
        badges_earned = []
        if consecutive_days % 30 == 0:
            season = datetime.now().strftime("%B_%Y").lower()
            badges_earned.append(season)

        result = {
            "flowers_added": flowers_added,
            "butterflies_added": butterflies_added,
            "level_up": level_up,
            "badges_earned": badges_earned
        }

        logger.info(
            f"Garden status updated",
            extra={
                "user_id": user_id,
                "flowers_added": flowers_added,
                "level_up": level_up
            }
        )

        return result

    except Exception as e:
        logger.error(f"Garden update failed: {e}", exc_info=True)
        raise TaskError(f"Garden update failed: {e}") from e


async def process_post_conversation_tasks(
    user_id: str,
    session_id: str,
    message: str,
    response: str,
    analysis_result: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    대화 후 모든 비동기 태스크 실행

    3개 태스크를 병렬로 실행:
    1. 기억 추출 및 저장
    2. 분석 데이터 업데이트
    3. 정원 상태 업데이트

    Args:
        user_id: 사용자 ID
        session_id: 세션 ID
        message: 사용자 메시지
        response: AI 응답
        analysis_result: 분석 결과
        context: 컨텍스트

    Returns:
        {
            "memory_result": {...},
            "analysis_result": {...},
            "garden_result": {...},
            "total_processing_time_ms": 처리 시간
        }
    """
    start_time = datetime.now()

    try:
        logger.info(
            f"Starting post-conversation tasks",
            extra={"user_id": user_id, "session_id": session_id}
        )

        # 3개 태스크 병렬 실행
        memory_task = extract_and_store_memories(
            user_id, session_id, message, response, context
        )

        analysis_task = update_analysis_data(
            user_id, session_id, analysis_result
        )

        garden_task = update_garden_status(
            user_id, session_id, context.get("conversation_count", 0)
        )

        # 모든 태스크 완료 대기
        memory_result, analysis_result_updated, garden_result = await asyncio.gather(
            memory_task,
            analysis_task,
            garden_task,
            return_exceptions=True
        )

        # 에러 처리
        for i, result in enumerate([memory_result, analysis_result_updated, garden_result]):
            if isinstance(result, Exception):
                task_name = ["memory", "analysis", "garden"][i]
                logger.error(f"{task_name} task failed: {result}")

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        final_result = {
            "memory_result": memory_result if not isinstance(memory_result, Exception) else {"error": str(memory_result)},
            "analysis_result": analysis_result_updated if not isinstance(analysis_result_updated, Exception) else {"error": str(analysis_result_updated)},
            "garden_result": garden_result if not isinstance(garden_result, Exception) else {"error": str(garden_result)},
            "total_processing_time_ms": processing_time
        }

        logger.info(
            f"Post-conversation tasks completed",
            extra={
                "user_id": user_id,
                "total_processing_time_ms": processing_time
            }
        )

        return final_result

    except Exception as e:
        logger.error(
            f"Post-conversation tasks failed: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise TaskError(f"Post-conversation tasks failed: {e}") from e


# ============================================
# 9. 배치 분석 태스크
# ============================================

async def generate_weekly_report(user_id: str) -> Dict[str, Any]:
    """
    주간 리포트 생성

    최근 7일간의 데이터를 분석하여 리포트 생성:
    - MCDI 점수 추이
    - 위험도 변화
    - 대화 참여율
    - 정원 성장 통계

    Args:
        user_id: 사용자 ID

    Returns:
        {
            "report_id": 리포트 ID,
            "period": "2025-02-03 ~ 2025-02-10",
            "mcdi_trend": {...},
            "risk_summary": {...},
            "engagement": {...},
            "garden_growth": {...}
        }
    """
    try:
        logger.info(f"Generating weekly report for user: {user_id}")

        # TODO: 리포트 생성 로직 구현
        # 1. 최근 7일 데이터 조회
        # 2. MCDI 추이 분석
        # 3. 위험도 변화 추적
        # 4. 참여율 계산
        # 5. 정원 성장 통계

        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        report = {
            "report_id": f"weekly_{user_id}_{end_date.strftime('%Y%m%d')}",
            "user_id": user_id,
            "report_type": "weekly",
            "period": f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
            "mcdi_trend": {
                "average": 75.5,
                "min": 70.0,
                "max": 82.0,
                "trend": "stable"
            },
            "risk_summary": {
                "current_level": "GREEN",
                "changes": 0
            },
            "engagement": {
                "total_conversations": 14,
                "consecutive_days": 7,
                "participation_rate": 1.0
            },
            "garden_growth": {
                "flowers_added": 14,
                "butterflies_added": 2,
                "level_ups": 1
            },
            "generated_at": datetime.now().isoformat()
        }

        # TODO: DB에 저장

        logger.info(f"Weekly report generated for user: {user_id}")

        return report

    except Exception as e:
        logger.error(f"Weekly report generation failed: {e}", exc_info=True)
        raise TaskError(f"Weekly report generation failed: {e}") from e


async def generate_monthly_report(user_id: str) -> Dict[str, Any]:
    """
    월간 리포트 생성

    최근 30일간의 데이터를 분석하여 상세 리포트 생성:
    - 종합 MCDI 분석
    - 위험도 추이
    - 개별 지표 상세 분석
    - 정원 성장 마일스톤
    - 보호자 알림 요약

    Args:
        user_id: 사용자 ID

    Returns:
        월간 리포트 딕셔너리
    """
    try:
        logger.info(f"Generating monthly report for user: {user_id}")

        # TODO: 월간 리포트 생성 로직

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        report = {
            "report_id": f"monthly_{user_id}_{end_date.strftime('%Y%m')}",
            "user_id": user_id,
            "report_type": "monthly",
            "period": f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
            "mcdi_analysis": {
                "average": 76.2,
                "trend": "improving",
                "detailed_scores": {
                    "LR": 78.5,
                    "SD": 80.0,
                    "NC": 75.0,
                    "TO": 77.0,
                    "ER": 72.0,
                    "RT": 74.5
                }
            },
            "risk_history": {
                "GREEN": 28,
                "YELLOW": 2,
                "ORANGE": 0,
                "RED": 0
            },
            "engagement_summary": {
                "total_conversations": 60,
                "consecutive_days_max": 30,
                "participation_rate": 1.0
            },
            "garden_milestones": {
                "total_flowers": 60,
                "total_butterflies": 10,
                "current_level": 4,
                "badges_earned": ["february_2025"]
            },
            "alerts_summary": {
                "total_alerts": 2,
                "resolved": 2
            },
            "generated_at": datetime.now().isoformat()
        }

        logger.info(f"Monthly report generated for user: {user_id}")

        return report

    except Exception as e:
        logger.error(f"Monthly report generation failed: {e}", exc_info=True)
        raise TaskError(f"Monthly report generation failed: {e}") from e


async def cleanup_old_sessions(days_to_keep: int = 90) -> Dict[str, Any]:
    """
    오래된 세션 정리

    N일 이전의 완료된 세션을 정리합니다.
    - Session Memory (Redis): 삭제
    - Session 레코드 (PostgreSQL): 상태를 'archived'로 변경

    Args:
        days_to_keep: 보관 기간 (일)

    Returns:
        {
            "sessions_archived": 아카이브된 세션 수,
            "redis_keys_deleted": 삭제된 Redis 키 수
        }
    """
    try:
        logger.info(f"Cleaning up sessions older than {days_to_keep} days")

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # TODO: 세션 정리 로직 구현
        # 1. cutoff_date 이전의 완료된 세션 조회
        # 2. Redis에서 세션 데이터 삭제
        # 3. PostgreSQL 세션 상태를 'archived'로 변경

        sessions_archived = 0
        redis_keys_deleted = 0

        result = {
            "sessions_archived": sessions_archived,
            "redis_keys_deleted": redis_keys_deleted,
            "cutoff_date": cutoff_date.isoformat()
        }

        logger.info(
            f"Session cleanup completed",
            extra={
                "sessions_archived": sessions_archived,
                "cutoff_date": cutoff_date.isoformat()
            }
        )

        return result

    except Exception as e:
        logger.error(f"Session cleanup failed: {e}", exc_info=True)
        raise TaskError(f"Session cleanup failed: {e}") from e


# ============================================
# 10. 태스크 워커 (선택적 사용)
# ============================================

async def process_task_queue():
    """
    Redis 큐에서 태스크를 가져와 실행하는 워커

    별도 프로세스로 실행하여 백그라운드에서 태스크를 처리합니다.

    Usage:
        # 별도 터미널에서 실행
        python -c "import asyncio; from tasks.dialogue import process_task_queue; asyncio.run(process_task_queue())"
    """
    logger.info("Task queue worker started")

    task_manager = DialogueTaskManager()

    while True:
        try:
            # Redis 큐에서 태스크 가져오기 (블로킹, 5초 타임아웃)
            task_data = await redis_client.brpop(TASK_QUEUE_KEY, timeout=5)

            if not task_data:
                # 큐가 비어있으면 계속 대기
                continue

            # 태스크 파싱
            _, task_json = task_data
            task = json.loads(task_json)

            task_id = task["task_id"]
            task_type = task["task_type"]
            task_payload = task["task_data"]

            logger.info(f"Processing task: {task_id} ({task_type})")

            # 태스크 상태를 processing으로 변경
            await task_manager.update_task_status(task_id, TASK_STATUS_PROCESSING)

            # 태스크 타입별 실행
            result = None

            if task_type == TASK_TYPE_MEMORY_EXTRACTION:
                result = await extract_and_store_memories(**task_payload)

            elif task_type == TASK_TYPE_ANALYSIS_UPDATE:
                result = await update_analysis_data(**task_payload)

            elif task_type == TASK_TYPE_GARDEN_UPDATE:
                result = await update_garden_status(**task_payload)

            elif task_type == TASK_TYPE_WEEKLY_REPORT:
                result = await generate_weekly_report(**task_payload)

            elif task_type == TASK_TYPE_MONTHLY_REPORT:
                result = await generate_monthly_report(**task_payload)

            elif task_type == TASK_TYPE_SESSION_CLEANUP:
                result = await cleanup_old_sessions(**task_payload)

            else:
                logger.warning(f"Unknown task type: {task_type}")
                await task_manager.update_task_status(task_id, TASK_STATUS_FAILED)
                continue

            # 태스크 완료
            await task_manager.update_task_status(
                task_id,
                TASK_STATUS_COMPLETED,
                result
            )

            logger.info(f"Task completed: {task_id}")

        except Exception as e:
            logger.error(f"Task processing error: {e}", exc_info=True)

            # 태스크 실패 기록
            if task_id:
                await task_manager.update_task_status(task_id, TASK_STATUS_FAILED)

            # 에러 발생 시 잠시 대기
            await asyncio.sleep(5)


# ============================================
# 11. FastAPI BackgroundTasks 헬퍼
# ============================================

def add_post_conversation_tasks_to_background(
    background_tasks: BackgroundTasks,
    user_id: str,
    session_id: str,
    message: str,
    response: str,
    analysis_result: Dict[str, Any],
    context: Dict[str, Any]
) -> None:
    """
    FastAPI BackgroundTasks에 대화 후 처리 태스크 추가

    API 라우터에서 사용:

    @router.post("/sessions/{session_id}/messages")
    async def send_message(
        session_id: str,
        message_request: MessageRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db)
    ):
        # 대화 처리
        response = await process_conversation(...)

        # 백그라운드 태스크 추가
        add_post_conversation_tasks_to_background(
            background_tasks,
            user_id, session_id, message, response,
            analysis_result, context
        )

        return response

    Args:
        background_tasks: FastAPI BackgroundTasks 인스턴스
        user_id: 사용자 ID
        session_id: 세션 ID
        message: 사용자 메시지
        response: AI 응답
        analysis_result: 분석 결과
        context: 컨텍스트
    """
    background_tasks.add_task(
        process_post_conversation_tasks,
        user_id=user_id,
        session_id=session_id,
        message=message,
        response=response,
        analysis_result=analysis_result,
        context=context
    )

    logger.debug(
        f"Background tasks added for session: {session_id}",
        extra={"user_id": user_id}
    )


# ============================================
# 12. 스케줄 대화 전송
# ============================================

async def send_scheduled_dialogue(user_id: str) -> Dict[str, Any]:
    """
    스케줄된 자동 대화 시작

    채널 챗봇 사용자와 OAuth 사용자 모두 지원.
    우선순위: 채널 나에게 보내기(OAuth) → 채널 친구톡(channel_user_key)

    Args:
        user_id: 사용자 UUID (DB primary key)

    Returns:
        {
            "success": True/False,
            "method": "send_to_me" | "channel" | "none",
            "message_sent": 전송된 메시지,
            "sent_at": 실제 전송 시간
        }
    """
    try:
        logger.info(f"📨 Sending scheduled dialogue to {user_id}")

        from database.postgres import AsyncSessionLocal
        from database.models import User
        from sqlalchemy import select
        import uuid as uuid_module

        async with AsyncSessionLocal() as db:
            # UUID 또는 kakao_id로 사용자 조회
            try:
                uuid_obj = uuid_module.UUID(str(user_id))
                result_query = await db.execute(select(User).where(User.id == uuid_obj))
            except (ValueError, AttributeError):
                result_query = await db.execute(select(User).where(User.kakao_id == user_id))

            user = result_query.scalar_one_or_none()

            if not user:
                logger.error(f"User not found: {user_id}")
                return {"success": False, "error": "User not found", "method": "none"}

            # ── 맞춤형 메시지 생성 ───────────────────────
            message = await _build_scheduled_message(str(user.id))

            # ── 전송 방법 결정 ───────────────────────────
            # 방법 1: OAuth 토큰 (나에게 보내기)
            if user.kakao_access_token:
                result = await _send_via_oauth(user, message)
                if result["success"]:
                    return result

            # 방법 2: 채널 챗봇 사용자 (친구톡 준비)
            if user.kakao_channel_user_key:
                result = await _send_via_channel(user, message)
                return result

            # 둘 다 없음
            logger.warning(f"No sending method available for {user_id}")
            return {
                "success": False,
                "error": "No available sending method (need OAuth token or channel user key)",
                "method": "none",
                "user_id": str(user.id)
            }

    except Exception as e:
        logger.error(f"❌ Scheduled dialogue failed for {user_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "method": "none",
            "sent_at": datetime.now().isoformat()
        }


async def _build_scheduled_message(user_id: str) -> str:
    """맞춤형 스케줄 메시지 생성

    send_to_me로 전송되므로 채널 채팅방으로 유도하는 안내 포함.
    """
    try:
        from core.dialogue.dialogue_manager import DialogueManager
        dialogue_manager = DialogueManager()

        # 다음 대화 계획 생성
        ai_response = await dialogue_manager.generate_response(
            user_id=user_id,
            user_message="[SCHEDULER_INIT]"
        )

        greeting = _get_time_based_greeting()
        return (
            f"{greeting}\n\n"
            f"{ai_response}\n\n"
            f"아래 버튼을 눌러 채널에서 답해주세요 😊"
        )

    except Exception as e:
        logger.warning(f"Custom message generation failed, using default: {e}")
        greeting = _get_time_based_greeting()
        return (
            f"{greeting}\n\n"
            f"오늘의 정원은 어떤가요? 잠깐 이야기 나눠볼까요? 🌱\n\n"
            f"아래 버튼을 눌러 채널에서 답해주세요 😊"
        )


async def _send_via_oauth(user, message: str) -> Dict[str, Any]:
    """OAuth 토큰으로 '나에게 보내기' 전송"""
    import httpx
    from services.kakao_client import KakaoClient
    from sqlalchemy import select
    from database.models import User as UserModel

    # 전송에 사용할 실제 토큰 (갱신 후 변경될 수 있음)
    access_token = user.kakao_access_token

    # 토큰 만료 체크 (1시간 전 갱신)
    if user.kakao_token_expires_at:
        time_until_expiry = user.kakao_token_expires_at - datetime.now()
        if time_until_expiry < timedelta(hours=1):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"http://localhost:8002/api/v1/auth/kakao/refresh/{user.kakao_id}"
                    )
                    resp.raise_for_status()
                logger.info(f"Token refreshed for {user.kakao_id}")

                # 갱신된 토큰을 DB에서 다시 읽어 사용
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(UserModel).where(UserModel.id == user.id)
                    )
                    refreshed_user = result.scalar_one_or_none()
                    if refreshed_user and refreshed_user.kakao_access_token:
                        access_token = refreshed_user.kakao_access_token
                        logger.info(f"Using refreshed token for {user.kakao_id}")

            except Exception as e:
                logger.warning(f"Token refresh failed (using current token): {e}")

    try:
        kakao_client = KakaoClient()
        kakao_result = await kakao_client.send_to_me(
            access_token=access_token,
            message=message
        )

        logger.info(f"✅ [send_to_me] Message sent to {user.kakao_id}")
        return {
            "success": True,
            "method": "send_to_me",
            "user_id": str(user.id),
            "message_sent": message[:100],
            "sent_at": datetime.now().isoformat(),
            "kakao_result": kakao_result
        }

    except Exception as e:
        logger.error(f"send_to_me failed for {user.kakao_id}: {e}")
        return {"success": False, "method": "send_to_me", "error": str(e)}


async def _send_via_channel(user, message: str) -> Dict[str, Any]:
    """비즈메시지 친구톡으로 채널 구독자에게 메시지 전송

    카카오 i 커넥트 메시지 API 사용.
    KAKAO_BIZ_CLIENT_ID, KAKAO_BIZ_CLIENT_SECRET, KAKAO_SENDER_KEY 설정 필요.

    자격증명 미설정 시 channel_pending 상태로 반환 (메시지 미전송).
    """
    from services.kakao_client import KakaoClient

    channel_key = user.kakao_channel_user_key
    kakao_client = KakaoClient()

    try:
        result = await kakao_client.send_channel_message(
            channel_user_key=channel_key,
            message=message
        )

        method = result.get("method", "unknown")

        if method == "channel_pending":
            logger.warning(
                f"⏳ [channel] 비즈메시지 미설정 → 메시지 미전송",
                extra={
                    "user_id": str(user.id),
                    "channel_key": channel_key[:10] + "...",
                    "action": result.get("action_required")
                }
            )
            return {
                "success": False,
                "method": "channel_pending",
                "user_id": str(user.id),
                "channel_user_key": channel_key,
                "message_prepared": message[:100],
                "reason": result.get("reason"),
                "sent_at": datetime.now().isoformat()
            }

        logger.info(
            f"✅ [channel] 비즈메시지 친구톡 전송 완료",
            extra={
                "user_id": str(user.id),
                "channel_key": channel_key[:10] + "...",
                "method": method
            }
        )
        return {
            "success": True,
            "method": method,
            "user_id": str(user.id),
            "channel_user_key": channel_key,
            "message_sent": message[:100],
            "sent_at": datetime.now().isoformat(),
            "kakao_result": result
        }

    except Exception as e:
        logger.error(
            f"❌ [channel] 비즈메시지 친구톡 전송 실패: {e}",
            extra={"user_id": str(user.id), "channel_key": channel_key[:10] + "..."}
        )
        return {
            "success": False,
            "method": "channel_error",
            "user_id": str(user.id),
            "error": str(e),
            "sent_at": datetime.now().isoformat()
        }


def _get_time_based_greeting() -> str:
    """
    시간대별 인사말 반환

    Returns:
        시간대에 맞는 인사말

    Example:
        >>> greeting = _get_time_based_greeting()
        >>> print(greeting)
        "좋은 아침이에요! ☀️"
    """
    current_hour = datetime.now().hour

    if 5 <= current_hour < 12:
        return "좋은 아침이에요! ☀️"
    elif 12 <= current_hour < 17:
        return "안녕하세요! 🌤️"
    elif 17 <= current_hour < 21:
        return "좋은 저녁이에요! 🌙"
    else:
        return "편안한 밤 되세요! ✨"


# ============================================
# 저녁 회상 퀴즈 스케줄링
# ============================================

async def pre_generate_evening_quizzes():
    """저녁 회상 퀴즈 사전 생성 스케줄 태스크

    17:50에 실행되어 모든 활성 사용자의 퀴즈를 미리 생성.
    18~24시 사이에 사용자가 메시지를 보내면 캐시된 퀴즈가 즉시 전송됨.

    Returns:
        생성된 퀴즈 수
    """
    try:
        from zoneinfo import ZoneInfo
        from sqlalchemy import select
        from database.models import User
        from api.routes.kakao_webhook import _pre_generate_evening_quiz

        logger.info("🌙 Pre-generating evening quizzes for all active users")

        # 최근 7일간 활성 사용자 조회
        seven_days_ago = datetime.now() - timedelta(days=7)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(
                    User.last_interaction_at >= seven_days_ago,
                    User.onboarding_day >= 15  # 베이스라인 완성된 사용자만
                )
            )
            active_users = result.scalars().all()

        generated_count = 0
        failed_count = 0

        for user in active_users:
            try:
                await _pre_generate_evening_quiz(str(user.id))
                generated_count += 1
            except Exception as e:
                logger.warning(f"Quiz generation failed for {user.id}: {e}")
                failed_count += 1

        logger.info(
            f"✅ Evening quiz pre-generation complete: {generated_count} generated, {failed_count} failed",
            extra={"generated": generated_count, "failed": failed_count}
        )

        return {
            "generated": generated_count,
            "failed": failed_count,
            "total": len(active_users)
        }

    except Exception as e:
        logger.error(f"Evening quiz pre-generation failed: {e}", exc_info=True)
        return {"generated": 0, "failed": 0, "error": str(e)}


# ============================================
# C5: Proactive Messaging
# ============================================

async def send_proactive_messages():
    """Proactive 메시지 스케줄 태스크 (C5)

    36시간 이상 비활성 사용자에게 자동 메시지 발송
    """
    from services.proactive_service import ProactiveService

    service = ProactiveService()
    result = await service.send_batch_proactive_messages(limit=10)
    logger.info(f"Proactive messages sent: {result}")
    return result
