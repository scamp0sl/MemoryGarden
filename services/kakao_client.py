"""
카카오톡 알림톡 API 클라이언트

Mock 모드를 지원하여 실제 카카오 설정 없이 개발 가능.
"""

import asyncio
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4

import httpx

from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import ExternalServiceError

logger = get_logger(__name__)


class KakaoClient:
    """
    카카오톡 알림톡 API 클라이언트

    Features:
        - 알림톡 전송
        - Mock 모드 지원 (개발/테스트용)
        - Retry 로직 (3회)
        - 전송 로그 기록
    """

    def __init__(
        self,
        api_key: str = None,
        admin_key: str = None,
        sender_key: str = None,
        mock_mode: bool = None
    ):
        """
        Args:
            api_key: 카카오 REST API 키
            admin_key: 카카오 Admin 키 (친구톡 전송용)
            sender_key: 발신 프로필 키
            mock_mode: Mock 모드 활성화 (None이면 settings.KAKAO_MOCK_MODE 사용)
        """
        self.api_key = api_key or getattr(settings, "KAKAO_REST_API_KEY", "mock_api_key")
        self.admin_key = admin_key or getattr(settings, "KAKAO_ADMIN_KEY", "mock_admin_key")
        self.sender_key = sender_key or getattr(settings, "KAKAO_SENDER_KEY", None)
        # mock_mode가 명시되지 않으면 settings에서 읽기
        self.mock_mode = mock_mode if mock_mode is not None else getattr(settings, "KAKAO_MOCK_MODE", True)
        self.base_url = "https://kapi.kakao.com"
        self.timeout = 10.0

        # 비즈메시지 설정
        self.biz_client_id = getattr(settings, "KAKAO_BIZ_CLIENT_ID", None)
        self.biz_client_secret = getattr(settings, "KAKAO_BIZ_CLIENT_SECRET", None)
        self.biz_base_url = getattr(settings, "KAKAO_BIZ_BASE_URL", "https://bizmsg-web.kakaoenterprise.com")

        # 비즈메시지 OAuth 토큰 캐시
        self._biz_token: Optional[str] = None
        self._biz_token_expires_at: Optional[datetime] = None

        if self.mock_mode:
            logger.info("✅ KakaoClient initialized in MOCK mode")
        else:
            logger.info(
                "✅ KakaoClient initialized in REAL mode",
                extra={
                    "has_sender_key": bool(self.sender_key),
                    "has_biz_credentials": bool(self.biz_client_id and self.biz_client_secret)
                }
            )

    async def send_friend_talk(
        self,
        user_key: str,
        message: str,
        access_token: Optional[str] = None,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        친구톡 전송 (템플릿 승인 불필요!)

        Args:
            user_key: 사용자 고유 키 (카카오 채널 친구 ID)
            message: 자유 형식 메시지 (최대 1000자)
            access_token: 사용자 OAuth 액세스 토큰 (필수!)
            retry_count: 재시도 횟수 (기본: 3)

        Returns:
            {
                "success": True,
                "message_id": "msg_12345",
                "timestamp": "2025-02-11T15:00:00",
                "user_key": "user_xxx",
                "message_length": 45
            }

        Raises:
            ExternalServiceError: 전송 실패 시

        Note:
            - 템플릿 승인 불필요 ✅
            - 채널 친구에게만 발송 가능
            - 광고성 메시지 아님 (정보성 메시지만)

        Example:
            >>> client = KakaoClient(mock_mode=False)
            >>> result = await client.send_friend_talk(
            ...     user_key="user_abc123",
            ...     message="안녕하세요! 오늘의 정원 가꾸기 시간입니다 🌱\\n\\n어제 저녁은 무엇을 드셨나요?",
            ...     access_token="user_oauth_token_here"
            ... )
            >>> print(result["success"])
            True
        """
        # Mock 모드
        if self.mock_mode:
            return await self._send_mock_friend_talk(user_key, message)

        # 실제 카카오 API 호출
        if not access_token:
            raise ValueError(
                "access_token is required for real mode. "
                "Use /kakao/oauth/login to obtain access token."
            )

        return await self._send_real_friend_talk(user_key, message, access_token, retry_count)

    async def send_alimtalk(
        self,
        phone: str,
        template_code: str,
        variables: Dict[str, str],
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        알림톡 전송

        Args:
            phone: 수신자 전화번호 (010-XXXX-XXXX)
            template_code: 템플릿 코드 (예: MEMORY_GARDEN_ALERT)
            variables: 템플릿 변수
                {
                    "urgency": "즉시 확인 필요",
                    "user_name": "홍길동",
                    "risk_level": "RED",
                    "mcdi_score": "45.0",
                    "recommendation": "가능한 빨리 전문의 상담을 받으세요."
                }
            retry_count: 재시도 횟수 (기본: 3)

        Returns:
            {
                "success": True,
                "message_id": "msg_12345",
                "timestamp": "2025-02-11T15:00:00",
                "phone": "010-XXXX-XXXX",
                "template_code": "MEMORY_GARDEN_ALERT"
            }

        Raises:
            ExternalServiceError: 전송 실패 시

        Example:
            >>> client = KakaoClient(mock_mode=True)
            >>> result = await client.send_alimtalk(
            ...     phone="010-1234-5678",
            ...     template_code="MEMORY_GARDEN_ALERT",
            ...     variables={"urgency": "즉시 확인 필요", ...}
            ... )
            >>> print(result["success"])
            True
        """
        # Mock 모드
        if self.mock_mode:
            return await self._send_mock_alimtalk(
                phone, template_code, variables
            )

        # 실제 카카오 API 호출
        return await self._send_real_alimtalk(
            phone, template_code, variables, retry_count
        )

    async def _send_mock_friend_talk(
        self,
        user_key: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Mock 친구톡 전송 (실제 전송 없음)

        개발/테스트용으로 즉시 성공 응답 반환.
        """
        message_id = f"mock_ft_{uuid4().hex[:12]}"

        logger.info(
            f"[MOCK] Friend Talk sent",
            extra={
                "user_key": user_key,
                "message_length": len(message),
                "message_preview": message[:50] + "..." if len(message) > 50 else message,
                "message_id": message_id
            }
        )

        return {
            "success": True,
            "message_id": message_id,
            "timestamp": datetime.now().isoformat(),
            "user_key": user_key,
            "message_length": len(message),
            "mode": "mock"
        }

    async def _send_mock_alimtalk(
        self,
        phone: str,
        template_code: str,
        variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Mock 알림톡 전송 (실제 전송 없음)

        개발/테스트용으로 즉시 성공 응답 반환.
        """
        message_id = f"mock_{uuid4().hex[:12]}"

        logger.info(
            f"[MOCK] Alimtalk sent",
            extra={
                "phone": phone,
                "template_code": template_code,
                "variables": variables,
                "message_id": message_id
            }
        )

        return {
            "success": True,
            "message_id": message_id,
            "timestamp": datetime.now().isoformat(),
            "phone": phone,
            "template_code": template_code,
            "mode": "mock"
        }

    async def _send_real_friend_talk(
        self,
        user_key: str,
        message: str,
        access_token: str,
        retry_count: int
    ) -> Dict[str, Any]:
        """
        실제 친구톡 전송

        카카오 친구톡 API를 호출하여 실제 메시지 전송.
        OAuth 2.0 사용자 액세스 토큰 필요.

        중요: 카카오 공식 문서에 따라
        - Content-Type: application/x-www-form-urlencoded
        - receiver_uuids: JSON 문자열
        - template_object: JSON 문자열
        """
        import json

        attempt = 0
        last_error = None

        while attempt < retry_count:
            attempt += 1

            try:
                async with httpx.AsyncClient() as client:
                    # 템플릿 객체 구성
                    template_object = {
                        "object_type": "text",
                        "text": message,
                        "link": {
                            "web_url": "https://n8n.softline.co.kr",
                            "mobile_web_url": "https://n8n.softline.co.kr"
                        }
                    }

                    # Form data로 전송 (카카오 공식 문서 요구사항)
                    response = await client.post(
                        f"{self.base_url}/v1/api/talk/friends/message/default/send",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"  # ✅ 수정
                        },
                        data={  # ✅ json → data 변경
                            "receiver_uuids": json.dumps([user_key], ensure_ascii=False),  # ✅ JSON 문자열로
                            "template_object": json.dumps(template_object, ensure_ascii=False)  # ✅ JSON 문자열로
                        },
                        timeout=self.timeout
                    )

                    response.raise_for_status()
                    data = response.json()

                    logger.info(
                        f"[REAL] Friend Talk sent successfully",
                        extra={
                            "user_key": user_key,
                            "message_length": len(message),
                            "attempt": attempt
                        }
                    )

                    return {
                        "success": True,
                        "message_id": data.get("messageId", f"ft_{uuid4().hex[:12]}"),
                        "timestamp": datetime.now().isoformat(),
                        "user_key": user_key,
                        "message_length": len(message),
                        "mode": "real"
                    }

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"Friend Talk HTTP error (attempt {attempt}/{retry_count}): {e}",
                    extra={
                        "status_code": e.response.status_code,
                        "response": e.response.text
                    }
                )

                # 400 에러는 재시도 안 함 (잘못된 요청)
                if e.response.status_code == 400:
                    break

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Friend Talk error (attempt {attempt}/{retry_count}): {e}"
                )

        # 모든 재시도 실패
        logger.error(
            f"Friend Talk failed after {retry_count} attempts: {last_error}",
            exc_info=True
        )

        raise ExternalServiceError(
            f"Failed to send friend talk after {retry_count} attempts: {last_error}"
        ) from last_error

    async def _send_real_alimtalk(
        self,
        phone: str,
        template_code: str,
        variables: Dict[str, str],
        retry_count: int
    ) -> Dict[str, Any]:
        """
        실제 알림톡 전송

        카카오 API를 호출하여 실제 메시지 전송.
        """
        attempt = 0
        last_error = None

        while attempt < retry_count:
            attempt += 1

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/v2/api/alimtalk/send",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "senderKey": self.sender_key,
                            "templateCode": template_code,
                            "recipientList": [{
                                "recipientNo": phone,
                                "templateParameter": variables
                            }]
                        },
                        timeout=self.timeout
                    )

                    response.raise_for_status()
                    data = response.json()

                    logger.info(
                        f"[REAL] Alimtalk sent successfully",
                        extra={
                            "phone": phone,
                            "template_code": template_code,
                            "attempt": attempt
                        }
                    )

                    return {
                        "success": True,
                        "message_id": data.get("messageId"),
                        "timestamp": datetime.now().isoformat(),
                        "phone": phone,
                        "template_code": template_code,
                        "mode": "real"
                    }

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"Alimtalk HTTP error (attempt {attempt}/{retry_count}): {e}",
                    extra={
                        "status_code": e.response.status_code,
                        "response": e.response.text
                    }
                )

                # 400 에러는 재시도 안 함 (잘못된 요청)
                if e.response.status_code == 400:
                    break

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Alimtalk error (attempt {attempt}/{retry_count}): {e}"
                )

        # 모든 재시도 실패
        logger.error(
            f"Alimtalk failed after {retry_count} attempts: {last_error}",
            exc_info=True
        )

        raise ExternalServiceError(
            f"Failed to send alimtalk after {retry_count} attempts: {last_error}"
        ) from last_error

    async def validate_template(
        self,
        template_code: str
    ) -> bool:
        """
        템플릿 유효성 검증

        Args:
            template_code: 템플릿 코드

        Returns:
            유효하면 True, 아니면 False

        Note:
            Mock 모드에서는 항상 True 반환
        """
        if self.mock_mode:
            logger.debug(f"[MOCK] Template {template_code} validated")
            return True

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v2/api/alimtalk/template/{template_code}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    timeout=self.timeout
                )

                return response.status_code == 200

        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            return False

    def get_template_preview(
        self,
        template_code: str,
        variables: Dict[str, str]
    ) -> str:
        """
        템플릿 미리보기 생성

        Args:
            template_code: 템플릿 코드
            variables: 템플릿 변수

        Returns:
            렌더링된 메시지

        Example:
            >>> preview = client.get_template_preview(
            ...     "MEMORY_GARDEN_ALERT",
            ...     {"urgency": "즉시 확인 필요", "user_name": "홍길동"}
            ... )
            >>> print(preview)
            [Memory Garden 알림]
            즉시 확인 필요
            사용자 ID: 홍길동
            ...
        """
        # 기본 템플릿
        if template_code == "MEMORY_GARDEN_ALERT":
            return f"""[Memory Garden 알림]

{variables.get('urgency', 'N/A')}

사용자 ID: {variables.get('user_name', 'N/A')}
위험도: {variables.get('risk_level', 'N/A')}
MCDI 점수: {variables.get('mcdi_score', 'N/A')}점

## 권장 사항
{variables.get('recommendation', 'N/A')}

자세한 내용은 Memory Garden 앱에서 확인하세요."""

        # 다른 템플릿은 간단한 키-값 출력
        return "\n".join([f"{k}: {v}" for k, v in variables.items()])

    async def health_check(self) -> bool:
        """
        카카오 API 서버 상태 확인

        Returns:
            정상이면 True, 아니면 False

        Note:
            Mock 모드에서는 항상 True 반환
        """
        if self.mock_mode:
            return True

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/api/health",
                    timeout=5.0
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Kakao API health check failed: {e}")
            return False

    # ============================================
    # OAuth 기반 메시지 전송 (2026-02-12 추가)
    # ============================================

    async def get_friends(
        self,
        access_token: str,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        카카오톡 친구 목록 조회

        Args:
            access_token: 사용자의 카카오 액세스 토큰
            limit: 조회할 친구 수 (기본: 10, 최대: 100)
            offset: 시작 위치 (페이지네이션)

        Returns:
            {
                "elements": [
                    {
                        "uuid": "friend_uuid_1",
                        "profile_nickname": "친구1",
                        "profile_thumbnail_image": "https://...",
                        "favorite": false
                    },
                    ...
                ],
                "total_count": 42,
                "before_url": "...",
                "after_url": "..."
            }

        Raises:
            ExternalServiceError: 조회 실패 시

        Example:
            >>> client = KakaoClient()
            >>> friends = await client.get_friends(access_token="user_token")
            >>> print(friends["total_count"])
            42
        """
        if self.mock_mode:
            logger.info(f"✅ [MOCK] Getting friends list (limit={limit}, offset={offset})")
            return {
                "elements": [
                    {
                        "uuid": f"mock_friend_{i}",
                        "profile_nickname": f"테스트친구{i}",
                        "profile_thumbnail_image": "",
                        "favorite": False
                    }
                    for i in range(1, min(limit + 1, 4))
                ],
                "total_count": 3,
                "before_url": None,
                "after_url": None
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://kapi.kakao.com/v1/api/talk/friends",
                    headers={
                        "Authorization": f"Bearer {access_token}"
                    },
                    params={
                        "limit": limit,
                        "offset": offset
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Get friends failed: {e}",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text
                }
            )
            raise ExternalServiceError(f"친구 목록 조회 실패: {e.response.text}")

        except Exception as e:
            logger.error(f"Get friends failed: {e}", exc_info=True)
            raise ExternalServiceError(f"친구 목록 조회 실패: {e}")

    async def send_to_me(
        self,
        access_token: str,
        message: str
    ) -> Dict[str, Any]:
        """
        나에게 보내기 (OAuth 버전)

        Args:
            access_token: 사용자의 카카오 액세스 토큰
            message: 전송할 메시지

        Returns:
            전송 결과

        Raises:
            ExternalServiceError: 전송 실패 시

        Example:
            >>> client = KakaoClient()
            >>> result = await client.send_to_me(
            ...     access_token="user_token",
            ...     message="안녕하세요! 오늘 하루는 어떠셨나요?"
            ... )
        """
        if self.mock_mode:
            logger.info(f"✅ [MOCK] Sending to self: {message[:50]}...")
            return {
                "success": True,
                "mock": True,
                "message": message[:100]
            }

        # 버튼 URL: 반드시 카카오 앱에 등록된 도메인이어야 허용됨
        # 우리 서버(/kakao/channel)를 경유해 pf.kakao.com/채널ID/chat으로 리다이렉트
        import json
        channel_redirect_url = "https://n8n.softline.co.kr/kakao/channel"

        template_object = {
            "object_type": "text",
            "text": message,
            "link": {
                "web_url": channel_redirect_url,
                "mobile_web_url": channel_redirect_url
            },
            "button_title": "채널에서 답하기 🌱"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://kapi.kakao.com/v2/api/talk/memo/default/send",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
                    },
                    data={
                        "template_object": json.dumps(template_object, ensure_ascii=False)
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Send to me failed: {e}",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text
                }
            )
            raise ExternalServiceError(f"카카오톡 메시지 전송 실패: {e.response.text}")

        except Exception as e:
            logger.error(f"Send to me failed: {e}", exc_info=True)
            raise ExternalServiceError(f"카카오톡 메시지 전송 실패: {e}")

    async def send_to_friends(
        self,
        access_token: str,
        receiver_uuids: list,
        message: str
    ) -> Dict[str, Any]:
        """
        친구에게 보내기 (OAuth 버전)

        Args:
            access_token: 사용자의 카카오 액세스 토큰
            receiver_uuids: 친구 UUID 리스트 (최대 5명)
            message: 전송할 메시지

        Returns:
            전송 결과

        Raises:
            ExternalServiceError: 전송 실패 시

        Example:
            >>> client = KakaoClient()
            >>> result = await client.send_to_friends(
            ...     access_token="user_token",
            ...     receiver_uuids=["uuid1", "uuid2"],
            ...     message="안녕하세요!"
            ... )
        """
        if self.mock_mode:
            logger.info(f"✅ [MOCK] Sending to {len(receiver_uuids)} friends: {message[:50]}...")
            return {
                "success": True,
                "mock": True,
                "receiver_count": len(receiver_uuids)
            }

        # 템플릿 객체 생성
        import json
        template_object = {
            "object_type": "text",
            "text": message,
            "link": {
                "web_url": "https://n8n.softline.co.kr/static/index.html",
                "mobile_web_url": "https://n8n.softline.co.kr/static/index.html"
            },
            "button_title": "대화하기"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://kapi.kakao.com/v1/api/talk/friends/message/default/send",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
                    },
                    data={
                        "receiver_uuids": json.dumps(receiver_uuids),
                        "template_object": json.dumps(template_object, ensure_ascii=False)
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Send to friends failed: {e}",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text
                }
            )
            raise ExternalServiceError(f"친구톡 전송 실패: {e.response.text}")

        except Exception as e:
            logger.error(f"Send to friends failed: {e}", exc_info=True)
            raise ExternalServiceError(f"친구톡 전송 실패: {e}")

    async def _get_bizmessage_token(self) -> str:
        """
        비즈메시지 OAuth 2.0 액세스 토큰 획득 (캐싱 포함)

        카카오 i 커넥트 메시지 플랫폼용 토큰.
        만료 5분 전에 자동 갱신.

        Returns:
            Bearer 액세스 토큰

        Raises:
            ExternalServiceError: 토큰 획득 실패 시
        """
        # 캐시된 토큰이 유효한지 확인
        if (
            self._biz_token
            and self._biz_token_expires_at
            and datetime.now() < self._biz_token_expires_at - timedelta(minutes=5)
        ):
            return self._biz_token

        if not self.biz_client_id or not self.biz_client_secret:
            raise ExternalServiceError(
                "비즈메시지 자격증명 미설정: .env에 KAKAO_BIZ_CLIENT_ID, KAKAO_BIZ_CLIENT_SECRET 추가 필요"
            )

        # Basic auth 헤더 생성 (base64 인코딩)
        credentials = f"{self.biz_client_id}:{self.biz_client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.biz_base_url}/v2/oauth/token",
                    headers={
                        "Authorization": f"Basic {encoded}",
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    data={"grant_type": "client_credentials"},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                self._biz_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._biz_token_expires_at = datetime.now() + timedelta(seconds=expires_in)

                logger.info("비즈메시지 OAuth 토큰 획득 성공")
                return self._biz_token

        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(
                f"비즈메시지 토큰 획득 실패 HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
        except Exception as e:
            raise ExternalServiceError(f"비즈메시지 토큰 획득 실패: {e}")

    async def send_bizmessage_friend_talk(
        self,
        plus_friend_user_key: str,
        message: str,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        비즈메시지 친구톡 전송 (채널 → 구독자 직접 발송)

        카카오 i 커넥트 메시지 API 사용.
        채널 관리자가 구독자에게 먼저 메시지를 보낼 수 있음.

        필요 설정:
        - KAKAO_BIZ_CLIENT_ID: 비즈메시지 클라이언트 ID
        - KAKAO_BIZ_CLIENT_SECRET: 비즈메시지 클라이언트 시크릿
        - KAKAO_SENDER_KEY: 발신프로파일키 (40자)

        Args:
            plus_friend_user_key: plusfriendUserKey (채널 구독자 식별자)
            message: 전송할 메시지 (최대 1000자)
            retry_count: 재시도 횟수

        Returns:
            {
                "success": True,
                "method": "bizmessage_ft",
                "message_id": "...",
                "plus_friend_user_key": "..."
            }

        Raises:
            ExternalServiceError: 전송 실패 또는 자격증명 미설정 시
        """
        if self.mock_mode:
            logger.info(
                f"[MOCK] BizMessage FriendTalk sent to {plus_friend_user_key[:8]}...",
                extra={"message_preview": message[:50]}
            )
            return {
                "success": True,
                "method": "bizmessage_ft_mock",
                "plus_friend_user_key": plus_friend_user_key,
                "message_length": len(message)
            }

        if not self.sender_key:
            raise ExternalServiceError(
                "발신프로파일키 미설정: .env에 KAKAO_SENDER_KEY 추가 필요\n"
                "카카오 i 커넥트 메시지 콘솔에서 발신프로파일 등록 후 발급"
            )

        attempt = 0
        last_error = None

        while attempt < retry_count:
            attempt += 1
            try:
                token = await self._get_bizmessage_token()
                cid = f"mg_{uuid4().hex[:16]}"

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.biz_base_url}/v2/send/kakao",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "message_type": "FT",
                            "sender_key": self.sender_key,
                            "user_key": plus_friend_user_key,
                            "message": message,
                            "fall_back_yn": False,
                            "cid": cid
                        },
                        timeout=self.timeout
                    )

                    if response.status_code in (200, 201):
                        data = response.json()
                        logger.info(
                            f"[REAL] BizMessage FriendTalk sent to {plus_friend_user_key[:8]}...",
                            extra={"attempt": attempt, "cid": cid}
                        )
                        return {
                            "success": True,
                            "method": "bizmessage_ft",
                            "plus_friend_user_key": plus_friend_user_key,
                            "message_id": data.get("msg_uid", cid),
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                        logger.warning(
                            f"BizMessage FriendTalk HTTP {response.status_code} (attempt {attempt}/{retry_count})",
                            extra={"response_body": response.text[:300]}
                        )

                        # 401은 토큰 만료 가능성 → 캐시 무효화 후 재시도
                        if response.status_code == 401:
                            self._biz_token = None
                            self._biz_token_expires_at = None
                        elif response.status_code in (400, 403):
                            break

            except ExternalServiceError:
                raise
            except Exception as e:
                last_error = str(e)
                logger.warning(f"BizMessage attempt {attempt} failed: {e}")
                if attempt < retry_count:
                    await asyncio.sleep(1)

        raise ExternalServiceError(f"비즈메시지 친구톡 전송 실패 ({retry_count}회 시도): {last_error}")

    async def send_channel_message(
        self,
        channel_user_key: str,
        message: str,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        채널 구독자에게 메시지 전송 (비즈메시지 친구톡 사용)

        내부적으로 send_bizmessage_friend_talk()를 호출.
        비즈메시지 자격증명(KAKAO_BIZ_CLIENT_ID, KAKAO_BIZ_CLIENT_SECRET, KAKAO_SENDER_KEY)이
        설정된 경우 실제 발송, 미설정 시 channel_pending 상태 반환.

        Args:
            channel_user_key: plusfriendUserKey (채널 사용자 고유 키)
            message: 전송할 메시지 (최대 1000자)
            retry_count: 재시도 횟수
        """
        if self.mock_mode:
            logger.info(
                f"[MOCK] Channel message sent to {channel_user_key[:8]}...",
                extra={"message_preview": message[:50]}
            )
            return {
                "success": True,
                "method": "channel_admin_mock",
                "channel_user_key": channel_user_key,
                "message_length": len(message)
            }

        # 비즈메시지 자격증명 확인
        if not self.biz_client_id or not self.biz_client_secret or not self.sender_key:
            missing = []
            if not self.biz_client_id:
                missing.append("KAKAO_BIZ_CLIENT_ID")
            if not self.biz_client_secret:
                missing.append("KAKAO_BIZ_CLIENT_SECRET")
            if not self.sender_key:
                missing.append("KAKAO_SENDER_KEY")

            logger.warning(
                f"비즈메시지 자격증명 미설정 → channel_pending 처리",
                extra={
                    "missing_settings": missing,
                    "channel_user_key": channel_user_key[:10] + "..."
                }
            )
            return {
                "success": False,
                "method": "channel_pending",
                "channel_user_key": channel_user_key,
                "reason": f"비즈메시지 미설정 ({', '.join(missing)})",
                "action_required": "카카오 i 커넥트 메시지 서비스 가입 후 .env에 자격증명 추가"
            }

        return await self.send_bizmessage_friend_talk(
            plus_friend_user_key=channel_user_key,
            message=message,
            retry_count=retry_count
        )


# ============================================
# 싱글톤 인스턴스
# ============================================

_kakao_instance: Optional[KakaoClient] = None


def get_kakao_client(mock_mode: bool = True) -> KakaoClient:
    """
    KakaoClient 싱글톤 인스턴스 가져오기

    Args:
        mock_mode: Mock 모드 활성화 (기본: True)

    Returns:
        KakaoClient 인스턴스

    Example:
        >>> client = get_kakao_client(mock_mode=True)
        >>> result = await client.send_alimtalk(...)
    """
    global _kakao_instance

    if _kakao_instance is None:
        _kakao_instance = KakaoClient(mock_mode=mock_mode)

    return _kakao_instance
