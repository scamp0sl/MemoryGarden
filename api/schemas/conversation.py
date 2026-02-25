"""
대화 관련 Pydantic 스키마

Author: Memory Garden Team
Created: 2025-02-10
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# 요청 스키마
# ============================================

class MessageRequest(BaseModel):
    """메시지 전송 요청"""
    user_id: str = Field(..., description="사용자 UUID")
    message: str = Field(..., min_length=1, description="사용자 메시지")
    message_type: str = Field("text", pattern="^(text|image|selection)$", description="메시지 유형")
    image_url: Optional[str] = Field(None, description="이미지 URL (message_type이 image일 때)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "오늘 점심에 된장찌개 먹었어요",
                "message_type": "text",
                "image_url": None
            }
        }
    )


class ImageMessageRequest(BaseModel):
    """이미지 메시지 요청"""
    user_id: str
    message: str = Field(..., description="이미지 설명 메시지")
    image_url: str = Field(..., description="이미지 URL")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "오늘 점심 사진이에요",
                "image_url": "https://example.com/lunch.jpg"
            }
        }
    )


# ============================================
# 응답 스키마
# ============================================

class MessageResponse(BaseModel):
    """메시지 응답"""
    success: bool = Field(..., description="처리 성공 여부")
    response: str = Field(..., description="AI 응답 메시지")
    session_id: Optional[str] = Field(None, description="세션 ID")
    
    # 분석 결과
    mcdi_score: Optional[float] = Field(None, description="MCDI 점수")
    risk_level: Optional[str] = Field(None, description="위험도")
    detected_emotion: Optional[str] = Field(None, description="감지된 감정")
    
    # 정원 상태
    garden_status: Optional[dict] = Field(None, description="정원 상태")
    achievements: Optional[list[str]] = Field(None, description="달성한 업적")
    level_up: bool = Field(False, description="레벨 업 여부")
    
    # 메타데이터
    execution_time_ms: Optional[float] = Field(None, description="처리 시간 (밀리초)")
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "response": "맛있게 드셨나요? 🌸 첫 번째 꽃이 피었어요!",
                "session_id": "770e8400-e29b-41d4-a716-446655440002",
                "mcdi_score": 75.5,
                "risk_level": "GREEN",
                "detected_emotion": "joy",
                "garden_status": {
                    "flower_count": 1,
                    "butterfly_count": 0,
                    "garden_level": 1,
                    "weather": "sunny",
                    "status_message": "정원이 건강하게 자라고 있어요! ☀️"
                },
                "achievements": ["first_flower"],
                "level_up": False,
                "execution_time_ms": 1250.5,
                "timestamp": "2025-02-10T14:30:00Z"
            }
        }
    )


class ConversationTurn(BaseModel):
    """대화 턴 (한 번의 주고받기)"""
    user_message: str
    assistant_message: str
    emotion: Optional[str] = None
    mcdi_score: Optional[float] = None
    timestamp: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_message": "오늘 점심에 된장찌개 먹었어요",
                "assistant_message": "맛있게 드셨나요?",
                "emotion": "joy",
                "mcdi_score": 75.5,
                "timestamp": "2025-02-10T14:30:00Z"
            }
        }
    )


class ConversationHistory(BaseModel):
    """대화 히스토리"""
    user_id: str
    session_id: Optional[str] = None
    turns: list[ConversationTurn]
    total_count: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "770e8400-e29b-41d4-a716-446655440002",
                "turns": [
                    {
                        "user_message": "오늘 점심에 된장찌개 먹었어요",
                        "assistant_message": "맛있게 드셨나요?",
                        "emotion": "joy",
                        "mcdi_score": 75.5,
                        "timestamp": "2025-02-10T14:30:00Z"
                    }
                ],
                "total_count": 1,
                "start_date": "2025-02-10T14:00:00Z",
                "end_date": "2025-02-10T14:30:00Z"
            }
        }
    )


class ConversationListResponse(BaseModel):
    """대화 목록 응답"""
    conversations: list[ConversationHistory]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversations": [
                    {
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "session_id": "770e8400-e29b-41d4-a716-446655440002",
                        "turns": [
                            {
                                "user_message": "오늘 점심에 된장찌개 먹었어요",
                                "assistant_message": "맛있게 드셨나요?",
                                "emotion": "joy",
                                "mcdi_score": 75.5,
                                "timestamp": "2025-02-10T14:30:00Z"
                            }
                        ],
                        "total_count": 1,
                        "start_date": "2025-02-10T14:00:00Z",
                        "end_date": "2025-02-10T14:30:00Z"
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
    "MessageRequest",
    "ImageMessageRequest",
    "MessageResponse",
    "ConversationTurn",
    "ConversationHistory",
    "ConversationListResponse",
]
