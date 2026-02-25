"""
정원 상태 관련 Pydantic 스키마

Author: Memory Garden Team
Created: 2025-02-10
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# 요청 스키마
# ============================================

class GardenUpdateRequest(BaseModel):
    """정원 상태 업데이트 요청 (테스트/관리자용)"""
    user_id: str
    mcdi_score: Optional[float] = Field(None, ge=0, le=100)
    risk_level: Optional[str] = Field(None, pattern="^(GREEN|YELLOW|ORANGE|RED)$")
    emotion: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "mcdi_score": 75.5,
                "risk_level": "GREEN",
                "emotion": "joy"
            }
        }
    )


# ============================================
# 응답 스키마
# ============================================

class GardenStatusResponse(BaseModel):
    """정원 상태 응답"""
    user_id: str
    
    # 게임 메카닉
    flower_count: int = Field(..., ge=0, description="총 꽃 개수 (1대화=1꽃)")
    butterfly_count: int = Field(..., ge=0, description="나비 방문 횟수 (3일연속=1나비)")
    garden_level: int = Field(..., ge=1, le=10, description="정원 레벨 (7일연속마다 +1)")
    consecutive_days: int = Field(..., ge=0, description="연속 참여 일수")
    total_conversations: int = Field(..., ge=0, description="총 대화 횟수")
    
    # 정원 상태
    weather: str = Field(..., description="날씨 상태 (sunny/cloudy/rainy/stormy)")
    season_badge: Optional[str] = Field(None, description="계절 뱃지 (spring/summer/autumn/winter)")
    
    # 메시지
    status_message: str = Field(..., description="정원 상태 메시지")
    achievement_message: Optional[str] = Field(None, description="업적 달성 메시지")
    next_milestone: Optional[str] = Field(None, description="다음 목표")
    
    # 메타데이터
    last_interaction_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "flower_count": 42,
                "butterfly_count": 5,
                "garden_level": 3,
                "consecutive_days": 15,
                "total_conversations": 42,
                "weather": "sunny",
                "season_badge": "winter",
                "status_message": "정원이 건강하게 자라고 있어요! ☀️",
                "achievement_message": None,
                "next_milestone": "🦋 1일 더 참여하면 나비가 날아와요!",
                "last_interaction_at": "2025-02-10T14:30:00Z",
                "updated_at": "2025-02-10T14:30:00Z"
            }
        }
    )


class GardenUpdateResponse(BaseModel):
    """정원 업데이트 응답"""
    previous_status: GardenStatusResponse
    current_status: GardenStatusResponse
    achievements_unlocked: list[str] = Field(default_factory=list, description="달성한 업적")
    level_up: bool = Field(False, description="레벨 업 여부")
    new_badge: Optional[str] = Field(None, description="새로 획득한 뱃지")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "previous_status": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "flower_count": 41,
                    "butterfly_count": 5,
                    "garden_level": 3,
                    "consecutive_days": 15,
                    "total_conversations": 41,
                    "weather": "sunny",
                    "season_badge": "winter",
                    "status_message": "정원이 건강하게 자라고 있어요! ☀️",
                    "achievement_message": None,
                    "next_milestone": "🦋 1일 더 참여하면 나비가 날아와요!",
                    "last_interaction_at": "2025-02-09T14:30:00Z",
                    "updated_at": "2025-02-09T14:30:00Z"
                },
                "current_status": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "flower_count": 42,
                    "butterfly_count": 5,
                    "garden_level": 3,
                    "consecutive_days": 15,
                    "total_conversations": 42,
                    "weather": "sunny",
                    "season_badge": "winter",
                    "status_message": "정원이 건강하게 자라고 있어요! ☀️",
                    "achievement_message": "🌺 꽃 42송이 달성!",
                    "next_milestone": "🦋 1일 더 참여하면 나비가 날아와요!",
                    "last_interaction_at": "2025-02-10T14:30:00Z",
                    "updated_at": "2025-02-10T14:30:00Z"
                },
                "achievements_unlocked": ["flowers_42"],
                "level_up": False,
                "new_badge": None
            }
        }
    )


class GardenHistoryEntry(BaseModel):
    """정원 히스토리 항목"""
    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    flower_count: int
    butterfly_count: int
    garden_level: int
    consecutive_days: int
    weather: str
    achievements: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2025-02-10",
                "flower_count": 42,
                "butterfly_count": 5,
                "garden_level": 3,
                "consecutive_days": 15,
                "weather": "sunny",
                "achievements": ["flowers_42"]
            }
        }
    )


class GardenHistoryResponse(BaseModel):
    """정원 히스토리 응답"""
    user_id: str
    history: list[GardenHistoryEntry]
    start_date: str
    end_date: str
    total_entries: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "history": [
                    {
                        "date": "2025-02-10",
                        "flower_count": 42,
                        "butterfly_count": 5,
                        "garden_level": 3,
                        "consecutive_days": 15,
                        "weather": "sunny",
                        "achievements": ["flowers_42"]
                    }
                ],
                "start_date": "2025-02-01",
                "end_date": "2025-02-10",
                "total_entries": 10
            }
        }
    )


class AchievementListResponse(BaseModel):
    """업적 목록 응답"""
    user_id: str
    achievements: list[str] = Field(..., description="달성한 업적 목록")
    total_count: int
    latest_achievement: Optional[str] = None
    latest_achievement_date: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "achievements": [
                    "first_flower",
                    "butterfly_visit",
                    "garden_expansion",
                    "flowers_10",
                    "flowers_42",
                    "streak_7days",
                    "streak_14days"
                ],
                "total_count": 7,
                "latest_achievement": "flowers_42",
                "latest_achievement_date": "2025-02-10T14:30:00Z"
            }
        }
    )


# ============================================
# Export
# ============================================
__all__ = [
    "GardenUpdateRequest",
    "GardenStatusResponse",
    "GardenUpdateResponse",
    "GardenHistoryEntry",
    "GardenHistoryResponse",
    "AchievementListResponse",
]
