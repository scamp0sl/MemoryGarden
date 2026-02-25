"""
텍스트 임베딩 생성기

OpenAI Embeddings API를 사용하여 텍스트를 벡터로 변환합니다.
의미적 유사도 계산에 사용됩니다.

Scientific Basis:
    - Embedding Dimension: 1536 (OpenAI text-embedding-3-small)
    - Cosine Similarity: 의미적 거리 측정에 사용
    - Normalization: L2 정규화로 단위 벡터 변환

Usage:
    >>> embedder = Embedder()
    >>> vector = await embedder.embed("안녕하세요")
    >>> print(vector.shape)
    (1536,)

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import asyncio
from typing import Dict, List, Optional
from functools import lru_cache
import hashlib

# ============================================
# 2. Third-Party Imports
# ============================================
import numpy as np
from openai import AsyncOpenAI, OpenAIError, RateLimitError, APIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import MemoryGardenError

# ============================================
# 4. Logger Setup
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. Constants
# ============================================
DEFAULT_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
MAX_RETRIES = 3
CACHE_SIZE = 1000  # LRU cache size


# ============================================
# 6. Custom Exceptions
# ============================================
class EmbeddingError(MemoryGardenError):
    """임베딩 생성 실패"""
    pass


# ============================================
# 7. Embedder Class
# ============================================
class Embedder:
    """
    텍스트 임베딩 생성기

    OpenAI text-embedding-3-small 모델 사용.
    1536차원 벡터 생성 및 L2 정규화.

    Attributes:
        client: AsyncOpenAI 클라이언트
        model: 임베딩 모델명
        dimension: 벡터 차원수
        _cache: 임베딩 캐시 (메모리 절약)

    Example:
        >>> embedder = Embedder()
        >>> vec1 = await embedder.embed("봄에는 쑥을 뜯으러 갑니다")
        >>> vec2 = await embedder.embed("여름에는 해수욕을 갑니다")
        >>> similarity = np.dot(vec1, vec2)
        >>> print(f"Similarity: {similarity:.3f}")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        dimension: int = EMBEDDING_DIMENSION
    ):
        """
        초기화

        Args:
            api_key: OpenAI API 키 (None이면 settings에서 가져옴)
            model: 임베딩 모델명
            dimension: 벡터 차원수
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self.dimension = dimension

        # AsyncOpenAI 클라이언트 생성
        self.client = AsyncOpenAI(api_key=self.api_key)

        # 캐시 초기화 (텍스트 해시 → 벡터)
        self._cache: Dict[str, np.ndarray] = {}

        logger.info(
            f"Embedder initialized",
            extra={
                "model": self.model,
                "dimension": self.dimension,
                "cache_size": CACHE_SIZE
            }
        )

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def embed(
        self,
        text: str,
        normalize: bool = True
    ) -> np.ndarray:
        """
        텍스트를 벡터로 변환

        Args:
            text: 임베딩할 텍스트
            normalize: L2 정규화 여부 (코사인 유사도 계산 시 필수)

        Returns:
            1536차원 numpy 배열

        Raises:
            EmbeddingError: 임베딩 생성 실패 시

        Example:
            >>> embedder = Embedder()
            >>> vector = await embedder.embed("안녕하세요")
            >>> print(vector.shape)
            (1536,)
            >>> print(np.linalg.norm(vector))  # L2 norm
            1.0
        """
        if not text or not text.strip():
            raise EmbeddingError("Text cannot be empty")

        # 텍스트 정규화
        text = text.strip()

        # 캐시 확인
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for text: {text[:50]}...")
            return self._cache[cache_key]

        try:
            logger.debug(f"Generating embedding for text: {text[:50]}...")

            # OpenAI API 호출
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimension
            )

            # 벡터 추출
            embedding = response.data[0].embedding
            vector = np.array(embedding, dtype=np.float32)

            # L2 정규화 (코사인 유사도 계산용)
            if normalize:
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm

            # 캐시 저장 (LRU 방식)
            self._update_cache(cache_key, vector)

            logger.debug(
                f"Embedding generated successfully",
                extra={
                    "text_length": len(text),
                    "vector_norm": float(np.linalg.norm(vector)),
                    "cache_size": len(self._cache)
                }
            )

            return vector

        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise  # tenacity가 재시도

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise  # tenacity가 재시도

        except OpenAIError as e:
            logger.error(f"OpenAI error: {e}", exc_info=True)
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise EmbeddingError(f"Unexpected embedding error: {e}") from e

    async def embed_batch(
        self,
        texts: List[str],
        normalize: bool = True
    ) -> List[np.ndarray]:
        """
        여러 텍스트를 병렬로 임베딩

        Args:
            texts: 임베딩할 텍스트 리스트
            normalize: L2 정규화 여부

        Returns:
            벡터 리스트

        Example:
            >>> embedder = Embedder()
            >>> texts = ["안녕하세요", "반갑습니다", "좋은 하루"]
            >>> vectors = await embedder.embed_batch(texts)
            >>> print(len(vectors))
            3
        """
        if not texts:
            return []

        logger.info(f"Batch embedding {len(texts)} texts")

        # 병렬 처리
        tasks = [self.embed(text, normalize) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 에러 처리
        vectors = []
        failed_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to embed text {i}: {result}")
                failed_count += 1
                vectors.append(None)
            else:
                vectors.append(result)

        if failed_count > 0:
            logger.warning(
                f"Batch embedding completed with {failed_count} failures"
            )

        return vectors

    def calculate_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray
    ) -> float:
        """
        두 벡터 간 코사인 유사도 계산

        Args:
            vec1: 첫 번째 벡터 (L2 정규화 필수)
            vec2: 두 번째 벡터 (L2 정규화 필수)

        Returns:
            -1.0 ~ 1.0 사이의 유사도
            (1.0에 가까울수록 유사함)

        Example:
            >>> vec1 = await embedder.embed("봄에는 꽃이 핍니다")
            >>> vec2 = await embedder.embed("가을에는 단풍이 듭니다")
            >>> similarity = embedder.calculate_similarity(vec1, vec2)
            >>> print(f"Similarity: {similarity:.3f}")
            0.687
        """
        # 정규화된 벡터라면 dot product = cosine similarity
        similarity = float(np.dot(vec1, vec2))

        # -1 ~ 1 범위로 클리핑 (부동소수점 오차 대응)
        similarity = max(-1.0, min(1.0, similarity))

        return similarity

    def _get_cache_key(self, text: str) -> str:
        """
        캐시 키 생성 (SHA256 해시)

        Args:
            text: 원본 텍스트

        Returns:
            해시 문자열
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _update_cache(self, key: str, vector: np.ndarray) -> None:
        """
        LRU 캐시 업데이트

        Args:
            key: 캐시 키
            vector: 저장할 벡터
        """
        # 캐시 크기 제한
        if len(self._cache) >= CACHE_SIZE:
            # 가장 오래된 항목 제거 (FIFO 방식으로 단순화)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = vector

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        캐시 통계

        Returns:
            {
                "size": 현재 캐시 크기,
                "max_size": 최대 캐시 크기
            }
        """
        return {
            "size": len(self._cache),
            "max_size": CACHE_SIZE
        }


# ============================================
# 8. Utility Functions
# ============================================
async def get_embedder() -> Embedder:
    """
    싱글톤 Embedder 인스턴스 반환

    FastAPI dependency injection에서 사용.

    Returns:
        Embedder 인스턴스
    """
    if not hasattr(get_embedder, "_instance"):
        get_embedder._instance = Embedder()

    return get_embedder._instance
