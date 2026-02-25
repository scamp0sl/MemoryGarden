from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

# 알림 기본 정보
class NotificationBase(BaseModel):
    user_id: str = Field(..., description="대상 사용자 ID")
    type: Literal["RISK_ALERT", "DAILY_REPORT", "SYSTEM"] = Field(..., description="알림 유형")
    
# 알림 전송 요청 (Request)
class NotificationCreate(NotificationBase):
    recipient_phone: str = Field(..., description="수신자(보호자) 전화번호")
    title: str = Field(..., description="알림 제목")
    content: str = Field(..., description="알림 본문 내용")
    risk_level: Optional[str] = Field(None, description="관련 위험도 등급 (ORANGE/RED 등)")

# 알림 전송 이력 (Response/Log)
class NotificationLog(NotificationBase):
    notification_id: int
    sent_at: datetime
    status: Literal["SUCCESS", "FAILED"]
    
    class Config:
        from_attributes = True