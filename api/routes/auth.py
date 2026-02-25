"""
카카오 OAuth 인증 라우트

카카오 로그인 → 권한 동의 → 토큰 저장

Author: Claude Code
Created: 2026-02-12
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from datetime import datetime, timedelta
from typing import Dict, Any

# ============================================
# 2. Third-Party Imports
# ============================================
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings
from database.postgres import get_db
from database.models import User
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. Router 설정
# ============================================
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# ============================================
# 1단계: 카카오 로그인 시작
# ============================================
@router.get("/kakao/login")
async def kakao_login():
    """
    카카오 로그인 페이지로 리다이렉트

    사용자가 이 URL을 방문하면:
    1. 카카오 로그인 페이지로 이동
    2. 사용자가 로그인 + 권한 동의
    3. /auth/kakao/callback으로 리다이렉트됨

    Returns:
        RedirectResponse: 카카오 OAuth 페이지로 리다이렉트

    Example:
        브라우저에서 접속:
        http://localhost:8001/api/v1/auth/kakao/login
    """
    kakao_auth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={settings.KAKAO_REST_API_KEY}"
        f"&redirect_uri={settings.KAKAO_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=talk_message,friends"  # 카카오톡 메시지 + 친구목록
    )

    logger.info(f"Redirecting to Kakao OAuth: {kakao_auth_url}")
    return RedirectResponse(url=kakao_auth_url)


# ============================================
# 2단계: 카카오 콜백 처리
# ============================================
@router.get("/kakao/callback")
async def kakao_callback(
    code: str = Query(..., description="인가 코드"),
    db: AsyncSession = Depends(get_db)
):
    """
    카카오 OAuth 콜백 처리

    1. 인가 코드 → 액세스 토큰 교환
    2. 사용자 정보 조회
    3. DB에 저장
    4. 성공 메시지 반환

    Args:
        code: 카카오가 전달한 인가 코드
        db: 데이터베이스 세션

    Returns:
        Dict[str, Any]: 로그인 성공 정보

    Raises:
        HTTPException: OAuth 처리 실패 시
    """
    logger.info(f"Kakao callback received, code: {code[:10]}...")

    try:
        # 2-1. 토큰 발급
        token_response = await _get_kakao_token(code)
        access_token = token_response["access_token"]
        refresh_token = token_response["refresh_token"]
        expires_in = token_response["expires_in"]  # 43199초 (12시간)
        refresh_token_expires_in = token_response["refresh_token_expires_in"]  # 60일

        # 2-2. 사용자 정보 조회
        user_info = await _get_kakao_user_info(access_token)
        kakao_id = str(user_info["id"])
        nickname = user_info.get("kakao_account", {}).get("profile", {}).get("nickname", "사용자")

        logger.info(f"Kakao user authenticated: {kakao_id} ({nickname})")

        # 2-3. DB에 저장 (없으면 생성, 있으면 업데이트)
        result = await db.execute(
            select(User).where(User.kakao_id == kakao_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # 신규 사용자 생성
            user = User(
                kakao_id=kakao_id,
                name=nickname,
                created_at=datetime.now()
            )
            db.add(user)
            logger.info(f"New user created: {kakao_id}")

        # 토큰 업데이트
        user.kakao_access_token = access_token
        user.kakao_refresh_token = refresh_token
        user.kakao_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        user.kakao_refresh_token_expires_at = datetime.now() + timedelta(seconds=refresh_token_expires_in)
        user.updated_at = datetime.now()

        await db.commit()
        await db.refresh(user)

        logger.info(f"User tokens saved: {kakao_id}")

        # 2-4. 자동 스케줄 등록
        from core.dialogue.scheduler import get_scheduler
        from datetime import time

        try:
            scheduler = get_scheduler()
            await scheduler.add_user_schedule(
                user_id=kakao_id,
                schedule_times=[
                    time(9, 0),   # 오전 9시
                    time(14, 0),  # 오후 2시
                    time(19, 0),  # 오후 7시
                ]
            )
            logger.info(f"✅ Auto-scheduled dialogue for {kakao_id}")
            schedule_message = "매일 오전 9시, 오후 2시, 오후 7시에 자동으로 메시지를 받게 됩니다."
        except Exception as e:
            logger.error(f"Failed to auto-schedule for {kakao_id}: {e}")
            schedule_message = "스케줄 등록은 수동으로 진행해주세요."

        # 2-5. 성공 응답
        return {
            "status": "success",
            "message": f"카카오 로그인 완료! {schedule_message}",
            "user_id": kakao_id,
            "nickname": nickname,
            "expires_at": user.kakao_token_expires_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Kakao OAuth callback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth 처리 실패: {e}")


# ============================================
# 3단계: 토큰 갱신 (자동 실행용)
# ============================================
@router.post("/kakao/refresh/{user_id}")
async def refresh_kakao_token(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    액세스 토큰 갱신

    만료 1시간 전에 자동으로 호출되어야 함 (스케줄러 또는 메시지 전송 전)

    Args:
        user_id: 사용자 ID
        db: 데이터베이스 세션

    Returns:
        Dict[str, Any]: 새로운 토큰 정보

    Raises:
        HTTPException: 토큰 갱신 실패 시
    """
    result = await db.execute(
        select(User).where(User.kakao_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.kakao_refresh_token:
        raise HTTPException(
            status_code=404,
            detail="User or refresh token not found"
        )

    try:
        # 토큰 갱신 요청
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.KAKAO_REST_API_KEY,
                    "client_secret": settings.KAKAO_CLIENT_SECRET,
                    "refresh_token": user.kakao_refresh_token
                }
            )
            response.raise_for_status()
            token_data = response.json()

        # DB 업데이트
        user.kakao_access_token = token_data["access_token"]

        # refresh_token이 갱신되었으면 업데이트 (1개월 미만 남았을 때만)
        if "refresh_token" in token_data:
            user.kakao_refresh_token = token_data["refresh_token"]
            user.kakao_refresh_token_expires_at = datetime.now() + timedelta(
                seconds=token_data.get("refresh_token_expires_in", 5184000)
            )

        user.kakao_token_expires_at = datetime.now() + timedelta(
            seconds=token_data.get("expires_in", 43199)
        )
        user.updated_at = datetime.now()

        await db.commit()

        logger.info(f"Token refreshed for user: {user_id}")

        return {
            "status": "success",
            "message": "토큰 갱신 완료",
            "expires_at": user.kakao_token_expires_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Token refresh failed for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"토큰 갱신 실패: {e}")


