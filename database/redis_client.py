"""
Redis 연결 클라이언트

세션 캐싱 및 대화 컨텍스트 임시 저장용.
redis.asyncio를 사용한 비동기 클라이언트.

Author: Memory Garden Team
Created: 2025-01-15
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import json
from typing import Any, Optional, Dict, List
from datetime import timedelta

# ============================================
# 2. Third-Party Imports
# ============================================
import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import (
    RedisError,
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
)

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
DEFAULT_TTL_SECONDS = 86400  # 24시간
SESSION_TTL_SECONDS = 86400  # 세션: 24시간
CONTEXT_TTL_SECONDS = 3600   # 대화 컨텍스트: 1시간
CACHE_TTL_SECONDS = 1800     # 일반 캐시: 30분

# Redis Key Prefix
KEY_PREFIX_SESSION = "session:"
KEY_PREFIX_CONTEXT = "context:"
KEY_PREFIX_CACHE = "cache:"


# ============================================
# 6. Redis 클라이언트 클래스
# ============================================

class RedisClient:
    """
    Redis 비동기 클라이언트

    Singleton 패턴으로 전역 인스턴스 관리.
    세션 캐싱, 대화 컨텍스트 저장, 일반 캐싱 지원.

    Attributes:
        _instance: Singleton 인스턴스
        _pool: 연결 풀
        _client: Redis 클라이언트

    Example:
        >>> client = RedisClient.get_instance()
        >>> await client.set("key", "value", ttl=3600)
        >>> value = await client.get("key")
        >>> print(value)
        "value"
    """

    _instance: Optional["RedisClient"] = None
    _initialized = False  # 초기화 여부를 확인하는 플래그 추가
    _pool: Optional[ConnectionPool] = None
    _client: Optional[Redis] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        RedisClient 초기화

        Note:
            직접 호출하지 말고 get_instance() 사용
        """
# 이미 초기화되었다면 로직을 타지 않고 바로 반환 - 추가
        if RedisClient._initialized:
            return

        RedisClient._initialized = True

        if RedisClient._instance is not None:
            raise RuntimeError(
                "RedisClient is a singleton. Use get_instance() instead."
            )

# 초기화 완료 표시

    @classmethod
    def get_instance(cls) -> "RedisClient":
        """
        Singleton 인스턴스 반환

        Returns:
            RedisClient: 전역 Redis 클라이언트 인스턴스

        Example:
            >>> client = RedisClient.get_instance()
        """
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
#            cls._instance.__init__()
# 여기서 처음 한 번만 초기화하도록 설정
            cls._instance._initialized = False
#            logger.info("RedisClient singleton instance created")

        if not getattr(cls._instance, "_initialized", False):
