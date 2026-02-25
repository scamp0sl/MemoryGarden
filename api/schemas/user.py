"""
사용자 관련 Pydantic 스키마

Author: Memory Garden Team
Created: 2025-02-10
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# 요청 스키마
# ============================================

class UserCreate(BaseModel):
    """사용자 생성 요청"""
    kakao_id: str = Field(..., description="카카오톡 사용자 ID")
    name: str = Field(..., min_length=1, max_length=100, description="사용자 이름")
    birth_date: Optional[str] = Field(None, description="생년월일 (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$", description="성별")
    phone: Optional[str] = Field(None, description="전화번호")
    garden_name: Optional[str] = Field(None, max_length=100, description="정원 이름")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kakao_id": "1234567890",
                "name": "홍길동",
                "birth_date": "1953-05-15",
                "gender": "male",
                "phone": "010-1234-5678",
                "garden_name": "수진이네 정원"
            }
        }
    )


class UserUpdate(BaseModel):
    """사용자 정보 수정 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    garden_name: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "홍길동",
                "phone": "010-1234-5678",
                "garden_name": "행복한 정원"
            }
        }
    )


class GuardianCreate(BaseModel):
    """보호자 등록 요청"""
    name: str = Field(..., min_length=1, max_length=100, description="보호자 이름")
    relationship: str = Field(..., description="관계 (daughter, son, spouse, etc.)")
    phone: str = Field(..., description="전화번호")
    email: Optional[str] = Field(None, description="이메일")
    kakao_id: Optional[str] = Field(None, description="카카오톡 ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "홍수진",
                "relationship": "daughter",
                "phone": "010-9876-5432",
                "email": "sujin@example.com",
                "kakao_id": "9876543210"
            }
        }
    )


# ============================================
# 응답 스키마
# ============================================

class UserResponse(BaseModel):
    """사용자 기본 정보 응답"""
    id: str = Field(..., description="사용자 UUID")
    kakao_id: str
    name: str
    garden_name: Optional[str] = None
    baseline_mcdi: Optional[float] = Field(None, description="Baseline MCDI 점수")
    current_mcdi: Optional[float] = Field(None, description="현재 MCDI 점수")
    risk_level: Optional[str] = Field(None, description="위험도 (GREEN/YELLOW/ORANGE/RED)")
    consecutive_days: int = Field(0, description="연속 참여 일수")
    total_conversations: int = Field(0, description="총 대화 횟수")
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "kakao_id": "1234567890",
                "name": "홍길동",
                "garden_name": "수진이네 정원",
                "baseline_mcdi": 78.2,
                "current_mcdi": 75.5,
                "risk_level": "GREEN",
                "consecutive_days": 15,
                "total_conversations": 42,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-02-10T14:30:00Z"
            }
        }
    )


class UserProfile(BaseModel):
    """사용자 프로필 (상세 정보)"""
    id: str
    kakao_id: str
    name: str
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    garden_name: Optional[str] = None

    # 분석 정보
    baseline_mcdi: Optional[float] = None
    current_mcdi: Optional[float] = None
    risk_level: Optional[str] = None

    # 참여 정보
    consecutive_days: int = 0
    total_conversations: int = 0
    last_conversation_at: Optional[datetime] = None

    # 정원 상태
    garden_status: Optional[dict] = None

    # 메타데이터
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "kakao_id": "1234567890",
                "name": "홍길동",
                "birth_date": "1953-05-15",
                "gender": "male",
                "phone": "010-1234-5678",
                "garden_name": "수진이네 정원",
                "baseline_mcdi": 78.2,
                "current_mcdi": 75.5,
                "risk_level": "GREEN",
                "consecutive_days": 15,
                "total_conversations": 42,
                "last_conversation_at": "2025-02-10T14:30:00Z",
                "garden_status": {
                    "flower_count": 42,
                    "butterfly_count": 5,
                    "garden_level": 3,
                    "weather": "sunny"
                },
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-02-10T14:30:00Z"
            }
        }
    )


class GuardianResponse(BaseModel):
    """보호자 정보 응답"""
    id: str
    user_id: str
    name: str
    relationship: str
    phone: str
    email: Optional[str] = None
    kakao_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "홍수진",
                "relationship": "daughter",
                "phone": "010-9876-5432",
                "email": "sujin@example.com",
                "kakao_id": "9876543210",
                "is_active": True,
                "created_at": "2025-01-15T10:05:00Z"
            }
        }
    )


class UserListResponse(BaseModel):
    """사용자 목록 응답"""
    users: list[UserResponse]
    total: int = Field(..., description="전체 사용자 수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "kakao_id": "1234567890",
                        "name": "홍길동",
                        "garden_name": "수진이네 정원",
                        "baseline_mcdi": 78.2,
                        "current_mcdi": 75.5,
                        "risk_level": "GREEN",
                        "consecutive_days": 15,
                        "total_conversations": 42,
                        "created_at": "2025-01-15T10:00:00Z",
                        "updated_at": "2025-02-10T14:30:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20
            }
        }
    )


# ============================================
# Export
# ============================================
__all__ = [
    "UserCreate",
    "UserUpdate",
    "GuardianCreate",
    "UserResponse",
    "UserProfile",
    "GuardianResponse",
    "UserListResponse",
]
