"""
기억 관리자 (4계층 메모리 통합)

4계층 메모리 시스템 CRUD 관리:
- Layer 1: Session Memory (Redis)
- Layer 2: Episodic Memory (Qdrant)
- Layer 3: Biographical Memory (Qdrant + PostgreSQL)
- Layer 4: Analytical Memory (TimescaleDB)

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import uuid4

# ============================================
# 2. Third-Party Imports
# ============================================

# ============================================
# 3. Local Imports
# ============================================
from database.redis_client import redis_client
from core.memory.memory_extractor import (
    MemoryExtractor,
    MemoryExtractionResult,
    ExtractedMemory,
    ExtractedFact,
    MemoryType,
)
from utils.logger import get_logger
from utils.exceptions import WorkflowError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
SESSION_MEMORY_TTL = 86400  # 24시간
EPISODIC_COLLECTION = "episodic_memory"
BIOGRAPHICAL_COLLECTION = "biographical_memory"


# ============================================
# 6. MemoryManager 클래스
# ============================================

class MemoryManager:
    """기억 관리자 (4계층 통합)

    메모리 CRUD 및 검색 기능 제공.

    Attributes:
        memory_extractor: 기억 추출기

    Example:
        >>> manager = MemoryManager()
        >>> # 저장
        >>> await manager.store_all(
        ...     user_id="user123",
        ...     message="오늘 점심 된장찌개 먹었어요",
        ...     response="맛있게 드셨나요?",
        ...     analysis={"emotion": "neutral"}
        ... )
        >>> # 검색
        >>> memories = await manager.retrieve_all(
        ...     user_id="user123",
        ...     query="점심"
        ... )
    """

    def __init__(
        self,
        memory_extractor: Optional[MemoryExtractor] = None,
        embedder: Optional[Any] = None,
        llm_service: Optional[Any] = None
    ):
        """
        MemoryManager 초기화

        Args:
            memory_extractor: 기억 추출기 (None이면 생성)
            embedder: 임베딩 생성기 (벡터 검색용)
            llm_service: LLM 서비스 (사실 추출용)
        """
        self.memory_extractor = memory_extractor or MemoryExtractor()
        self.embedder = embedder
        self.llm_service = llm_service
        logger.info("MemoryManager initialized")

    # ============================================
    # 통합 저장/검색 메서드
    # ============================================

    async def store_all(
        self,
        user_id: str,
        message: str,
        response: str,
        analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        4계층에 기억 저장 (병렬 실행)

        Args:
            user_id: 사용자 ID
            message: 사용자 메시지
            response: AI 응답
            analysis: 분석 결과 (감정, MCDI 등)

        Returns:
            저장 결과
            {
                "session_stored": True,
                "episodic_stored": 3,
                "biographical_stored": 2,
                "analytical_stored": True
            }

        Example:
            >>> manager = MemoryManager()
            >>> result = await manager.store_all(
            ...     user_id="user123",
            ...     message="딸 이름은 수진이에요",
            ...     response="수진 씨 멋진 이름이네요!",
            ...     analysis={"emotion": "neutral", "mcdi_score": 78.5}
            ... )
        """
        logger.info(f"Storing memories for user {user_id}")

        analysis = analysis or {}

        # 기억 추출
        extraction_result = await self.memory_extractor.extract_from_message(
            user_message=message,
            assistant_message=response,
            context={"emotion": analysis.get("emotion")}
        )

        # 4계층 병렬 저장
        results = await asyncio.gather(
            self._store_session_memory(user_id, message, response),
            self._store_episodic_memories(user_id, extraction_result),
            self._store_biographical_facts(user_id, extraction_result),
            self._store_analytical_data(user_id, analysis),
            return_exceptions=True
        )

        # 결과 집계
        session_result, episodic_result, biographical_result, analytical_result = results

        storage_result = {
            "session_stored": not isinstance(session_result, Exception),
            "episodic_stored": episodic_result if not isinstance(episodic_result, Exception) else 0,
            "biographical_stored": biographical_result if not isinstance(biographical_result, Exception) else 0,
            "analytical_stored": not isinstance(analytical_result, Exception),
            "extraction_summary": extraction_result.summary
        }

        # 에러 로깅
        for i, (layer_name, result) in enumerate(zip(
            ["session", "episodic", "biographical", "analytical"],
            results
        )):
            if isinstance(result, Exception):
                logger.error(f"Failed to store {layer_name} memory: {result}")

        logger.info(
            "Memories stored",
            extra={
                "user_id": user_id,
                **storage_result
            }
        )

        return storage_result

    async def retrieve_all(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        4계층에서 기억 검색 (병렬 실행)

        Args:
            user_id: 사용자 ID
            query: 검색 쿼리 (선택)
            limit: 각 계층별 최대 결과 수

        Returns:
            검색된 기억들
            {
                "session": {...},
                "episodic": [...],
                "biographical": {...},
                "analytical": {...}
            }

        Example:
            >>> manager = MemoryManager()
            >>> memories = await manager.retrieve_all(
            ...     user_id="user123",
            ...     query="점심",
            ...     limit=5
            ... )
        """
        logger.debug(f"Retrieving memories for user {user_id}")

        # 4계층 병렬 검색
        results = await asyncio.gather(
            self._retrieve_session_memory(user_id),
            self._retrieve_episodic_memories(user_id, query, limit),
            self._retrieve_biographical_facts(user_id),
            self._retrieve_analytical_data(user_id, days=30),
            return_exceptions=True
        )

        session_data, episodic_data, biographical_data, analytical_data = results

        # 에러 처리
        memories = {
            "session": session_data if not isinstance(session_data, Exception) else {},
            "episodic": episodic_data if not isinstance(episodic_data, Exception) else [],
            "biographical": biographical_data if not isinstance(biographical_data, Exception) else {},
            "analytical": analytical_data if not isinstance(analytical_data, Exception) else {},
            "user_id": user_id,
            "query": query,
            "retrieved_at": datetime.now().isoformat()
        }

        logger.info(
            "Memories retrieved",
            extra={
                "user_id": user_id,
                "episodic_count": len(memories["episodic"]),
                "biographical_keys": len(memories["biographical"])
            }
        )

        return memories

    # ============================================
    # Layer 1: Session Memory (Redis)
    # ============================================

    async def _store_session_memory(
        self,
        user_id: str,
        message: str,
        response: str
    ) -> bool:
        """Session Memory 저장 (Redis)"""
        try:
            # 현재 세션 가져오기
            session_key = f"session:{user_id}"
            session_data = await redis_client.get_json(session_key) or {
                "user_id": user_id,
                "conversation_history": []
            }

            # 대화 턴 추가
            turn = {
                "timestamp": datetime.now().isoformat(),
                "user": message,
                "assistant": response
            }
            session_data["conversation_history"].append(turn)

            # 최근 10턴만 유지
            if len(session_data["conversation_history"]) > 10:
                session_data["conversation_history"] = session_data["conversation_history"][-10:]

            # Redis에 저장
            await redis_client.set_json(
                session_key,
                session_data,
                ttl=SESSION_MEMORY_TTL
            )

            logger.debug(f"Session memory stored for {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store session memory: {e}")
            raise

    async def _retrieve_session_memory(self, user_id: str) -> Dict[str, Any]:
        """Session Memory 검색 (Redis)"""
        try:
            session_key = f"session:{user_id}"
            session_data = await redis_client.get_json(session_key)
            return session_data or {}

        except Exception as e:
            logger.error(f"Failed to retrieve session memory: {e}")
            return {}

    # ============================================
    # Layer 2: Episodic Memory (Qdrant)
    # ============================================

    async def _store_episodic_memories(
        self,
        user_id: str,
        extraction_result: MemoryExtractionResult
    ) -> int:
        """Episodic Memory 저장 (Qdrant)"""
        try:
            stored_count = 0

            # TODO: Qdrant 연동
            # 현재는 Redis에 임시 저장
            for memory in extraction_result.episodic_memories:
                memory_id = str(uuid4())
                cache_key = f"episodic:{user_id}:{memory_id}"

                memory_data = {
                    "id": memory_id,
                    "user_id": user_id,
                    "content": memory.content,
                    "category": memory.category.value,
                    "confidence": memory.confidence,
                    "importance": memory.importance,
                    "timestamp": memory.timestamp,
                    "metadata": memory.metadata
                }

                await redis_client.set_json(
                    cache_key,
                    memory_data,
                    ttl=86400 * 30  # 30일
                )
                stored_count += 1

            logger.debug(f"Stored {stored_count} episodic memories for {user_id}")
            return stored_count

        except Exception as e:
            logger.error(f"Failed to store episodic memories: {e}")
            raise

    async def _retrieve_episodic_memories(
        self,
        user_id: str,
        query: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Episodic Memory 검색 (Qdrant)"""
        try:
            memories = []

            # TODO: Qdrant 벡터 검색 구현
            # 실제 구현 예시:
            # if query and self.embedder:
            #     # 쿼리 임베딩
            #     query_vector = await self.embedder.embed(query)
            #
            #     # Qdrant 검색
            #     from qdrant_client.models import Filter, FieldCondition
            #     results = qdrant_client.search(
            #         collection_name=EPISODIC_COLLECTION,
            #         query_vector=query_vector,
            #         query_filter=Filter(
            #             must=[FieldCondition(key="user_id", match={"value": user_id})]
            #         ),
            #         limit=limit,
            #         score_threshold=0.7
            #     )
            #
            #     memories = [
            #         {
            #             "content": hit.payload["content"],
            #             "timestamp": hit.payload["timestamp"],
            #             "category": hit.payload.get("category"),
            #             "score": hit.score
            #         }
            #         for hit in results
            #     ]
            # else:
            #     # 쿼리 없이 최근 순으로
            #     results = qdrant_client.scroll(
            #         collection_name=EPISODIC_COLLECTION,
            #         scroll_filter=Filter(
            #             must=[FieldCondition(key="user_id", match={"value": user_id})]
            #         ),
            #         limit=limit,
            #         order_by="timestamp"
            #     )
            #     memories = [point.payload for point in results[0]]

            # 현재는 Redis에서 임시 검색
            logger.debug(f"Retrieved {len(memories)} episodic memories (mock)")

            return memories

        except Exception as e:
            logger.error(f"Failed to retrieve episodic memories: {e}")
            return []

    # ============================================
    # Layer 3: Biographical Memory (Qdrant + PostgreSQL)
    # ============================================

    async def _store_biographical_facts(
        self,
        user_id: str,
        extraction_result: MemoryExtractionResult
    ) -> int:
        """Biographical Memory 저장"""
        try:
            stored_count = 0

            # TODO: PostgreSQL 및 Qdrant 연동
            # 현재는 Redis에 임시 저장
            for fact in extraction_result.biographical_facts:
                cache_key = f"biographical:{user_id}:{fact.entity}"

                fact_data = {
                    "entity": fact.entity,
                    "value": fact.value,
                    "category": fact.category.value,
                    "fact_type": fact.fact_type.value,
                    "confidence": fact.confidence,
                    "context": fact.context,
                    "timestamp": fact.timestamp
                }

                await redis_client.set_json(
                    cache_key,
                    fact_data,
                    ttl=86400 * 365  # 1년
                )
                stored_count += 1

            logger.debug(f"Stored {stored_count} biographical facts for {user_id}")
            return stored_count

        except Exception as e:
            logger.error(f"Failed to store biographical facts: {e}")
            raise

    async def _retrieve_biographical_facts(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Biographical Memory 검색"""
        try:
            # TODO: PostgreSQL 쿼리 구현
            # 현재는 Redis에서 검색 (임시)
            facts = {}

            # Mock data
            logger.debug(f"Retrieved biographical facts for {user_id} (mock)")

            return facts

        except Exception as e:
            logger.error(f"Failed to retrieve biographical facts: {e}")
            return {}

    # ============================================
    # Layer 4: Analytical Memory (TimescaleDB)
    # ============================================

    async def _store_analytical_data(
        self,
        user_id: str,
        analysis: Dict[str, Any]
    ) -> bool:
        """Analytical Memory 저장 (TimescaleDB)"""
        try:
            # TODO: TimescaleDB 연동
            # 현재는 Redis에 임시 저장
            if not analysis:
                return True

            cache_key = f"analytical:{user_id}:{datetime.now().date().isoformat()}"

            analytical_data = {
                "user_id": user_id,
                "date": datetime.now().date().isoformat(),
                "mcdi_score": analysis.get("mcdi_score"),
                "emotion": analysis.get("emotion"),
                "analysis_details": analysis,
                "timestamp": datetime.now().isoformat()
            }

            await redis_client.set_json(
                cache_key,
                analytical_data,
                ttl=86400 * 90  # 90일
            )

            logger.debug(f"Stored analytical data for {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store analytical data: {e}")
            raise

    async def _retrieve_analytical_data(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analytical Memory 검색 (최근 N일)"""
        try:
            analytical_data = {
                "latest_mcdi_score": None,
                "baseline_mean": None,
                "baseline_std": None,
                "recent_scores": [],
                "score_trend": None
            }

            # TODO: TimescaleDB 쿼리 구현
            # 실제 구현 예시:
            # from database.postgres import AsyncSessionLocal
            # from datetime import timedelta
            #
            # cutoff_date = datetime.now() - timedelta(days=days)
            #
            # async with AsyncSessionLocal() as session:
            #     # 최신 MCDI 점수
            #     result = await session.execute(
            #         """
            #         SELECT mcdi_score, lr_score, sd_score, nc_score,
            #                to_score, er_score, rt_score, risk_level, timestamp
            #         FROM analytical_memory
            #         WHERE user_id = :user_id
            #         ORDER BY timestamp DESC
            #         LIMIT 1
            #         """,
            #         {"user_id": user_id}
            #     )
            #     latest = result.fetchone()
            #     if latest:
            #         analytical_data["latest_mcdi_score"] = latest.mcdi_score
            #         analytical_data["latest_analysis"] = {
            #             "mcdi_score": latest.mcdi_score,
            #             "scores": {
            #                 "LR": latest.lr_score,
            #                 "SD": latest.sd_score,
            #                 "NC": latest.nc_score,
            #                 "TO": latest.to_score,
            #                 "ER": latest.er_score,
            #                 "RT": latest.rt_score
            #             },
            #             "risk_level": latest.risk_level,
            #             "timestamp": latest.timestamp.isoformat()
            #         }
            #
            #     # 최근 점수 추이 (시계열)
            #     result = await session.execute(
            #         """
            #         SELECT mcdi_score, timestamp
            #         FROM analytical_memory
            #         WHERE user_id = :user_id
            #           AND timestamp >= :cutoff_date
            #         ORDER BY timestamp ASC
            #         """,
            #         {"user_id": user_id, "cutoff_date": cutoff_date}
            #     )
            #     scores = result.fetchall()
            #     analytical_data["recent_scores"] = [
            #         {
            #             "score": row.mcdi_score,
            #             "timestamp": row.timestamp.isoformat()
            #         }
            #         for row in scores
            #     ]
            #
            #     # Baseline 계산 (첫 2주 평균)
            #     result = await session.execute(
            #         """
            #         SELECT AVG(mcdi_score) as mean, STDDEV(mcdi_score) as std
            #         FROM (
            #             SELECT mcdi_score
            #             FROM analytical_memory
            #             WHERE user_id = :user_id
            #             ORDER BY timestamp ASC
            #             LIMIT 10
            #         ) baseline
            #         """,
            #         {"user_id": user_id}
            #     )
            #     baseline = result.fetchone()
            #     if baseline:
            #         analytical_data["baseline_mean"] = float(baseline.mean) if baseline.mean else None
            #         analytical_data["baseline_std"] = float(baseline.std) if baseline.std else None

            # 현재는 Redis에서 임시 검색
            logger.debug(f"Retrieved analytical data for {user_id} (mock)")

            return analytical_data

        except Exception as e:
            logger.error(f"Failed to retrieve analytical data: {e}")
            return {}

    # ============================================
    # 검색 헬퍼 메서드
    # ============================================

    async def search_memories_by_keyword(
        self,
        user_id: str,
        keyword: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        키워드로 기억 검색

        Args:
            user_id: 사용자 ID
            keyword: 검색 키워드
            limit: 최대 결과 수

        Returns:
            검색된 기억 리스트

        Example:
            >>> manager = MemoryManager()
            >>> results = await manager.search_memories_by_keyword(
            ...     user_id="user123",
            ...     keyword="딸"
            ... )
        """
        logger.debug(f"Searching memories by keyword: {keyword}")

        memories = await self.retrieve_all(user_id, query=keyword, limit=limit)

        # Episodic memories에서 키워드 필터링
        filtered_episodic = [
            mem for mem in memories["episodic"]
            if keyword in mem.get("content", "")
        ]

        return filtered_episodic[:limit]

    async def search_memories_by_time_range(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        시간 범위로 기억 검색

        Args:
            user_id: 사용자 ID
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            검색된 기억 리스트

        Example:
            >>> manager = MemoryManager()
            >>> results = await manager.search_memories_by_time_range(
            ...     user_id="user123",
            ...     start_date=datetime(2025, 2, 1),
            ...     end_date=datetime(2025, 2, 10)
            ... )
        """
        logger.debug(f"Searching memories by time range: {start_date} to {end_date}")

        memories = await self.retrieve_all(user_id)

        # Episodic memories에서 시간 필터링
        filtered_episodic = []
        for mem in memories["episodic"]:
            try:
                mem_time = datetime.fromisoformat(mem.get("timestamp", ""))
                if start_date <= mem_time <= end_date:
                    filtered_episodic.append(mem)
            except:
                continue

        return filtered_episodic

    async def search_memories_by_emotion(
        self,
        user_id: str,
        emotion: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        감정으로 기억 검색

        Args:
            user_id: 사용자 ID
            emotion: 감정 (joy/sadness/anger/fear/surprise/neutral)
            limit: 최대 결과 수

        Returns:
            검색된 감정 기억 리스트

        Example:
            >>> manager = MemoryManager()
            >>> results = await manager.search_memories_by_emotion(
            ...     user_id="user123",
            ...     emotion="joy"
            ... )
        """
        logger.debug(f"Searching memories by emotion: {emotion}")

        memories = await self.retrieve_all(user_id)

        # Episodic memories에서 감정 필터링
        filtered_episodic = [
            mem for mem in memories["episodic"]
            if mem.get("metadata", {}).get("emotion") == emotion
        ]

        return filtered_episodic[:limit]

    async def get_recent_memories(
        self,
        user_id: str,
        days: int = 7,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        최근 N일 기억 조회

        Args:
            user_id: 사용자 ID
            days: 최근 N일
            limit: 최대 결과 수

        Returns:
            최근 기억 리스트 (시간 역순)

        Example:
            >>> manager = MemoryManager()
            >>> results = await manager.get_recent_memories(
            ...     user_id="user123",
            ...     days=7
            ... )
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        memories = await self.search_memories_by_time_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

        # 시간 역순 정렬
        memories.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )

        return memories[:limit]


# ============================================
# 8. Export
# ============================================
__all__ = [
    "MemoryManager",
]

logger.info("Memory manager module loaded")
