"""
알림 서비스

보호자에게 위험도 알림을 전송하는 서비스.
카카오톡 알림톡을 통해 알림 전송.

Author: Memory Garden Team
Created: 2025-02-11
Updated: 2025-02-11 (KakaoClient 통합, DB 연동)
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

# ============================================
# 2. Third-Party Imports
# ============================================

# ============================================
# 3. Local Imports
# ============================================
from services.kakao_client import KakaoClient, get_kakao_client
from database.postgres import get_db
from utils.logger import get_logger
from utils.exceptions import ExternalServiceError

# ============================================
# 4. Logger
# ============================================
logger = get_logger(__name__)


# ============================================
# 5. 데이터 모델
# ============================================

@dataclass
class Guardian:
    """보호자 정보"""
    id: str
    name: str
    phone: str
    relationship: str
    email: Optional[str] = None


# ============================================
# 6. NotificationService
# ============================================

class NotificationService:
    """
    알림 서비스

    위험도 상승 시 보호자에게 알림을 전송합니다.

    Features:
        - 카카오톡 알림톡 전송
        - 보호자 연락처 조회 (PostgreSQL)
        - 전송 로그 기록
        - Mock 모드 지원

    Attributes:
        kakao_client: KakaoClient 인스턴스
        mock_mode: Mock 모드 활성화 여부
    """

    def __init__(
        self,
        kakao_client: KakaoClient = None,
        mock_mode: bool = True
    ):
        """
        NotificationService 초기화

        Args:
            kakao_client: KakaoClient 인스턴스 (None이면 자동 생성)
            mock_mode: Mock 모드 활성화 (기본: True)
        """
        self.kakao_client = kakao_client or get_kakao_client(mock_mode=mock_mode)
        self.mock_mode = mock_mode

        mode_str = "MOCK" if mock_mode else "REAL"
        logger.info(f"✅ NotificationService initialized ({mode_str} mode)")

    async def send_guardian_alert(
        self,
        user_id: str,
        risk_level: str,
        mcdi_score: float,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        보호자에게 위험도 알림 전송

        Args:
            user_id: 사용자 ID
            risk_level: 위험도 레벨 (ORANGE/RED)
            mcdi_score: MCDI 점수
            analysis: 분석 결과

        Returns:
            알림 전송 결과
            {
                "alert_sent": True,
                "channel": "kakao",
                "message_id": "msg_12345",
                "guardian": {"name": "홍길동", "phone": "010-1234-5678"},
                "timestamp": "2025-02-11T15:00:00"
            }

        Example:
            >>> service = NotificationService(mock_mode=True)
            >>> result = await service.send_guardian_alert(
            ...     user_id="user123",
            ...     risk_level="ORANGE",
            ...     mcdi_score=55.0,
            ...     analysis={"scores": {...}}
            ... )
            >>> print(result["alert_sent"])
            True
        """
        logger.warning(
            f"🚨 Sending guardian alert",
            extra={
                "user_id": user_id,
                "risk_level": risk_level,
                "mcdi_score": mcdi_score
            }
        )

        try:
            # 1. 보호자 연락처 조회
            guardian = await self._get_guardian_contact(user_id)

            if not guardian:
                logger.warning(f"No guardian contact for user {user_id}")
                return {
                    "alert_sent": False,
                    "reason": "no_guardian",
                    "user_id": user_id
                }

            # 2. 알림 메시지 변수 생성
            message_vars = self._prepare_message_variables(
                guardian=guardian,
                risk_level=risk_level,
                mcdi_score=mcdi_score,
                analysis=analysis
            )

            # 3. 카카오톡 알림톡 전송
            try:
                kakao_result = await self.kakao_client.send_alimtalk(
                    phone=guardian.phone,
                    template_code="MEMORY_GARDEN_ALERT",
                    variables=message_vars
                )

                # 4. 전송 로그 기록 (성공)
                await self._log_notification(
                    user_id=user_id,
                    guardian_id=guardian.id,
                    risk_level=risk_level,
                    message_id=kakao_result.get("message_id"),
                    success=True
                )

                logger.info(
                    f"✅ Guardian alert sent successfully",
                    extra={
                        "user_id": user_id,
                        "guardian_name": guardian.name,
                        "message_id": kakao_result.get("message_id")
                    }
                )

                return {
                    "alert_sent": True,
                    "channel": "kakao",
                    "message_id": kakao_result.get("message_id"),
                    "guardian": {
                        "name": guardian.name,
                        "phone": guardian.phone
                    },
                    "timestamp": kakao_result.get("timestamp"),
                    "mode": kakao_result.get("mode", "unknown")
                }

            except Exception as e:
                # 4. 전송 로그 기록 (실패)
                await self._log_notification(
                    user_id=user_id,
                    guardian_id=guardian.id,
                    risk_level=risk_level,
                    error=str(e),
                    success=False
                )

                logger.error(
                    f"❌ Failed to send guardian alert: {e}",
                    exc_info=True
                )

                return {
                    "alert_sent": False,
                    "error": str(e),
                    "guardian": {
                        "name": guardian.name,
                        "phone": guardian.phone
                    }
                }

        except Exception as e:
            logger.error(
                f"Guardian alert workflow failed: {e}",
                exc_info=True
            )
            return {
                "alert_sent": False,
                "error": str(e)
            }

    async def _get_guardian_contact(
        self,
        user_id: str
    ) -> Optional[Guardian]:
        """
        보호자 연락처 조회 (PostgreSQL)

        Args:
            user_id: 사용자 ID

        Returns:
            Guardian 객체 (없으면 None)

        Example:
            >>> guardian = await service._get_guardian_contact("user_123")
            >>> print(guardian.name)
            "홍길동"
        """
        try:
            async for db in get_db():
                result = await db.execute(
                    """
                    SELECT
                        g.id, g.name, g.phone, g.relationship, g.email
                    FROM guardians g
                    JOIN user_guardians ug ON g.id = ug.guardian_id
                    WHERE ug.user_id = :user_id
                      AND g.is_active = TRUE
                    ORDER BY ug.priority ASC
                    LIMIT 1
                    """,
                    {"user_id": user_id}
                )

                row = result.fetchone()

                if row:
                    return Guardian(
                        id=row.id,
                        name=row.name,
                        phone=row.phone,
                        relationship=row.relationship,
                        email=row.email
                    )
                else:
                    return None

        except Exception as e:
            logger.error(f"Failed to get guardian contact: {e}")
            # Mock 모드에서는 테스트용 보호자 반환
            if self.mock_mode:
                logger.info("[MOCK] Returning test guardian")
                return Guardian(
                    id="mock_guardian_id",
                    name="테스트 보호자",
                    phone="010-0000-0000",
                    relationship="자녀"
                )
            return None

    def _prepare_message_variables(
        self,
        guardian: Guardian,
        risk_level: str,
        mcdi_score: float,
        analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        알림톡 템플릿 변수 준비

        Args:
            guardian: 보호자 정보
            risk_level: 위험도 레벨
            mcdi_score: MCDI 점수
            analysis: 분석 결과

        Returns:
            템플릿 변수 딕셔너리
        """
        # 긴급도 설정
        if risk_level == "RED":
            urgency = "⚠️ 즉시 확인 필요"
        elif risk_level == "ORANGE":
            urgency = "⚠️ 주의 필요"
        else:
            urgency = "ℹ️ 모니터링 필요"

        # 권장 사항 설정
        recommendation = self._get_recommendation(risk_level)

        return {
            "urgency": urgency,
            "user_name": guardian.name,
            "risk_level": risk_level,
            "mcdi_score": f"{mcdi_score:.1f}",
            "recommendation": recommendation
        }

    def _get_recommendation(self, risk_level: str) -> str:
        """
        위험도별 권장 사항

        Args:
            risk_level: 위험도 레벨

        Returns:
            권장 사항 메시지
        """
        recommendations = {
            "RED": "가능한 빨리 전문의 상담을 받으시기 바랍니다.",
            "ORANGE": "2주 내 전문의 상담을 권장합니다.",
            "YELLOW": "지속적인 관찰과 함께 1개월 내 검진을 권장합니다.",
            "GREEN": "현재 정상 범위입니다. 계속 모니터링하세요."
        }

        return recommendations.get(risk_level, "전문의와 상담하세요.")

    def _get_urgency(self, risk_level: str) -> str:
        """
        위험도별 긴급도 메시지

        Args:
            risk_level: 위험도 레벨

        Returns:
            긴급도 메시지
        """
        urgency_messages = {
            "RED": "⚠️ 즉시 확인 필요",
            "ORANGE": "⚠️ 주의 필요",
            "YELLOW": "ℹ️ 모니터링 필요",
            "GREEN": "✅ 정상 범위"
        }

        return urgency_messages.get(risk_level, "ℹ️ 알림")

    async def _log_notification(
        self,
        user_id: str,
        guardian_id: str,
        risk_level: str,
        message_id: str = None,
        error: str = None,
        success: bool = True
    ):
        """
        알림 전송 로그 기록 (PostgreSQL)

        Args:
            user_id: 사용자 ID
            guardian_id: 보호자 ID
            risk_level: 위험도 레벨
            message_id: 카카오톡 메시지 ID
            error: 에러 메시지 (실패 시)
            success: 성공 여부

        Returns:
            None
        """
        try:
            async for db in get_db():
                await db.execute(
                    """
                    INSERT INTO notification_logs (
                        user_id, guardian_id, risk_level,
                        message_id, error, success, created_at
                    ) VALUES (
                        :user_id, :guardian_id, :risk_level,
                        :message_id, :error, :success, NOW()
                    )
                    """,
                    {
                        "user_id": user_id,
                        "guardian_id": guardian_id,
                        "risk_level": risk_level,
                        "message_id": message_id,
                        "error": error,
                        "success": success
                    }
                )

                await db.commit()

            logger.debug(
                f"Notification log recorded",
                extra={
                    "user_id": user_id,
                    "success": success
                }
            )

        except Exception as e:
            logger.error(f"Failed to log notification: {e}")
            # 로그 기록 실패는 무시 (알림 전송 자체에는 영향 없음)

    async def send_weekly_report(
        self,
        user_id: str,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        주간 리포트 전송

        Args:
            user_id: 사용자 ID
            report_data: 주간 리포트 데이터

        Returns:
            전송 결과
        """
        logger.info(
            f"Sending weekly report for user {user_id}",
            extra={"user_id": user_id}
        )

        # TODO: 실제 주간 리포트 전송 구현
        # 현재는 알림과 동일한 플로우로 처리

        return {
            "report_sent": True,
            "channel": "kakao",
            "timestamp": datetime.now().isoformat()
        }

    def get_alert_preview(
        self,
        risk_level: str,
        mcdi_score: float,
        guardian_name: str = "홍길동"
    ) -> str:
        """
        알림 메시지 미리보기

        Args:
            risk_level: 위험도 레벨
            mcdi_score: MCDI 점수
            guardian_name: 보호자 이름

        Returns:
            렌더링된 알림 메시지

        Example:
            >>> preview = service.get_alert_preview("RED", 45.0)
            >>> print(preview)
            [Memory Garden 알림]
            ⚠️ 즉시 확인 필요
            ...
        """
        variables = {
            "urgency": self._get_urgency(risk_level),
            "user_name": guardian_name,
            "risk_level": risk_level,
            "mcdi_score": f"{mcdi_score:.1f}",
            "recommendation": self._get_recommendation(risk_level)
        }

        return self.kakao_client.get_template_preview(
            "MEMORY_GARDEN_ALERT",
            variables
        )


# ============================================
# 7. Export
# ============================================
__all__ = [
    "NotificationService",
    "Guardian"
]

logger.info("✅ Notification service module loaded")
