"""
사용자 관리 API 라우터

Author: Memory Garden Team
Created: 2025-02-10
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfile,
    GuardianCreate,
    GuardianResponse,
    UserListResponse,
)
from database.postgres import get_db
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


# ============================================
# User CRUD
# ============================================

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    신규 사용자 생성
    
    - **kakao_id**: 카카오톡 사용자 ID (필수)
    - **name**: 사용자 이름 (필수)
    - **birth_date**: 생년월일 (선택, YYYY-MM-DD)
    - **gender**: 성별 (선택, male/female/other)
    - **garden_name**: 정원 이름 (선택)
    
    Returns:
        UserResponse with UUID and initial status
    """
    try:
        logger.info(f"Creating user: kakao_id={user_data.kakao_id}")
        
        # TODO: UserService 구현 후 주입
        # user_service = UserService(db)
        # user = await user_service.create_user(user_data)
        
        # 임시 구현 (실제 DB 작업은 UserService에서)
        from datetime import datetime
        user_response = UserResponse(
            id="temp-user-id",  # UUID 생성 필요
            kakao_id=user_data.kakao_id,
            name=user_data.name,
            garden_name=user_data.garden_name,
            baseline_mcdi=None,
            current_mcdi=None,
            risk_level=None,
            consecutive_days=0,
            total_conversations=0,
            created_at=datetime.now(),
            updated_at=None
        )
        
        logger.info(f"User created: id={user_response.id}")
        return user_response
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 정보 조회
    
    Args:
        user_id: 사용자 UUID
    
    Returns:
        UserResponse with current MCDI score and risk level
    """
    try:
        logger.info(f"Getting user: user_id={user_id}")
        
        # TODO: UserService 구현 후 주입
        # user_service = UserService(db)
        # user = await user_service.get_user(user_id)
        # if not user:
        #     raise HTTPException(status_code=404, detail="User not found")
        
        # 임시 응답
        raise HTTPException(
            status_code=501,
            detail="UserService not implemented yet. Please implement services/user_service.py"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")


@router.get("/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 상세 프로필 조회 (정원 상태 포함)
    
    Returns:
        UserProfile with garden status and full details
    """
    try:
        logger.info(f"Getting user profile: user_id={user_id}")
        
        # TODO: UserService + GardenService 통합
        raise HTTPException(
            status_code=501,
            detail="UserService not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 정보 수정
    
    - **name**: 이름 변경
    - **phone**: 전화번호 변경
    - **garden_name**: 정원 이름 변경
    """
    try:
        logger.info(f"Updating user: user_id={user_id}")
        
        # TODO: UserService.update_user()
        raise HTTPException(
            status_code=501,
            detail="UserService not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(20, ge=1, le=100, description="조회 개수"),
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 목록 조회 (페이지네이션)
    
    Args:
        skip: 건너뛸 개수 (offset)
        limit: 조회 개수 (최대 100)
    """
    try:
        logger.info(f"Listing users: skip={skip}, limit={limit}")
        
        # TODO: UserService.list_users()
        raise HTTPException(
            status_code=501,
            detail="UserService not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# Guardian Management
# ============================================

@router.post("/{user_id}/guardians", response_model=GuardianResponse, status_code=201)
async def create_guardian(
    user_id: str,
    guardian_data: GuardianCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    보호자 등록
    
    - **name**: 보호자 이름
    - **relationship**: 관계 (daughter, son, spouse, etc.)
    - **phone**: 전화번호
    - **email**: 이메일 (선택)
    - **kakao_id**: 카카오톡 ID (선택)
    """
    try:
        logger.info(f"Creating guardian for user: user_id={user_id}")
        
        # TODO: GuardianService.create_guardian()
        raise HTTPException(
            status_code=501,
            detail="GuardianService not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create guardian: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/guardians", response_model=list[GuardianResponse])
async def list_guardians(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    사용자의 보호자 목록 조회
    """
    try:
        logger.info(f"Listing guardians for user: user_id={user_id}")
        
        # TODO: GuardianService.list_guardians()
        raise HTTPException(
            status_code=501,
            detail="GuardianService not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list guardians: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
