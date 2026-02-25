"""
카카오 OAuth 2.0 인증 엔드포인트

사용자 카카오 로그인 및 액세스 토큰 관리.
친구톡 전송에 필요한 사용자 인증 처리.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional
from pydantic import BaseModel
import httpx

from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import ExternalServiceError

logger = get_logger(__name__)

router = APIRouter(prefix="/kakao/oauth", tags=["kakao-oauth"])


# ============================================
# Pydantic 모델
# ============================================

class FriendTalkRequest(BaseModel):
    """친구톡 전송 요청"""
    user_key: str
    message: str


# ============================================
# 임시 토큰 저장소 (개발용)
# TODO: Redis 또는 DB로 교체
# ============================================
_token_storage = {}


@router.get("/login")
async def kakao_login(user_id: Optional[str] = Query(None)):
    """
    카카오 로그인 시작

    사용자를 카카오 로그인 페이지로 리다이렉트.

    Args:
        user_id: Memory Garden 사용자 ID (선택, state로 전달)

    Returns:
        카카오 로그인 페이지로 리다이렉트

    Example:
        브라우저에서 접속:
        https://n8n.softline.co.kr/kakao/oauth/login?user_id=user123
    """
    logger.info(f"OAuth login initiated for user: {user_id}")

    # 카카오 인증 URL 생성
    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={settings.KAKAO_REST_API_KEY}"
        f"&redirect_uri=https://n8n.softline.co.kr/kakao/oauth/callback"
        f"&response_type=code"
    )

    # state 파라미터 추가 (CSRF 방지 + user_id 전달)
    if user_id:
        auth_url += f"&state={user_id}"

    logger.debug(f"Redirecting to: {auth_url}")

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def kakao_callback(
    code: str = Query(..., description="카카오 인증 코드"),
    state: Optional[str] = Query(None, description="사용자 ID")
):
    """
    카카오 OAuth 콜백

    카카오 로그인 후 code를 받아 access_token으로 교환.

    Args:
        code: 카카오 인증 코드
        state: 사용자 ID (선택)

    Returns:
        {
            "success": True,
            "user_id": "user123",
            "access_token": "xxx",
            "expires_in": 21599,
            "message": "카카오 로그인 성공!"
        }

    Raises:
        HTTPException: 토큰 교환 실패 시
    """
    logger.info(f"OAuth callback received for user: {state}")

    try:
        # ============================================
        # 1. code → access_token 교환
        # ============================================
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://kauth.kakao.com/oauth/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.KAKAO_REST_API_KEY,
                    "client_secret": settings.KAKAO_CLIENT_SECRET,  # ✅ Client Secret 추가
                    "redirect_uri": "https://n8n.softline.co.kr/kakao/oauth/callback",
                    "code": code
                },
                timeout=10.0
            )

            token_response.raise_for_status()
            token_data = token_response.json()

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data["expires_in"]

        logger.info(
            "Access token obtained",
            extra={
                "user_id": state,
                "expires_in": expires_in,
                "has_refresh_token": refresh_token is not None
            }
        )

        # ============================================
        # 2. 사용자 정보 조회 (선택)
        # ============================================
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                timeout=10.0
            )

            user_response.raise_for_status()
            user_data = user_response.json()

        kakao_id = user_data["id"]
        kakao_account = user_data.get("kakao_account", {})

        logger.info(
            "User info retrieved",
            extra={
                "kakao_id": kakao_id,
                "has_email": "email" in kakao_account
            }
        )

        # ============================================
        # 3. 토큰 저장 (임시 - 메모리)
        # TODO: Redis 또는 PostgreSQL로 교체
        # ============================================
        user_id = state or f"kakao_{kakao_id}"

        _token_storage[user_id] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "kakao_id": kakao_id,
            "kakao_account": kakao_account
        }

        logger.info(f"Token stored for user: {user_id}")

        # ============================================
        # 4. 성공 응답
        # ============================================
        return JSONResponse(
            content={
                "success": True,
                "user_id": user_id,
                "kakao_id": kakao_id,
                "access_token": access_token[:20] + "...",  # 일부만 표시
                "expires_in": expires_in,
                "message": "✅ 카카오 로그인 성공! 이제 친구톡을 보낼 수 있습니다."
            }
        )

    except httpx.HTTPStatusError as e:
        logger.error(
            f"OAuth token exchange failed: {e}",
            extra={
                "status_code": e.response.status_code,
                "response": e.response.text
            }
        )

        raise HTTPException(
            status_code=500,
            detail=f"카카오 인증 실패: {e.response.text}"
        )

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"인증 처리 실패: {str(e)}"
        )


@router.get("/token/{user_id}")
async def get_token(user_id: str, full: bool = False):
    """
    사용자 액세스 토큰 조회

    Args:
        user_id: Memory Garden 사용자 ID
        full: 전체 토큰 반환 여부 (기본: False)

    Returns:
        {
            "user_id": "user123",
            "access_token": "xxx..." or "full_token",
            "expires_in": 21599,
            "kakao_id": 1234567890
        }

    Raises:
        HTTPException: 토큰 없음
    """
    if user_id not in _token_storage:
        raise HTTPException(
            status_code=404,
            detail=f"토큰 없음. 먼저 /kakao/oauth/login으로 로그인하세요."
        )

    token_data = _token_storage[user_id]

    return {
        "user_id": user_id,
        "access_token": token_data["access_token"] if full else token_data["access_token"][:20] + "...",
        "expires_in": token_data["expires_in"],
        "kakao_id": token_data["kakao_id"]
    }


@router.delete("/token/{user_id}")
async def revoke_token(user_id: str):
    """
    액세스 토큰 삭제 (로그아웃)

    Args:
        user_id: Memory Garden 사용자 ID

    Returns:
        {"success": True, "message": "로그아웃 완료"}
    """
    if user_id in _token_storage:
        del _token_storage[user_id]
        logger.info(f"Token revoked for user: {user_id}")

    return {
        "success": True,
        "message": "로그아웃 완료"
    }


# ============================================
# 헬퍼 함수
# ============================================

def get_access_token(user_id: str) -> Optional[str]:
    """
    사용자 액세스 토큰 가져오기

    Args:
        user_id: Memory Garden 사용자 ID

    Returns:
        액세스 토큰 또는 None

    Example:
        >>> from api.routes.kakao_oauth import get_access_token
        >>> token = get_access_token("user123")
        >>> if token:
        ...     await kakao_client.send_friend_talk(user_key, message, token)
    """
    token_data = _token_storage.get(user_id)
    return token_data["access_token"] if token_data else None


def has_valid_token(user_id: str) -> bool:
    """
    유효한 토큰 존재 여부

    Args:
        user_id: Memory Garden 사용자 ID

    Returns:
        토큰 존재 여부
    """
    return user_id in _token_storage


@router.post("/send-friend-talk/{user_id}")
async def send_friend_talk(
    user_id: str,
    request: FriendTalkRequest
):
    """
    친구톡 전송 (저장된 액세스 토큰 사용)

    Args:
        user_id: Memory Garden 사용자 ID
        request: 친구톡 전송 요청 (user_key, message)

    Request Body:
        {
            "user_key": "AkBzAKRCUoEn",
            "message": "안녕하세요! ..."
        }

    Returns:
        {
            "success": True,
            "message_id": "...",
            "user_key": "...",
            ...
        }

    Raises:
        HTTPException: 토큰 없음 또는 전송 실패
    """
    from services.kakao_client import KakaoClient

    # 액세스 토큰 가져오기
    access_token = get_access_token(user_id)

    if not access_token:
        raise HTTPException(
            status_code=404,
            detail=f"토큰 없음. 먼저 /kakao/oauth/login으로 로그인하세요."
        )

    try:
        # 친구톡 전송
        client = KakaoClient(mock_mode=False)

        result = await client.send_friend_talk(
            user_key=request.user_key,
            message=request.message,
            access_token=access_token
        )

        logger.info(
            "Friend talk sent successfully",
            extra={
                "user_id": user_id,
                "user_key": request.user_key,
                "message_length": len(request.message)
            }
        )

        return result

    except Exception as e:
        logger.error(f"Friend talk send failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"친구톡 전송 실패: {str(e)}"
        )
