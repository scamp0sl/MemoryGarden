"""
기억 관련 Pydantic 스키마

Author: Memory Garden Team
Created: 2025-02-10
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# 요청 스키마
# ============================================

class MemorySearchRequest(BaseModel):
    """기억 검색 요청"""
    user_id: str = Field(..., description="사용자 UUID")
    query: Optional[str] = Field(None, description="검색 쿼리")
    memory_type: Optional[str] = Field(None, pattern="^(episodic|biographical|emotional|all)$", description="기억 유형")
    start_date: Optional[datetime] = Field(None, description="시작 날짜")
    end_date: Optional[datetime] = Field(None, description="종료 날짜")
    limit: int = Field(10, ge=1, le=100, description="조회 개수")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "query": "딸",
                "memory_type": "episodic",
                "start_date": "2025-02-01T00:00:00Z",
                "end_date": "2025-02-10T23:59:59Z",
                "limit": 10
            }
        }
    )


class MemorySearchByEmotionRequest(BaseModel):
    """감정별 기억 검색 요청"""
    user_id: str
    emotion: str = Field(..., pattern="^(joy|sadness|anger|fear|surprise|neutral)$")
    limit: int = Field(10, ge=1, le=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "emotion": "joy",
                "limit": 10
            }
        }
    )


# ============================================
# 응답 스키마
# ============================================

class EpisodicMemory(BaseModel):
    """일화 기억"""
    id: str
    user_id: str
    content: str = Field(..., description="기억 내용")
    importance: float = Field(..., ge=0, le=1, description="중요도 (0-1)")
    confidence: float = Field(..., ge=0, le=1, description="신뢰도 (0-1)")
    emotion: Optional[str] = None
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440003",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "오늘 점심에 딸이랑 같이 된장찌개 먹었어요",
                "importance": 0.85,
                "confidence": 0.9,
                "emotion": "joy",
                "timestamp": "2025-02-10T12:30:00Z",
                "created_at": "2025-02-10T12:35:00Z"
            }
        }
    )


class BiographicalFact(BaseModel):
    """전기적 사실"""
    id: str
    user_id: str
    entity: str = Field(..., description="엔티티 (예: daughter_name, hometown)")
    value: str = Field(..., description="값")
    fact_type: str = Field(..., description="사실 유형 (IMMUTABLE, SEMI_IMMUTABLE, PREFERENCE, TEMPORARY)")
    confidence: float = Field(..., ge=0, le=1)
    source_conversation_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440004",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "entity": "daughter_name",
                "value": "수진",
                "fact_type": "IMMUTABLE",
                "confidence": 0.95,
                "source_conversation_id": "770e8400-e29b-41d4-a716-446655440002",
                "created_at": "2025-02-10T14:30:00Z",
                "updated_at": None
            }
        }
    )


class EmotionalMemory(BaseModel):
    """감정 기억"""
    id: str
    user_id: str
    content: str
    emotion: str
    intensity: float = Field(..., ge=0, le=1, description="감정 강도")
    trigger: Optional[str] = Field(None, description="감정 유발 요인")
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "aa0e8400-e29b-41d4-a716-446655440005",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "딸이 전화해서 기분이 좋았다",
                "emotion": "joy",
                "intensity": 0.9,
                "trigger": "딸의 전화",
                "timestamp": "2025-02-10T15:00:00Z",
                "created_at": "2025-02-10T15:05:00Z"
            }
        }
    )


class MemorySearchResponse(BaseModel):
    """기억 검색 응답"""
    episodic_memories: list[EpisodicMemory] = Field(default_factory=list)
    biographical_facts: list[BiographicalFact] = Field(default_factory=list)
    emotional_memories: list[EmotionalMemory] = Field(default_factory=list)
    total_count: int
    query: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "episodic_memories": [
                    {
                        "id": "880e8400-e29b-41d4-a716-446655440003",
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "content": "오늘 점심에 딸이랑 같이 된장찌개 먹었어요",
                        "importance": 0.85,
                        "confidence": 0.9,
                        "emotion": "joy",
                        "timestamp": "2025-02-10T12:30:00Z",
                        "created_at": "2025-02-10T12:35:00Z"
                    }
                ],
                "biographical_facts": [
                    {
                        "id": "990e8400-e29b-41d4-a716-446655440004",
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "entity": "daughter_name",
                        "value": "수진",
                        "fact_type": "IMMUTABLE",
                        "confidence": 0.95,
                        "source_conversation_id": "770e8400-e29b-41d4-a716-446655440002",
                        "created_at": "2025-02-10T14:30:00Z",
                        "updated_at": None
                    }
                ],
                "emotional_memories": [],
                "total_count": 2,
                "query": "딸"
            }
        }
    )


class MemoryStats(BaseModel):
    """기억 통계"""
    user_id: str
    total_episodic: int
    total_biographical: int
    total_emotional: int
    most_common_emotion: Optional[str] = None
    memory_retention_rate: Optional[float] = Field(None, description="기억 보존율")
    last_updated: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_episodic": 42,
                "total_biographical": 15,
                "total_emotional": 28,
                "most_common_emotion": "joy",
                "memory_retention_rate": 0.85,
                "last_updated": "2025-02-10T18:00:00Z"
            }
        }
    )


# ============================================
# Export
# ============================================
__all__ = [
    "MemorySearchRequest",
    "MemorySearchByEmotionRequest",
    "EpisodicMemory",
    "BiographicalFact",
    "EmotionalMemory",
    "MemorySearchResponse",
    "MemoryStats",
]
