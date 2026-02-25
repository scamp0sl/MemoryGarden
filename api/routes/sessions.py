"""
세션 관리 API 라우터

대화 세션 생성, 조회, 종료.

Author: Memory Garden Team
Created: 2025-02-10
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    SessionCreate,
    SessionResponse,
    SessionStatusResponse,
    SessionListResponse,
)
from database.postgres import get_db
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


# ============================================
# Session Management
# ============================================

@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    신규 세션 생성
    
    - **user_id**: 사용자 UUID (필수)
    
    Returns:
        SessionResponse with session_id and status="active"
    
    Notes:
        - Redis에 세션 상태 저장
        - PostgreSQL에 세션 메타데이터 저장
        - 기존 active 세션이 있으면 자동 종료 후 새 세션 생성
    """
    try:
        logger.info(f"Creating session for user: user_id={session_data.user_id}")
        
        # TODO: SessionService 구현 후 주입
        # session_service = SessionService(db, redis_client)
        # session = await session_service.create_session(session_data.user_id)
        
        # 임시 구현
        from datetime import datetime
        session_response = SessionResponse(
            session_id="temp-session-id",
            user_id=session_data.user_id,
            status="active",
            started_at=datetime.now(),
            completed_at=None,
            conversation_count=0,
            last_activity_at=datetime.now()
        )
        
        logger.info(f"Session created: session_id={session_response.session_id}")
        return session_response
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/schedules")
async def list_all_schedules():
    """
    모든 사용자 스케줄 목록 조회 (관리자용)

    Returns:
        스케줄 목록
    """
    try:
        logger.info("Listing all schedules")

        from core.dialogue.scheduler import get_scheduler

        scheduler = get_scheduler()
        schedules = await scheduler.list_all_schedules()

        return {
            "total": len(schedules),
            "schedules": schedules
        }

    except Exception as e:
        logger.error(f"Failed to list schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    세션 정보 조회
    
    Args:
        session_id: 세션 UUID
    
    Returns:
        SessionResponse with current status and conversation_count
    """
    try:
        logger.info(f"Getting session: session_id={session_id}")
        
        # TODO: SessionService.get_session()
        raise HTTPException(
            status_code=501,
            detail="SessionService not implemented yet. Please implement services/session_service.py"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    세션 상태 조회 (간소화)
    
    Returns:
        SessionStatusResponse with elapsed_time and is_active
    """
    try:
        logger.info(f"Getting session status: session_id={session_id}")
        
        # TODO: SessionService.get_session_status()
        raise HTTPException(
            status_code=501,
            detail="SessionService not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    세션 종료
    
    - status를 "completed"로 변경
    - completed_at 타임스탬프 기록
    - Redis 세션 데이터 정리
    
    Returns:
        SessionResponse with status="completed"
    """
    try:
        logger.info(f"Ending session: session_id={session_id}")
        
        # TODO: SessionService.end_session()
        # - Redis 세션 데이터 제거
        # - PostgreSQL에 종료 시간 기록
        # - 최종 대화 횟수 업데이트
        
        raise HTTPException(
            status_code=501,
            detail="SessionService not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{user_id}/sessions", response_model=SessionListResponse)
async def list_user_sessions(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    사용자의 세션 목록 조회 (페이지네이션)
    
    Args:
        user_id: 사용자 UUID
        skip: 건너뛸 개수
        limit: 조회 개수 (최대 100)
    
    Returns:
        SessionListResponse with sessions, total, page, page_size
    """
    try:
        logger.info(f"Listing sessions for user: user_id={user_id}, skip={skip}, limit={limit}")
        
        # TODO: SessionService.list_user_sessions()
        raise HTTPException(
            status_code=501,
            detail="SessionService not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list user sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# Schedule Management
# ============================================

from typing import Optional, List
from pydantic import BaseModel


class ScheduleCreateRequest(BaseModel):
    """스케줄 생성 요청"""
    schedule_times: Optional[List[str]] = None


@router.post("/users/{user_id}/schedule", status_code=201)
async def create_user_schedule(
    user_id: str,
    request: ScheduleCreateRequest = ScheduleCreateRequest()
):
    """
    사용자 대화 스케줄 생성

    일일 3회 자동 대화를 스케줄링합니다.

    Args:
        user_id: 사용자 UUID
        schedule_times: 커스텀 시간대 (선택, 기본값: 10:00, 15:00, 20:00)

    Returns:
        {
            "user_id": "user123",
            "schedule_times": ["10:00", "15:00", "20:00"],
            "job_ids": ["user123_10:00", "user123_15:00", "user123_20:00"],
            "enabled": True
        }

    Example:
        POST /api/v1/sessions/users/user123/schedule
        {
            "schedule_times": ["09:00", "14:00", "19:00"]
        }
    """
    try:
        logger.info(f"Creating schedule for user: {user_id}")

        from core.dialogue.scheduler import get_scheduler
        from datetime import time

        scheduler = get_scheduler()

        # 문자열 시간을 time 객체로 변환
        time_objects = None
        if request.schedule_times:
            time_objects = []
            for time_str in request.schedule_times:
                hour, minute = map(int, time_str.split(":"))
                time_objects.append(time(hour, minute))

        result = await scheduler.add_user_schedule(
            user_id=user_id,
            schedule_times=time_objects,
            enabled=True
        )

        logger.info(f"Schedule created for user: {user_id}")
        return result

    except Exception as e:
        logger.error(f"Failed to create schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.get("/users/{user_id}/schedule")
async def get_user_schedule(user_id: str):
    """
    사용자 스케줄 조회

    Args:
        user_id: 사용자 UUID

    Returns:
        스케줄 정보 또는 404
    """
    try:
        logger.info(f"Getting schedule for user: {user_id}")

        from core.dialogue.scheduler import get_scheduler

        scheduler = get_scheduler()
        schedule = await scheduler.get_user_schedule(user_id)

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        # 다음 실행 시간 추가
        next_run_time = scheduler.get_next_run_time(user_id)
        if next_run_time:
            schedule["next_run_time"] = next_run_time.isoformat()

        return schedule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/users/{user_id}/schedule")
async def delete_user_schedule(user_id: str):
    """
    사용자 스케줄 삭제

    Args:
        user_id: 사용자 UUID

    Returns:
        {"success": True, "message": "Schedule deleted"}
    """
    try:
        logger.info(f"Deleting schedule for user: {user_id}")

        from core.dialogue.scheduler import get_scheduler

        scheduler = get_scheduler()
        success = await scheduler.remove_user_schedule(user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")

        return {"success": True, "message": "Schedule deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
