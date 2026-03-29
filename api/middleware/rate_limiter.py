"""
Redis 기반 슬라이딩 윈도우 Rate Limiter

SPEC §5.3.1: 100 requests/minute per user

구현 방식: Redis Sorted Set 슬라이딩 윈도우
- 키: rate_limit:{identifier}
- Value: timestamp (float)
- Score: timestamp (float)
- TTL: 60초

Author: Memory Garden Team
Created: 2026-02-27
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import time
from typing import Optional, Callable

# ============================================
# 2. Third-Party Imports
# ============================================
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ============================================
# 3. Local Imports
# ============================================
from database.redis_client import redis_client
from config.settings import settings
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
RATE_LIMIT_REQUESTS = getattr(settings, "RATE_LIMIT_REQUESTS", 100)  # 요청 수
RATE_LIMIT_WINDOW = getattr(settings, "RATE_LIMIT_WINDOW", 60)       # 윈도우 (초)
RATE_LIMIT_KEY_PREFIX = "rate_limit:"

# Rate limit 제외 경로 (헬스체크, 정적 파일)
EXEMPT_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static",
    "/firebase-messaging-sw.js",
}


# ============================================
# 6. Rate Limiter 미들웨어
# ============================================

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Redis 슬라이딩 윈도우 Rate Limiter 미들웨어

    사용자당 분당 최대 `RATE_LIMIT_REQUESTS` 요청을 허용합니다.
    초과 시 429 Too Many Requests 반환.

    식별자 우선순위:
    1. X-Kakao-User-Key 헤더 (카카오 채널 사용자)
    2. Authorization Bearer 토큰 해시
    3. 클라이언트 IP

    Example:
        app.add_middleware(RateLimiterMiddleware)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 제외 경로 체크
        path = request.url.path
        if any(path.startswith(exempt) for exempt in EXEMPT_PATHS):
            return await call_next(request)

        # 식별자 추출
        identifier = self._get_identifier(request)

        # Rate limit 체크
        allowed, current_count, retry_after = await self._check_rate_limit(identifier)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded: identifier={identifier[:20]}, "
                f"count={current_count}, path={path}"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {RATE_LIMIT_REQUESTS}/min",
                    "retry_after": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                }
            )

        # 요청 처리
        response = await call_next(request)

        # Rate limit 헤더 추가
        remaining = max(0, RATE_LIMIT_REQUESTS - current_count)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + RATE_LIMIT_WINDOW)

        return response

    def _get_identifier(self, request: Request) -> str:
        """
        요청 식별자 추출.

        우선순위: Kakao-User-Key > Auth token hash > IP
        """
        # 1. 카카오 사용자 키
        kakao_key = request.headers.get("X-Kakao-User-Key")
        if kakao_key:
            return f"kakao:{kakao_key}"

        # 2. Authorization 토큰 (해시)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            # 토큰 해시 (전체 토큰 대신 앞 16자)
            return f"token:{token[:16]}"

        # 3. IP 주소 (Nginx 프록시 뒤에서는 X-Forwarded-For 사용)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def _check_rate_limit(
        self, identifier: str
    ) -> tuple[bool, int, int]:
        """
        슬라이딩 윈도우 Rate Limit 체크.

        Args:
            identifier: 요청 식별자

        Returns:
            (allowed, current_count, retry_after_seconds)
        """
        try:
            redis_conn = await redis_client.get_client()
            if redis_conn is None:
                # Redis 연결 실패 시 허용 (서비스 가용성 우선)
                logger.warning("Redis unavailable, rate limiting skipped")
                return True, 0, 0

            key = f"{RATE_LIMIT_KEY_PREFIX}{identifier}"
            now = time.time()
            window_start = now - RATE_LIMIT_WINDOW

            # 파이프라인으로 원자적 실행
            async with redis_conn.pipeline() as pipe:
                # 윈도우 밖 오래된 요청 제거
                await pipe.zremrangebyscore(key, 0, window_start)
                # 현재 요청 수 조회
                await pipe.zcard(key)
                # 현재 요청 추가
                await pipe.zadd(key, {str(now): now})
                # TTL 설정
                await pipe.expire(key, RATE_LIMIT_WINDOW)
                results = await pipe.execute()

            current_count = results[1]  # zcard 결과

            if current_count >= RATE_LIMIT_REQUESTS:
                # 가장 오래된 요청의 만료까지 남은 시간 계산
                oldest = await redis_conn.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_ts = oldest[0][1]
                    retry_after = max(1, int(RATE_LIMIT_WINDOW - (now - oldest_ts)))
                else:
                    retry_after = RATE_LIMIT_WINDOW
                return False, current_count, retry_after

            return True, current_count + 1, 0

        except Exception as e:
            logger.error(f"Rate limiter error: {e}", exc_info=True)
            # 에러 시 허용 (서비스 가용성 우선)
            return True, 0, 0
