"""
카카오 토큰 관리 태스크

모든 사용자의 카카오 액세스 토큰 상태를 주기적으로 점검하고,
만료 임박 또는 만료된 토큰을 리프레시 토큰을 사용하여 자동으로 갱신합니다.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx
from sqlalchemy import select, and_

from database.postgres import AsyncSessionLocal
from database.models import User
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

async def check_and_refresh_all_tokens() -> Dict[str, Any]:
    """
    모든 활성 사용자의 카카오 토큰 점검 및 자동 갱신
    
    새벽 시간에 매일 1회 실행되는 것을 권장합니다.
    """
    logger.info("🔍 [TokenManagement] Starting all-user token check...")
    
    now = datetime.now()
    # 24시간 이내에 만료될 예정이거나 이미 만료된 토큰 대상 (좀 더 넉넉하게 잡음)
    threshold = now + timedelta(hours=24)
    
    async with AsyncSessionLocal() as db:
        # 탈퇴하지 않고 온보딩이 진행된 사용자 중 OAuth 토큰이 있는 대상
        query = select(User).where(
            and_(
                User.deleted_at == None,
                User.onboarding_day >= 1,
                User.kakao_refresh_token != None
            )
        )
        result = await db.execute(query)
        users = result.scalars().all()
        
        total_count = len(users)
        success_count = 0
        fail_count = 0
        skipped_count = 0
        permanent_fail_count = 0
        
        for user in users:
            # 1. 갱신 필요 여부 확인
            needs_refresh = False
            if not user.kakao_token_expires_at or user.kakao_token_expires_at <= threshold:
                needs_refresh = True
                
            if not needs_refresh:
                skipped_count += 1
                continue
                
            # 2. 리프레시 토큰 만료 여부 확인
            if user.kakao_refresh_token_expires_at and user.kakao_refresh_token_expires_at <= now:
                logger.warning(f"❌ [TokenManagement] Refresh token expired for user {user.kakao_id} ({user.name})")
                permanent_fail_count += 1
                continue
                
            # 3. 토큰 갱신 시도
            try:
                # auth.py에 있는 내부 갱신 로직 활용 (HTTP POST 호출하거나 직접 로직 구현)
                # 여기서는 가급적 중앙화된 갱신 엔드포인트를 호출하여 로직 중복 방지
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 로컬 서버의 refresh 엔드포인트 호출
                    refresh_url = f"http://localhost:8002/api/v1/auth/kakao/refresh/{user.kakao_id}"
                    resp = await client.post(refresh_url)
                    
                    if resp.status_code == 200:
                        success_count += 1
                        logger.info(f"✅ [TokenManagement] Successfully refreshed token for {user.kakao_id}")
                    else:
                        fail_count += 1
                        logger.error(f"❌ [TokenManagement] Failed to refresh for {user.kakao_id}: {resp.status_code} {resp.text}")
            except Exception as e:
                fail_count += 1
                logger.error(f"⚠️ [TokenManagement] Error during refresh for {user.kakao_id}: {e}")
                
        summary = {
            "total": total_count,
            "refreshed": success_count,
            "failed": fail_count,
            "skipped": skipped_count,
            "expired_refresh_token": permanent_fail_count,
            "timestamp": now.isoformat()
        }
        
        logger.info(f"📊 [TokenManagement] Check complete: {summary}")
        return summary
