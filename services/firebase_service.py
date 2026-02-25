"""
Firebase Cloud Messaging (FCM) 서비스

푸시 알림 전송 및 토큰 관리.
"""

from typing import Dict, Any, Optional, List
import firebase_admin
from firebase_admin import credentials, messaging
from pathlib import Path

from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import ExternalServiceError

logger = get_logger(__name__)


class FirebaseService:
    """
    Firebase Cloud Messaging 서비스

    Features:
        - 푸시 알림 전송
        - 멀티캐스트 (여러 기기 동시 전송)
        - 딥링크 지원
        - 토픽 구독
    """

    _instance: Optional['FirebaseService'] = None
    _initialized: bool = False

    def __new__(cls):
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Firebase Admin SDK 초기화"""
        if not self._initialized:
            self._initialize_firebase()
            self._initialized = True

    def _initialize_firebase(self):
        """Firebase Admin SDK 초기화"""
        try:
            # 이미 초기화되었는지 확인
            if firebase_admin._apps:
                logger.info("Firebase already initialized")
                return

            # 인증 파일 경로
            cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH)

            if not cred_path.exists():
                logger.warning(
                    f"Firebase credentials not found: {cred_path}. "
                    "FCM push notifications will be unavailable."
                )
                return

            # Firebase 초기화
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred)

            logger.info("✅ Firebase initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}", exc_info=True)
            raise ExternalServiceError(f"Firebase initialization failed: {e}") from e

    async def send_push_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        deep_link: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        단일 기기에 푸시 알림 전송

        Args:
            token: FCM 등록 토큰
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터 (딕셔너리)
            deep_link: 딥링크 URL (선택)

        Returns:
            {
                "success": True,
                "message_id": "projects/.../messages/...",
                "token": "...",
                "title": "...",
                "body": "..."
            }

        Raises:
            ExternalServiceError: 전송 실패 시

        Example:
            >>> service = FirebaseService()
            >>> result = await service.send_push_notification(
            ...     token="user_fcm_token",
            ...     title="Memory Garden 🌱",
            ...     body="오늘의 정원 가꾸기 시간입니다!",
            ...     deep_link="kakaotalk://talk/chat/_ZeUTxl"
            ... )
            >>> print(result["success"])
            True
        """
        try:
            # 데이터 준비
            notification_data = data or {}

            # 딥링크 추가
            if deep_link:
                notification_data["deep_link"] = deep_link

            # 메시지 구성
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=notification_data,
                token=token,
                # Android 설정
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        icon='notification_icon',
                        color='#4CAF50',  # Memory Garden 녹색
                        sound='default'
                    )
                ),
                # iOS 설정
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=title,
                                body=body
                            ),
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )

            # 전송
            response = messaging.send(message)

            logger.info(
                "Push notification sent successfully",
                extra={
                    "message_id": response,
                    "token": token[:20] + "...",
                    "title": title
                }
            )

            return {
                "success": True,
                "message_id": response,
                "token": token,
                "title": title,
                "body": body
            }

        except messaging.UnregisteredError:
            logger.warning(f"Token is unregistered: {token[:20]}...")
            raise ExternalServiceError("FCM token is unregistered or invalid")

        except messaging.SenderIdMismatchError:
            logger.error(f"Token sender ID mismatch: {token[:20]}...")
            raise ExternalServiceError("FCM token sender ID mismatch")

        except Exception as e:
            logger.error(
                f"Failed to send push notification: {e}",
                extra={"token": token[:20] + "..."},
                exc_info=True
            )
            raise ExternalServiceError(f"Failed to send push: {e}") from e

    async def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        deep_link: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        여러 기기에 동시 전송 (멀티캐스트)

        Args:
            tokens: FCM 토큰 리스트 (최대 500개)
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터
            deep_link: 딥링크 URL

        Returns:
            {
                "success_count": 2,
                "failure_count": 1,
                "failed_tokens": ["token3"],
                "responses": [...]
            }

        Example:
            >>> tokens = ["token1", "token2", "token3"]
            >>> result = await service.send_multicast(
            ...     tokens=tokens,
            ...     title="Memory Garden 🌱",
            ...     body="오늘의 정원 가꾸기 시간입니다!"
            ... )
            >>> print(f"성공: {result['success_count']}, 실패: {result['failure_count']}")
        """
        try:
            # 데이터 준비
            notification_data = data or {}
            if deep_link:
                notification_data["deep_link"] = deep_link

            # 멀티캐스트 메시지 구성
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=notification_data,
                tokens=tokens,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        icon='notification_icon',
                        color='#4CAF50',
                        sound='default'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=title,
                                body=body
                            ),
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )

            # 전송
            response = messaging.send_multicast(message)

            # 실패한 토큰 수집
            failed_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_tokens.append(tokens[idx])

            logger.info(
                f"Multicast sent: {response.success_count} success, "
                f"{response.failure_count} failures",
                extra={
                    "total_tokens": len(tokens),
                    "success_count": response.success_count,
                    "failure_count": response.failure_count
                }
            )

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "failed_tokens": failed_tokens,
                "responses": response.responses
            }

        except Exception as e:
            logger.error(f"Multicast send failed: {e}", exc_info=True)
            raise ExternalServiceError(f"Multicast send failed: {e}") from e

    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        토픽 구독자들에게 전송

        Args:
            topic: 토픽 이름 (예: "daily_prompts")
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터

        Returns:
            {"success": True, "message_id": "..."}

        Example:
            >>> # 모든 활성 사용자에게 전송
            >>> result = await service.send_to_topic(
            ...     topic="active_users",
            ...     title="Memory Garden 🌱",
            ...     body="오늘의 정원 가꾸기 시간입니다!"
            ... )
        """
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                topic=topic
            )

            response = messaging.send(message)

            logger.info(
                f"Topic message sent: {topic}",
                extra={"topic": topic, "message_id": response}
            )

            return {
                "success": True,
                "message_id": response,
                "topic": topic
            }

        except Exception as e:
            logger.error(f"Topic send failed: {e}", exc_info=True)
            raise ExternalServiceError(f"Topic send failed: {e}") from e

    async def subscribe_to_topic(
        self,
        tokens: List[str],
        topic: str
    ) -> Dict[str, Any]:
        """
        토픽 구독

        Args:
            tokens: FCM 토큰 리스트
            topic: 구독할 토픽 이름

        Returns:
            {"success_count": 2, "failure_count": 0}
        """
        try:
            response = messaging.subscribe_to_topic(tokens, topic)

            logger.info(
                f"Topic subscription: {topic}",
                extra={
                    "topic": topic,
                    "success_count": response.success_count,
                    "failure_count": response.failure_count
                }
            )

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }

        except Exception as e:
            logger.error(f"Topic subscription failed: {e}", exc_info=True)
            raise ExternalServiceError(f"Topic subscription failed: {e}") from e


# ============================================
# 싱글톤 인스턴스
# ============================================

_firebase_service: Optional[FirebaseService] = None


def get_firebase_service() -> FirebaseService:
    """
    FirebaseService 싱글톤 인스턴스 가져오기

    Returns:
        FirebaseService 인스턴스

    Example:
        >>> service = get_firebase_service()
        >>> await service.send_push_notification(...)
    """
    global _firebase_service

    if _firebase_service is None:
        _firebase_service = FirebaseService()

    return _firebase_service
