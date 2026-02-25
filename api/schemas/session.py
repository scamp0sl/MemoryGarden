"""
세션 관련 Pydantic 스키마

Author: Memory Garden Team
Created: 2025-02-10
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# 요청 스키마
# ============================================

class SessionCreate(BaseModel):
    """세션 생성 요청"""
    user_id: str = Field(..., description="사용자 UUID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


# ============================================
# 응답 스키마
# ============================================

class SessionResponse(BaseModel):
    """세션 정보 응답"""
    session_id: str = Field(..., description="세션 UUID")
    user_id: str
    status: str = Field(..., description="세션 상태 (active, completed, cancelled)")
    started_at: datetime
    completed_at: Optional[datetime] = None
    conversation_count: int = Field(0, description="이번 세션의 대화 횟수")
    last_activity_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "770e8400-e29b-41d4-a716-446655440002",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "active",
                "started_at": "2025-02-10T14:00:00Z",
                "completed_at": None,
                "conversation_count": 3,
                "last_activity_at": "2025-02-10T14:15:00Z"
            }
        }
    )


class SessionStatusResponse(BaseModel):
    """세션 상태 조회 응답"""
    session_id: str
    status: str
    is_active: bool
    elapsed_time_seconds: float
    conversation_count: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "770e8400-e29b-41d4-a716-446655440002",
                "status": "active",
                "is_active": True,
                "elapsed_time_seconds": 900.5,
                "conversation_count": 3
            }
        }
    )


class SessionListResponse(BaseModel):
    """세션 목록 응답"""
    sessions: list[SessionResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sessions": [
                    {
                        "session_id": "770e8400-e29b-41d4-a716-446655440002",
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "completed",
                        "started_at": "2025-02-10T14:00:00Z",
                        "completed_at": "2025-02-10T14:30:00Z",
                        "conversation_count": 5,
                        "last_activity_at": "2025-02-10T14:30:00Z"
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
    "SessionCreate",
    "SessionResponse",
    "SessionStatusResponse",
    "SessionListResponse",
]