# 실제 초기화 수행 (기존 __init__ 내용을 별도 메서드로 빼거나 여기서 처리)
            cls._instance._initialized = True

        logger.info("RedisClient singleton instance created") ##추가

        return cls._instance
    async def ping(self):
        """
        Redis 연결 테스트

        Returns:
            bool: 연결 성공 시 True

        Raises:
            RedisConnectionError: 연결 실패 시
        """
        client = await self.get_client()
        return await client.ping()

    async def get_client(self) -> Redis:
        """
        Redis 클라이언트 반환 (Lazy Loading)

        연결되지 않았으면 자동으로 연결 생성.

        Returns:
            Redis: 비동기 Redis 클라이언트

        Raises:
            RedisConnectionError: 연결 실패 시

        Example:
            >>> client = RedisClient.get_instance()
            >>> redis_conn = await client.get_client()
            >>> await redis_conn.ping()
            True
        """
        if self._client is None:
            try:
                # 연결 풀 생성
                self._pool = ConnectionPool.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=20,  # 최대 연결 수
                    socket_timeout=5.0,  # 소켓 타임아웃 (초)
                    socket_connect_timeout=5.0,  # 연결 타임아웃 (초)
                    retry_on_timeout=True,  # 타임아웃 시 재시도
                )

                # 클라이언트 생성
                self._client = Redis(connection_pool=self._pool)

                # 연결 테스트
                await self._client.ping()

                logger.info(
                    "Redis client connected",
                    extra={
                        "redis_url": settings.REDIS_URL.split("@")[-1],  # 비밀번호 제외
                        "max_connections": 20,
                    }
                )

            except RedisConnectionError as e:
                logger.error(f"Redis connection failed: {e}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Unexpected error creating Redis client: {e}", exc_info=True)
                raise

        return self._client

    # ============================================
    # 7. 기본 연산 (get/set/delete/expire)
    # ============================================

    async def get(self, key: str) -> Optional[str]:
        """
        키의 값 조회

        Args:
            key: Redis 키

        Returns:
            Optional[str]: 값 (없으면 None)

        Example:
            >>> value = await client.get("user:123")
            >>> print(value)
            "John Doe"
        """
        try:
            client = await self.get_client()
            value = await client.get(key)

            if value:
                logger.debug(f"Redis GET: {key} -> found")
            else:
                logger.debug(f"Redis GET: {key} -> not found")

            return value

        except RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {e}", exc_info=True)
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        키에 값 저장

        Args:
            key: Redis 키
            value: 저장할 값
            ttl: TTL (초 단위, None이면 영구)
            nx: True면 키가 없을 때만 저장
            xx: True면 키가 있을 때만 저장

        Returns:
            bool: 성공 여부

        Example:
            >>> await client.set("session:abc123", "data", ttl=3600)
            True
        """
        try:
            client = await self.get_client()

            # 옵션 설정
            kwargs = {}
            if ttl:
                kwargs["ex"] = ttl
            if nx:
                kwargs["nx"] = True
            if xx:
                kwargs["xx"] = True

            result = await client.set(key, value, **kwargs)

            logger.debug(
                f"Redis SET: {key} (ttl={ttl})",
                extra={"nx": nx, "xx": xx}
            )

            return bool(result)

        except RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {e}", exc_info=True)
            return False

    async def delete(self, *keys: str) -> int:
        """
        키 삭제

        Args:
            *keys: 삭제할 키들

        Returns:
            int: 삭제된 키 개수

        Example:
            >>> deleted = await client.delete("key1", "key2", "key3")
            >>> print(deleted)
            3
        """
        try:
            client = await self.get_client()
            result = await client.delete(*keys)

            logger.debug(f"Redis DELETE: {len(keys)} keys, {result} deleted")

            return result

        except RedisError as e:
            logger.error(f"Redis DELETE error: {e}", exc_info=True)
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """
        키의 TTL 설정

        Args:
            key: Redis 키
            ttl: TTL (초 단위)

        Returns:
            bool: 성공 여부

        Example:
            >>> await client.expire("session:abc", 7200)
            True
        """
        try:
            client = await self.get_client()
            result = await client.expire(key, ttl)

            logger.debug(f"Redis EXPIRE: {key} -> {ttl}s")

            return bool(result)

        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}", exc_info=True)
            return False

    async def ttl(self, key: str) -> int:
        """
        키의 남은 TTL 조회

        Args:
            key: Redis 키

        Returns:
            int: 남은 TTL (초), -1이면 영구, -2면 키 없음

        Example:
            >>> remaining = await client.ttl("session:abc")
            >>> print(f"Remaining: {remaining}s")
        """
        try:
            client = await self.get_client()
            result = await client.ttl(key)
            return result

        except RedisError as e:
            logger.error(f"Redis TTL error for key '{key}': {e}", exc_info=True)
            return -2

    async def exists(self, *keys: str) -> int:
        """
        키 존재 여부 확인

        Args:
            *keys: 확인할 키들

        Returns:
            int: 존재하는 키 개수

        Example:
            >>> count = await client.exists("key1", "key2")
            >>> print(f"{count} keys exist")
        """
        try:
            client = await self.get_client()
            result = await client.exists(*keys)
            return result

        except RedisError as e:
            logger.error(f"Redis EXISTS error: {e}", exc_info=True)
            return 0

    async def keys(self, pattern: str) -> List[str]:
        """
        패턴과 일치하는 모든 키 조회

        Args:
            pattern: Redis 패턴 (예: "schedule:*", "session:user_*")

        Returns:
            List[str]: 일치하는 키 목록

        Warning:
            ⚠️  대규모 데이터셋에서는 성능 문제가 발생할 수 있습니다.
            운영 환경에서는 SCAN 사용을 권장합니다.

        Example:
            >>> keys = await client.keys("schedule:*")
            >>> print(f"Found {len(keys)} schedules")
            Found 5 schedules
        """
        try:
            client = await self.get_client()
            result = await client.keys(pattern)

            logger.debug(f"Redis KEYS: {pattern} -> {len(result)} keys found")

            return result

        except RedisError as e:
            logger.error(f"Redis KEYS error for pattern '{pattern}': {e}", exc_info=True)
            return []

    async def scan(
        self,
        cursor: int = 0,
        match: Optional[str] = None,
        count: int = 10
    ) -> tuple[int, List[str]]:
        """
        커서 기반 키 스캔 (KEYS보다 안전)

        Args:
            cursor: 커서 위치 (0부터 시작)
            match: 매칭 패턴 (선택)
            count: 한 번에 가져올 개수 힌트

        Returns:
            (next_cursor, keys): 다음 커서와 키 목록

        Example:
            >>> cursor = 0
            >>> all_keys = []
            >>> while True:
            ...     cursor, keys = await client.scan(cursor, match="schedule:*", count=100)
            ...     all_keys.extend(keys)
            ...     if cursor == 0:
            ...         break
            >>> print(f"Total keys: {len(all_keys)}")
        """
        try:
            client = await self.get_client()
            cursor, keys = await client.scan(cursor=cursor, match=match, count=count)

            logger.debug(
                f"Redis SCAN: cursor={cursor}, match={match}, count={count} -> {len(keys)} keys"
            )

            return cursor, keys

        except RedisError as e:
            logger.error(f"Redis SCAN error: {e}", exc_info=True)
            return 0, []

    # ============================================
    # 8. JSON 직렬화 헬퍼
    # ============================================

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        JSON으로 저장된 값 조회

        Args:
            key: Redis 키

        Returns:
            Optional[Dict]: 파싱된 JSON 객체 (실패 시 None)

        Example:
            >>> data = await client.get_json("user:123:profile")
            >>> print(data["name"])
            "John Doe"
        """
        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
            return None

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key '{key}': {e}", exc_info=True)
            return None

    async def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        딕셔너리를 JSON으로 저장

        Args:
            key: Redis 키
            value: 저장할 딕셔너리
            ttl: TTL (초 단위)

        Returns:
            bool: 성공 여부

        Example:
            >>> await client.set_json(
            ...     "user:123:profile",
            ...     {"name": "John", "age": 30},
            ...     ttl=3600
            ... )
            True
        """
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return await self.set(key, json_str, ttl=ttl)

        except (TypeError, ValueError) as e:
            logger.error(f"JSON encode error for key '{key}': {e}", exc_info=True)
            return False

    # ============================================
    # 9. 세션 관리
    # ============================================

    async def set_session(
        self,
        user_id: str,
        session_data: Dict[str, Any],
        ttl: int = SESSION_TTL_SECONDS
    ) -> bool:
        """
        세션 데이터 저장

        Args:
            user_id: 사용자 ID
            session_data: 세션 데이터
            ttl: TTL (기본 24시간)

        Returns:
            bool: 성공 여부

        Example:
            >>> await client.set_session(
            ...     "user_123",
            ...     {"last_message": "안녕하세요", "turn": 5},
            ...     ttl=86400
            ... )
            True
        """
        key = f"{KEY_PREFIX_SESSION}{user_id}"
        return await self.set_json(key, session_data, ttl=ttl)

    async def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 데이터 조회

        Args:
            user_id: 사용자 ID

        Returns:
            Optional[Dict]: 세션 데이터 (없으면 None)

        Example:
            >>> session = await client.get_session("user_123")
            >>> print(session["turn"])
            5
        """
        key = f"{KEY_PREFIX_SESSION}{user_id}"
        return await self.get_json(key)

    async def delete_session(self, user_id: str) -> bool:
        """
        세션 삭제

        Args:
            user_id: 사용자 ID

        Returns:
            bool: 성공 여부
        """
        key = f"{KEY_PREFIX_SESSION}{user_id}"
        deleted = await self.delete(key)
        return deleted > 0

    # ============================================
    # 10. 대화 컨텍스트 관리
    # ============================================

    async def set_context(
        self,
        user_id: str,
        context_data: Dict[str, Any],
        ttl: int = CONTEXT_TTL_SECONDS
    ) -> bool:
        """
        대화 컨텍스트 저장

        Args:
            user_id: 사용자 ID
            context_data: 컨텍스트 데이터
            ttl: TTL (기본 1시간)

        Returns:
            bool: 성공 여부

        Example:
            >>> await client.set_context(
            ...     "user_123",
            ...     {
            ...         "recent_turns": [...],
            ...         "current_category": "reminiscence",
            ...         "timestamp": "2025-01-15T10:00:00Z"
            ...     }
            ... )
            True
        """
        key = f"{KEY_PREFIX_CONTEXT}{user_id}"
        return await self.set_json(key, context_data, ttl=ttl)

    async def get_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        대화 컨텍스트 조회

        Args:
            user_id: 사용자 ID

        Returns:
            Optional[Dict]: 컨텍스트 데이터 (없으면 None)
        """
        key = f"{KEY_PREFIX_CONTEXT}{user_id}"
        return await self.get_json(key)

    async def delete_context(self, user_id: str) -> bool:
        """
        대화 컨텍스트 삭제

        Args:
            user_id: 사용자 ID

        Returns:
            bool: 성공 여부
        """
        key = f"{KEY_PREFIX_CONTEXT}{user_id}"
        deleted = await self.delete(key)
        return deleted > 0

    # ============================================
    # 11. 일반 캐싱
    # ============================================

    async def set_cache(
        self,
        cache_key: str,
        value: Any,
        ttl: int = CACHE_TTL_SECONDS
    ) -> bool:
        """
        일반 캐시 저장

        Args:
            cache_key: 캐시 키
            value: 캐시할 값 (dict이면 JSON, 아니면 str)
            ttl: TTL (기본 30분)

        Returns:
            bool: 성공 여부

        Example:
            >>> await client.set_cache("mcdi_baseline:user_123", 78.5)
            True
        """
        key = f"{KEY_PREFIX_CACHE}{cache_key}"

        if isinstance(value, dict):
            return await self.set_json(key, value, ttl=ttl)
        else:
            return await self.set(key, str(value), ttl=ttl)

    async def get_cache(self, cache_key: str) -> Optional[Any]:
        """
        일반 캐시 조회

        Args:
            cache_key: 캐시 키

        Returns:
            Optional[Any]: 캐시된 값 (없으면 None)
        """
        key = f"{KEY_PREFIX_CACHE}{cache_key}"

        # JSON 시도
        json_value = await self.get_json(key)
        if json_value is not None:
            return json_value

        # 문자열 시도
        return await self.get(key)

    # ============================================
    # 12. Health Check
    # ============================================

    async def check_connection(self) -> bool:
        """
        Redis 연결 상태 확인

        Returns:
            bool: 연결 성공 여부

        Example:
            >>> is_healthy = await client.check_connection()
            >>> print(f"Redis healthy: {is_healthy}")
            Redis healthy: True
        """
        try:
            client = await self.get_client()
            result = await client.ping()

            if result:
                logger.info("Redis connection check: OK")
                return True
            else:
                logger.warning("Redis connection check: FAILED")
                return False

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Redis connection check failed: {e}", exc_info=True)
            return False

    # ============================================
    # 13. Lifecycle Management
    # ============================================

    async def close(self) -> None:
        """
        Redis 연결 종료

        Note:
            애플리케이션 종료 시 호출
        """
        try:
            if self._client:
                await self._client.close()
                logger.info("Redis client closed")

            if self._pool:
                await self._pool.disconnect()
                logger.info("Redis connection pool closed")

            self._client = None
            self._pool = None

        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}", exc_info=True)
            raise

    async def flush_db(self, async_mode: bool = True) -> bool:
        """
        현재 DB의 모든 키 삭제 (주의!)

        Args:
            async_mode: 비동기 flush 사용 여부

        Returns:
            bool: 성공 여부

        Warning:
            ⚠️  개발/테스트 환경에서만 사용!
            운영 환경에서는 절대 호출하지 마세요.

        Example:
            >>> if settings.APP_ENV == "test":
            ...     await client.flush_db()
        """
        if settings.APP_ENV == "production":
            logger.error("flush_db() called in production environment! Blocked.")
            return False

        try:
            client = await self.get_client()

            if async_mode:
                await client.flushdb(asynchronous=True)
            else:
                await client.flushdb()

            logger.warning("Redis database flushed (all keys deleted)")
            return True

        except RedisError as e:
            logger.error(f"Redis FLUSHDB error: {e}", exc_info=True)
            return False


# ============================================
# 14. 전역 인스턴스
# ============================================

# Singleton 인스턴스 생성
redis_client = RedisClient.get_instance()


# ============================================
# 15. FastAPI Dependency (선택)
# ============================================

async def get_redis() -> Redis:
    """
    FastAPI dependency용 Redis 클라이언트

    Yields:
        Redis: 비동기 Redis 클라이언트

    Example:
        ```python
        from fastapi import Depends

        @app.get("/cache")
        async def get_cache_value(redis: Redis = Depends(get_redis)):
            value = await redis.get("key")
            return {"value": value}
        ```
    """
    return await redis_client.get_client()


# ============================================
# 16. Export
# ============================================
__all__ = [
    "RedisClient",
    "redis_client",
    "get_redis",
    # Constants
    "DEFAULT_TTL_SECONDS",
    "SESSION_TTL_SECONDS",
    "CONTEXT_TTL_SECONDS",
    "CACHE_TTL_SECONDS",
]


logger.info("Redis client module loaded")
