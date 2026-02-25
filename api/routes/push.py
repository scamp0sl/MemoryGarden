"""
푸시 알림 API 엔드포인트

FCM 토큰 등록/관리 및 푸시 알림 테스트.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime

from database.postgres import get_db
from database.models import FCMToken, User
from services.firebase_service import get_firebase_service
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/push", tags=["push"])


# ============================================
# Pydantic 스키마
# ============================================

class FCMTokenRegister(BaseModel):
    """FCM 토큰 등록 요청"""
    user_id: str = Field(..., description="사용자 ID")
    token: str = Field(..., description="FCM 등록 토큰")
    device_type: str = Field(..., description="기기 타입", pattern="^(android|ios|web)$")
    device_id: Optional[str] = Field(None, description="기기 고유 ID")
    device_name: Optional[str] = Field(None, description="기기 이름")


class PushTestRequest(BaseModel):
    """푸시 알림 테스트 요청"""
    user_id: str = Field(..., description="사용자 ID")
    title: str = Field(..., description="알림 제목")
    body: str = Field(..., description="알림 내용")
    deep_link: Optional[str] = Field(None, description="딥링크 URL")


# ============================================
# API 엔드포인트
# ============================================

@router.post("/register", status_code=201)
async def register_fcm_token(
    request: FCMTokenRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    FCM 토큰 등록

    사용자의 FCM 푸시 토큰을 등록합니다.
    동일한 토큰이 이미 존재하면 업데이트합니다.

    Args:
        request: 토큰 등록 정보

    Returns:
        {
            "success": True,
            "token_id": 1,
            "user_id": "...",
            "message": "FCM token registered successfully"
        }

    Example:
        POST /api/v1/push/register
        {
            "user_id": "user_123",
            "token": "fcm_token_here...",
            "device_type": "android",
            "device_name": "Samsung Galaxy S21"
        }
    """
    try:
        # 사용자 존재 확인 (UUID 변환)
        from uuid import UUID
        try:
            user_uuid = UUID(request.user_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid user_id format. Must be a valid UUID."
            )

        result = await db.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()

        if not user:
            # 웹 사용자 자동 생성
            user = User(
                id=user_uuid,
                kakao_id=f"web_{user_uuid}",  # 고유한 kakao_id
                name=f"Web User ({request.device_name})"  # 디바이스 이름 포함
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            logger.info(
                f"✅ New web user created: {user_uuid}",
                extra={
                    "user_id": str(user_uuid),
                    "device_type": request.device_type,
                    "device_name": request.device_name
                }
            )

        # 기존 토큰 확인
        result = await db.execute(
            select(FCMToken).where(FCMToken.token == request.token)
        )
        existing_token = result.scalar_one_or_none()

        if existing_token:
            # 토큰 업데이트
            existing_token.user_id = user_uuid
            existing_token.device_type = request.device_type
            existing_token.device_id = request.device_id
            existing_token.device_name = request.device_name
            existing_token.is_active = True
            existing_token.last_used_at = datetime.now()
            existing_token.updated_at = datetime.now()

            await db.commit()

            logger.info(
                f"FCM token updated for user: {request.user_id}",
                extra={"token_id": existing_token.id, "device_type": request.device_type}
            )

            return {
                "success": True,
                "token_id": existing_token.id,
                "user_id": request.user_id,
                "message": "FCM token updated successfully"
            }

        # 새 토큰 등록
        new_token = FCMToken(
            user_id=user_uuid,
            token=request.token,
            device_type=request.device_type,
            device_id=request.device_id,
            device_name=request.device_name,
            is_active=True,
            last_used_at=datetime.now()
        )

        db.add(new_token)
        await db.commit()
        await db.refresh(new_token)

        logger.info(
            f"FCM token registered for user: {request.user_id}",
            extra={"token_id": new_token.id, "device_type": request.device_type}
        )

        return {
            "success": True,
            "token_id": new_token.id,
            "user_id": request.user_id,
            "message": "FCM token registered successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FCM token registration failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register FCM token: {str(e)}"
        )


@router.get("/tokens/{user_id}")
async def get_user_tokens(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 FCM 토큰 조회

    Args:
        user_id: 사용자 ID

    Returns:
        {
            "user_id": "...",
            "tokens": [
                {
                    "id": 1,
                    "token": "...",
                    "device_type": "android",
                    "device_name": "Samsung Galaxy S21",
                    "is_active": true,
                    "last_used_at": "2025-02-23T10:00:00"
                }
            ]
        }
    """
    try:
        from uuid import UUID
        user_uuid = UUID(user_id)

        result = await db.execute(
            select(FCMToken)
            .where(FCMToken.user_id == user_uuid)
            .where(FCMToken.is_active == True)
        )
        tokens = result.scalars().all()

        return {
            "user_id": user_id,
            "tokens": [
                {
                    "id": token.id,
                    "token": token.token[:20] + "...",  # 보안상 일부만 표시
                    "device_type": token.device_type,
                    "device_name": token.device_name,
                    "is_active": token.is_active,
                    "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None
                }
                for token in tokens
            ]
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        logger.error(f"Failed to get tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tokens/{token_id}")
async def delete_fcm_token(
    token_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    FCM 토큰 삭제

    Args:
        token_id: 토큰 ID

    Returns:
        {"success": True, "message": "FCM token deleted successfully"}
    """
    try:
        result = await db.execute(
            delete(FCMToken).where(FCMToken.id == token_id)
        )

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"FCM token not found: {token_id}"
            )

        await db.commit()

        logger.info(f"FCM token deleted: {token_id}")

        return {
            "success": True,
            "message": "FCM token deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete token: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_push_notification(
    request: PushTestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    푸시 알림 테스트

    사용자의 모든 활성 기기에 테스트 알림 전송.

    Args:
        request: 테스트 알림 정보

    Returns:
        {
            "success": True,
            "sent_count": 2,
            "failed_count": 0,
            "message": "Push notifications sent successfully"
        }

    Example:
        POST /api/v1/push/test
        {
            "user_id": "user_123",
            "title": "Memory Garden 🌱",
            "body": "테스트 알림입니다!",
            "deep_link": "kakaotalk://talk/chat/_ZeUTxl"
        }
    """
    try:
        from uuid import UUID
        user_uuid = UUID(request.user_id)

        # 사용자의 활성 토큰 조회
        result = await db.execute(
            select(FCMToken)
            .where(FCMToken.user_id == user_uuid)
            .where(FCMToken.is_active == True)
        )
        tokens = result.scalars().all()

        if not tokens:
            raise HTTPException(
                status_code=404,
                detail=f"No active FCM tokens found for user: {request.user_id}"
            )

        # Firebase 서비스
        firebase_service = get_firebase_service()

        # 각 토큰에 전송
        sent_count = 0
        failed_count = 0

        for token in tokens:
            try:
                await firebase_service.send_push_notification(
                    token=token.token,
                    title=request.title,
                    body=request.body,
                    deep_link=request.deep_link
                )
                sent_count += 1

                # last_used_at 업데이트
                token.last_used_at = datetime.now()

            except Exception as e:
                logger.error(f"Failed to send to token {token.id}: {e}")
                failed_count += 1

                # 토큰 무효화
                if "unregistered" in str(e).lower():
                    token.is_active = False

        await db.commit()

        return {
            "success": True,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "message": f"Push notifications sent to {sent_count} device(s)"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Push test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