# ============================================
# Helper Functions
# ============================================
async def _get_kakao_token(code: str) -> Dict[str, Any]:
    """
    인가 코드를 액세스 토큰으로 교환

    Args:
        code: 카카오에서 받은 인가 코드

    Returns:
        Dict[str, Any]: {
            "access_token": "...",
            "refresh_token": "...",
            "expires_in": 43199,
            "refresh_token_expires_in": 5184000
        }

    Raises:
        Exception: 토큰 발급 실패 시
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KAKAO_REST_API_KEY,
                "client_secret": settings.KAKAO_CLIENT_SECRET,  # 2024년부터 필수!
                "redirect_uri": settings.KAKAO_REDIRECT_URI,
                "code": code
            }
        )
        response.raise_for_status()
        return response.json()


async def _get_kakao_user_info(access_token: str) -> Dict[str, Any]:
    """
    액세스 토큰으로 사용자 정보 조회

    Args:
        access_token: 카카오 액세스 토큰

    Returns:
        Dict[str, Any]: {
            "id": 123456789,
            "kakao_account": {
                "profile": {
                    "nickname": "닉네임",
                    "profile_image_url": "..."
                }
            }
        }

    Raises:
        Exception: 사용자 정보 조회 실패 시
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
        response.raise_for_status()
        return response.json()
