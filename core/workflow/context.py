"""
처리 컨텍스트

LangGraph State 대신 사용하는 dataclass.
메시지 처리 과정의 모든 정보를 담는 컨테이너.

Author: Memory Garden Team
Created: 2025-02-11
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

# ============================================
# 2. Logger
# ============================================
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================
# 3. ProcessingContext
# ============================================


@dataclass
class ProcessingContext:
    """메시지 처리 컨텍스트

    워크플로우의 모든 단계에서 공유하는 상태 객체.
    LangGraph State 대신 사용하는 순수 Python dataclass.

    Attributes:
        user_id: 사용자 고유 ID
        message: 사용자 입력 메시지
        message_type: text/image/selection
        memory: 검색된 메모리 데이터
        analysis: 분석 결과
        mcdi_score: MCDI 종합 점수
        risk_level: 위험도 (GREEN/YELLOW/ORANGE/RED)
        alert_needed: 알림 필요 여부
        should_check_confounds: 교란 변수 체크 필요 여부
        next_category: 다음 질문 카테고리
        next_difficulty: 다음 질문 난이도
        confound_question_scheduled: 교란 변수 질문
        response: 최종 응답 메시지
        processing_time_ms: 처리 시간 (밀리초)
        error: 에러 메시지 (발생 시)

    Example:
        >>> ctx = ProcessingContext(
        ...     user_id="user123",
        ...     message="봄에 엄마와 쑥을 뜯으러 갔어요"
        ... )
        >>> ctx.mcdi_score = 77.6
        >>> ctx.risk_level = "YELLOW"
        >>> print(ctx.to_dict())
    """

    # ============================================
    # 입력 (Required)
    # ============================================
    user_id: str
    message: str

    # ============================================
    # 입력 (Optional)
    # ============================================
    message_type: str = "text"
    image_url: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    # ============================================
    # 중간 처리 결과
    # ============================================
    memory: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    mcdi_score: Optional[float] = None

    # ============================================
    # 위험도 평가
    # ============================================
    risk_level: Optional[str] = None
    alert_needed: bool = False
    should_check_confounds: bool = False

    # ============================================
    # 다음 상호작용 계획
    # ============================================
    next_category: Optional[str] = None
    next_difficulty: Optional[str] = None
    confound_question_scheduled: Optional[str] = None

    # ============================================
    # 최종 출력
    # ============================================
    response: Optional[str] = None

    # ============================================
    # 메타데이터
    # ============================================
    processing_time_ms: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        로깅/저장용 딕셔너리 변환

        Returns:
            컨텍스트의 주요 정보를 담은 딕셔너리

        Example:
            >>> ctx = ProcessingContext(user_id="user123", message="안녕")
            >>> ctx.mcdi_score = 80.0
            >>> data = ctx.to_dict()
            >>> print(data["user_id"], data["mcdi_score"])
            user123 80.0
        """
        return {
            "user_id": self.user_id,
            "message": self.message,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "mcdi_score": self.mcdi_score,
            "risk_level": self.risk_level,
            "next_category": self.next_category,
            "next_difficulty": self.next_difficulty,
            "processing_time_ms": self.processing_time_ms,
            "error": self.error
        }

    def validate(self) -> bool:
        """
        필수 필드 검증

        Returns:
            검증 성공 여부

        Example:
            >>> ctx = ProcessingContext(user_id="", message="test")
            >>> ctx.validate()
            False
            >>> ctx.user_id = "user123"
            >>> ctx.validate()
            True
        """
        if not self.user_id:
            logger.error("Validation failed: user_id is empty")
            return False

        if not self.message:
            logger.error("Validation failed: message is empty")
            return False

        if self.message_type not in ["text", "image", "selection"]:
            logger.warning(f"Unknown message_type: {self.message_type}, defaulting to 'text'")
            self.message_type = "text"

        return True

    def __repr__(self) -> str:
        """디버깅용 문자열 표현"""
        return (
            f"ProcessingContext("
            f"user_id='{self.user_id}', "
            f"message_type='{self.message_type}', "
            f"mcdi_score={self.mcdi_score}, "
            f"risk_level='{self.risk_level}'"
            f")"
        )


# ============================================
# 4. Export
# ============================================
__all__ = [
    "ProcessingContext",
]

logger.info("Processing context module loaded")
