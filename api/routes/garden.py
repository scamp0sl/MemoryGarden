"""
정원 상태 API 라우터

게이미피케이션 - 정원 상태 및 업적 조회.

Author: Memory Garden Team
Created: 2025-02-10
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    GardenStatusResponse,
    GardenHistoryResponse,
    AchievementListResponse,
)
from database.postgres import get_db
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/garden", tags=["Garden"])


# ============================================
# 정원 상태 조회
# ============================================

@router.get("/users/{user_id}/garden", response_model=GardenStatusResponse)
async def get_user_garden_status(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 정원 상태 조회
    
    게임 메카닉 (SPEC.md 2.2.1):
    - 🌸 flower_count: 1 대화 = 1 꽃
    - 🦋 butterfly_count: 3일 연속 = 1 나비
    - 🌳 garden_level: 7일 연속마다 +1 레벨
    - 🏅 season_badge: 30일 = 계절 뱃지
    
    날씨 매핑 (위험도 → 날씨):
    - GREEN → ☀️ sunny
    - YELLOW → ☁️ cloudy
    - ORANGE → 🌧️ rainy
    - RED → ⛈️ stormy
    
    Returns:
        GardenStatusResponse with:
        - flower_count, butterfly_count, garden_level
        - consecutive_days, total_conversations
        - weather, season_badge
        - status_message, achievement_message, next_milestone
    """
    try:
        logger.info(f"Getting garden status: user_id={user_id}")
        
        # TODO: GardenMapper 주입
        # from core.analysis.garden_mapper import GardenMapper
        # 
        # garden_mapper = GardenMapper(db)
        # garden_status = await garden_mapper.get_garden_status(user_id)
        # 
        # return garden_status
        
        raise HTTPException(
            status_code=501,
            detail="GardenMapper not fully integrated yet. Please implement services/garden_service.py"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get garden status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{user_id}/garden/history", response_model=GardenHistoryResponse)
async def get_garden_history(
    user_id: str,
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    limit: int = Query(30, ge=1, le=365, description="조회 일수 (최대 365일)"),
    db: AsyncSession = Depends(get_db)
):
    """
    정원 히스토리 조회
    
    일별 정원 상태 변화를 시계열로 반환.
    
    Args:
        user_id: 사용자 UUID
        start_date: 시작 날짜 (선택, 기본: 30일 전)
        end_date: 종료 날짜 (선택, 기본: 오늘)
        limit: 조회 일수 (최대 365일)
    
    Returns:
        GardenHistoryResponse with:
        - history: 일별 정원 상태 목록
        - start_date, end_date, total_entries
    """
    try:
        logger.info(
            f"Getting garden history: user_id={user_id}, "
            f"start_date={start_date}, end_date={end_date}, limit={limit}"
        )
        
        # TODO: GardenMapper.get_garden_history()
        raise HTTPException(
            status_code=501,
            detail="GardenMapper history not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get garden history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# 업적 조회
# ============================================

@router.get("/users/{user_id}/achievements", response_model=AchievementListResponse)
async def get_user_achievements(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 업적 목록 조회
    
    달성한 업적 종류:
    - first_flower: 첫 번째 꽃 🌸
    - butterfly_visit: 첫 나비 방문 🦋
    - garden_expansion: 정원 확장 (레벨업) 🌳
    - flowers_10, flowers_42, flowers_100: 꽃 개수 이정표
    - streak_7days, streak_14days, streak_30days: 연속 참여 이정표
    - season_badge_spring/summer/autumn/winter: 계절 뱃지 🏅
    
    Returns:
        AchievementListResponse with:
        - achievements: 달성한 업적 목록
        - total_count: 총 업적 개수
        - latest_achievement: 최근 달성 업적
        - latest_achievement_date: 달성 날짜
    """
    try:
        logger.info(f"Getting achievements: user_id={user_id}")
        
        # TODO: GardenMapper.get_achievements()
        raise HTTPException(
            status_code=501,
            detail="Achievement system not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get achievements: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# 관리자 / 테스트용 엔드포인트
# ============================================

@router.post("/admin/users/{user_id}/garden/reset", response_model=GardenStatusResponse)
async def reset_user_garden(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    [관리자 전용] 정원 상태 초기화
    
    WARNING: 모든 정원 데이터가 초기화됩니다.
    - flower_count = 0
    - butterfly_count = 0
    - garden_level = 1
    - consecutive_days = 0
    - 모든 업적 삭제
    
    테스트 및 디버깅 목적으로만 사용하세요.
    """
    try:
        logger.warning(f"ADMIN: Resetting garden for user: user_id={user_id}")
        
        # TODO: GardenMapper.reset_garden()
        raise HTTPException(
            status_code=501,
            detail="Admin endpoints not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset garden: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
