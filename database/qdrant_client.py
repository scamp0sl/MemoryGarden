"""
Qdrant 벡터 DB 클라이언트

에피소딕/전기적 메모리 컬렉션 관리 및 싱글톤 클라이언트 제공.

Collections:
    - episodic_memory: 일화적 기억 (사건, 감정, 대화 내용)
    - biographical_memory: 전기적 사실 (이름, 가족, 거주지 등)

Author: Memory Garden Team
Created: 2026-02-27
"""

from typing import Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
    CreateCollection,
)

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ============================================
# 컬렉션 상수
# ============================================
EPISODIC_COLLECTION = "episodic_memory"
BIOGRAPHICAL_COLLECTION = "biographical_memory"
VECTOR_SIZE = 1536          # OpenAI text-embedding-3-small
SCORE_THRESHOLD = 0.35      # 유사도 최소값 (에피소딕 검색 - 키워드 단답형 매칭 지원)


# ============================================
# QdrantManager 클래스
# ============================================

class QdrantManager:
    """
    Qdrant 비동기 클라이언트 싱글톤

    컬렉션 초기화 및 클라이언트 접근을 담당합니다.
    서버 연결 불가 시 graceful degradation (None 반환).

    Example:
        >>> manager = QdrantManager.get_instance()
        >>> await manager.initialize()
        >>> client = manager.client  # AsyncQdrantClient or None
    """

    _instance: Optional["QdrantManager"] = None
    _client: Optional[AsyncQdrantClient] = None
    _initialized: bool = False

    @classmethod
    def get_instance(cls) -> "QdrantManager":
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def client(self) -> Optional[AsyncQdrantClient]:
        return self._client

    async def initialize(self) -> bool:
        """
        클라이언트 연결 및 컬렉션 초기화

        Returns:
            True: 초기화 성공
            False: 연결 실패 (graceful degradation)
        """
        if self._initialized:
            return self._client is not None

        try:
            qdrant_url = settings.QDRANT_URL
            api_key = settings.QDRANT_API_KEY or None

            self._client = AsyncQdrantClient(
                url=qdrant_url,
                api_key=api_key,
                timeout=10,
            )

            # 연결 테스트
            await self._client.get_collections()

            # 컬렉션 초기화 (없으면 생성)
            await self._ensure_collections()

            self._initialized = True
            logger.info(
                f"✅ Qdrant connected: {qdrant_url}",
                extra={"url": qdrant_url}
            )
            return True

        except Exception as e:
            logger.warning(
                f"⚠️  Qdrant unavailable, using Redis fallback: {e}"
            )
            self._client = None
            self._initialized = True
            return False

    async def _ensure_collections(self) -> None:
        """필요한 컬렉션이 없으면 생성 (idempotent)"""
        existing = await self._client.get_collections()
        existing_names = {c.name for c in existing.collections}

        for name in [EPISODIC_COLLECTION, BIOGRAPHICAL_COLLECTION]:
            if name not in existing_names:
                await self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
                # user_id 필드에 인덱스 추가 (필터 성능 향상)
                await self._client.create_payload_index(
                    collection_name=name,
                    field_name="user_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                logger.info(f"✅ Created Qdrant collection: {name}")
            else:
                logger.debug(f"Collection already exists: {name}")

    async def is_available(self) -> bool:
        """Qdrant 사용 가능 여부 확인"""
        if not self._initialized:
            await self.initialize()
        return self._client is not None

    async def close(self) -> None:
        """클라이언트 종료"""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False
            logger.info("Qdrant client closed")


# ============================================
# 전역 인스턴스
# ============================================
qdrant_manager = QdrantManager.get_instance()


async def get_qdrant_client() -> Optional[AsyncQdrantClient]:
    """
    Qdrant 클라이언트 반환 (FastAPI dependency injection 용)

    Returns:
        AsyncQdrantClient 또는 None (연결 불가 시)
    """
    await qdrant_manager.initialize()
    return qdrant_manager.client
