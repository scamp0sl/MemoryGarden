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
import httpx
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings
from database.redis_client import redis_client
from database.qdrant_client import (
    qdrant_manager,
    EPISODIC_COLLECTION,
    BIOGRAPHICAL_COLLECTION,
    SCORE_THRESHOLD,
)
from core.nlp.embedder import Embedder
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
            embedder: 임베딩 생성기 (벡터 검색용, None이면 생성)
            llm_service: LLM 서비스 (사실 추출용)
        """
        self.memory_extractor = memory_extractor or MemoryExtractor()
        self.embedder = embedder or Embedder()
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

        # C1-3: 후속 화제 추출
        follow_up_notes = await self._extract_follow_up_topics(message, response)

        # C1-3: analysis에 follow_up_notes 추가
        if follow_up_notes:
            analysis = analysis or {}
            analysis["follow_up_notes"] = follow_up_notes
            logger.debug(f"Extracted {len(follow_up_notes)} follow-up topics")

        # R-5: samantha_emotion 주입 (간단 키워드 매칭, LLM 호출 없음)
        if not analysis.get("samantha_emotion"):
            _emotion_keywords = {
                "기쁨": ["기쁘", "좋아", "행복", "즐겁", "신나", "ㅋㅋ", "ㅎㅎ", "대박"],
                "우울": ["슬프", "우울", "쓸쓸", "외롭", "ㅠㅠ", "ㅜㅜ"],
                "분노": ["화나", "짜증", "속상", "억울", "미치"],
                "불안": ["무섭", "두렵", "걱정"],
                "피곤": ["피곤", "힘들", "지치"],
            }
            for _label, _kws in _emotion_keywords.items():
                if any(kw in message for kw in _kws):
                    analysis["samantha_emotion"] = _label
                    break
            else:
                analysis["samantha_emotion"] = "중립"

        # 4계층 병렬 저장 (C1-2: analysis 전달 for emotion intensity filter)
        results = await asyncio.gather(
            self._store_session_memory(user_id, message, response),
            self._store_episodic_memories(user_id, extraction_result, analysis),
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
    # C1-3: 후속 화제 추출 헬퍼
    # ============================================

    async def _extract_follow_up_topics(
        self,
        user_message: str,
        assistant_message: str
    ) -> List[str]:
        """대화에서 후속 화제 추출 (C1-3)

        다음 패턴에서 후속 화제 추출:
        1. 사용자가 던진 질문 (나중에 답변 가능한 것들)
        2. "다음에", "나중에" 등의 미래 표현이 있는 문맥
        3. 미완성 대화 (단답형 응답 후 확장 가능한 주제)

        Args:
            user_message: 사용자 메시지
            assistant_message: AI 응답

        Returns:
            후속 화제 리스트 (최대 3개)
        """
        import re

        follow_ups = []

        # 패턴 1: 사용자 메시지의 질문식 표현
        # TODO, 물음표 등 포함
        question_patterns = [
            r"(?:할|가고|먹고|보고|하고 싶은|하고 있는)[\s\S]{1,20}",
            r"(?:좋아하는|즐겨하는|자주 가는|자주 하는)[\s\S]{1,20}",
            r"(?:어떻게|언제|어디서|무엇을|누구와)[\s\S]{1,20}",
        ]
        for pattern in question_patterns:
            matches = re.findall(pattern, user_message)
            for match in matches[:2]:  # 패턴당 최대 2개
                cleaned = match.strip(" ?.!,'")
                if len(cleaned) >= 2 and cleaned not in follow_ups:
                    follow_ups.append(cleaned)

        # 패턴 2: 미래 표현 키워드
        future_keywords = ["다음에", "나중에", "다음 번", "곧", "이따가", "내일"]
        for keyword in future_keywords:
            if keyword in user_message or keyword in assistant_message:
                # 키워드 주변 문맥 추출
                idx = max(user_message.find(keyword), assistant_message.find(keyword))
                context = (user_message + " " + assistant_message)[max(0, idx-10):idx+20]
                # 너무 길면 잘라서 저장
                context = context[:30]
                if context and context not in follow_ups:
                    follow_ups.append(f"{keyword} 관련 대화")

        # 패턴 3: 짧은 응답 후 확장 가능한 주제 (사용자 메시지가 20자 이하)
        if len(user_message) <= 20 and len(follow_ups) < 3:
            # 사용자 메시지 자체를 후속 화제로 저장
            cleaned = user_message.strip(" ?.!,'")
            if len(cleaned) >= 2:
                follow_ups.append(f"더 이야기 나누고 싶은 주제: {cleaned}")

        # 최대 3개로 제한
        return follow_ups[:3]

    async def _generate_follow_up_note_async(
        self,
        memory_content: str,
        user_emotion: Optional[str] = None
    ) -> Optional[str]:
        """LLM 기반 후속 추적 메모 생성 (C1)

        Args:
            memory_content: 기억 내용
            user_emotion: 사용자 감정 (선택사항)

        Returns:
            후속 추적 메모 (None 가능)
        """
        try:
            from services.llm_service import default_llm_service

            prompt = f"""다음 사용자 기억을 바탕으로, 추후 대화 시 다시 물어볼 만한 후속 추적 메모를 한 문장으로 작성해주세요.

기억 내용: {memory_content}
사용자 감정: {user_emotion or "정보 없음"}

가이드라인:
- 1문장으로 간결하게
- 구체적인 질문 형태 (예: "OOO에 대해 다시 물어보기")
- 사용자의 감정 상태를 고려한 표현

후속 추적 메모:"""

            llm_service = default_llm_service
            response = await llm_service.call(prompt, max_tokens=100, temperature=0.7)

            # 응답 정리
            note = response.strip(" .\n")
            if note and len(note) >= 5:
                logger.debug(f"Generated follow-up note: {note}")
                return note

            return None

        except Exception as e:
            logger.warning(f"Failed to generate follow-up note: {e}")
            return None

    # ============================================
    # Layer 2: Episodic Memory (Qdrant)
    # ============================================

    async def _store_episodic_memories(
        self,
        user_id: str,
        extraction_result: MemoryExtractionResult,
        analysis: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Episodic Memory 저장

        Qdrant 가용 시: 벡터 임베딩 + Qdrant upsert
        Qdrant 불가 시: Redis 임시 저장 (fallback)
        """
        try:
            if not extraction_result.episodic_memories:
                return 0

            stored_count = 0

            # Qdrant 초기화 (최초 1회 또는 연결이 끊어졌을 때)
            await qdrant_manager.initialize()
            client = qdrant_manager.client

            # C1-2: 감정 벡터에서 valence 추출
            emotion_vector = analysis.get("emotion_vector", {}) if analysis else {}
            valence = emotion_vector.get("v", 0.0)
            valence_intensity = abs(valence)

            # C1-3: 후속 화제 메타데이터
            follow_up_notes = analysis.get("follow_up_notes", []) if analysis else []
            samantha_emotion = analysis.get("samantha_emotion") if analysis else None

            if client is not None:
                # ---- Qdrant 저장 ----
                points = []
                for memory in extraction_result.episodic_memories:
                    # C1-2: 감정 강도 필터
                    if valence_intensity < 0.4 and memory.importance < 0.6:
                        logger.debug(
                            f"Skipped ordinary conversation: valence={valence:.2f}, "
                            f"importance={memory.importance:.2f}"
                        )
                        continue

                    try:
                        vector = await self.embedder.embed(memory.content)
                        point_id = str(uuid4())

                        # C1-1: 서사 강화 필드 추가
                        enhanced_metadata = {
                            "samantha_emotion": samantha_emotion,
                            "follow_up_notes": follow_up_notes,
                            **memory.metadata
                        }

                        points.append(PointStruct(
                            id=point_id,
                            vector=vector.tolist(),
                            payload={
                                "user_id": user_id,
                                "content": memory.content,
                                "category": memory.category.value,
                                "confidence": memory.confidence,
                                "importance": memory.importance,
                                "timestamp": memory.timestamp,
                                "metadata": enhanced_metadata,
                            }
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to embed episodic memory: {e}")

                if points:
                    await client.upsert(
                        collection_name=EPISODIC_COLLECTION,
                        points=points,
                    )
                    stored_count = len(points)
                    logger.debug(
                        f"Stored {stored_count} episodic memories to Qdrant for {user_id}"
                    )

            else:
                # ---- Redis fallback ----
                for memory in extraction_result.episodic_memories:
                    # C1-2: 감정 강도 필터
                    if valence_intensity < 0.4 and memory.importance < 0.6:
                        continue

                    memory_id = str(uuid4())
                    cache_key = f"episodic:{user_id}:{memory_id}"

                    enhanced_metadata = {
                        "samantha_emotion": samantha_emotion,
                        "follow_up_notes": follow_up_notes,
                        **memory.metadata
                    }

                    await redis_client.set_json(
                        cache_key,
                        {
                            "id": memory_id,
                            "user_id": user_id,
                            "content": memory.content,
                            "category": memory.category.value,
                            "confidence": memory.confidence,
                            "importance": memory.importance,
                            "timestamp": memory.timestamp,
                            "metadata": enhanced_metadata,
                        },
                        ttl=86400 * 30,
                    )
                    stored_count += 1
                logger.debug(
                    f"Stored {stored_count} episodic memories to Redis (fallback) for {user_id}"
                )

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
        """
        Episodic Memory 검색

        Qdrant 가용 시:
          - query 있음 → 벡터 유사도 검색 (cosine ≥ SCORE_THRESHOLD)
          - query 없음 → scroll (최근 N개)
        Qdrant 불가 시: 빈 리스트 반환
        """
        try:
            # Qdrant 초기화
            await qdrant_manager.initialize()
            client = qdrant_manager.client
            if client is None:
                logger.debug("Qdrant unavailable, skipping episodic retrieval")
                return []

            user_filter = Filter(
                must=[FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )]
            )

            if query:
                # Qdrant 1.7.4 호환: 직접 REST API 사용
                # (client library 1.17.1와 server 1.7.4의 API 불일치 문제 해결)
                query_vector = await self.embedder.embed(query)

                async with httpx.AsyncClient(timeout=30.0) as http:
                    response = await http.post(
                        f"{settings.QDRANT_URL}/collections/{EPISODIC_COLLECTION}/points/search",
                        json={
                            "vector": query_vector.tolist(),
                            "filter": {
                                "must": [
                                    {"key": "user_id", "match": {"value": user_id}}
                                ]
                            },
                            "limit": limit,
                            "with_payload": True,
                            "score_threshold": SCORE_THRESHOLD
                        }
                    )

                    if response.status_code == 200:
                        search_result = response.json().get("result", [])
                        memories = [
                            {
                                "content": hit.get("payload", {}).get("content", ""),
                                "timestamp": hit.get("payload", {}).get("timestamp", ""),
                                "category": hit.get("payload", {}).get("category"),
                                "confidence": hit.get("payload", {}).get("confidence", 1.0),
                                "importance": hit.get("payload", {}).get("importance", 0.5),
                                "metadata": hit.get("payload", {}).get("metadata", {}),
                                "score": hit.get("score", 1.0),
                            }
                            for hit in search_result
                        ]
                    else:
                        logger.warning(f"Qdrant search failed: {response.status_code}")
                        return []
            else:
                # 쿼리 없이 최근 순으로 scroll
                results, _ = await client.scroll(
                    collection_name=EPISODIC_COLLECTION,
                    scroll_filter=user_filter,
                    limit=limit,
                    with_payload=True,
                )
                memories = [
                    {
                        "content": p.payload.get("content", ""),
                        "timestamp": p.payload.get("timestamp", ""),
                        "category": p.payload.get("category"),
                        "confidence": p.payload.get("confidence", 1.0),
                        "importance": p.payload.get("importance", 0.5),
                        "metadata": p.payload.get("metadata", {}),
                    }
                    for p in results
                ]
                # timestamp 역순 정렬 (최신 우선)
                memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            logger.debug(f"Retrieved {len(memories)} episodic memories for {user_id}")
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
        """
        Biographical Memory 저장

        Qdrant: 의미 검색용 벡터 저장 (entity+value 임베딩)
        Redis: 빠른 키-값 조회용 캐시 (entity 기준)
        """
        try:
            if not extraction_result.biographical_facts:
                return 0

            stored_count = 0

            # Qdrant 초기화
            await qdrant_manager.initialize()
            client = qdrant_manager.client

            for fact in extraction_result.biographical_facts:
                fact_data = {
                    "user_id": user_id,
                    "entity": fact.entity,
                    "value": fact.value,
                    "category": fact.category.value,
                    "fact_type": fact.fact_type.value,
                    "confidence": fact.confidence,
                    "context": fact.context,
                    "timestamp": fact.timestamp,
                }

                # Redis에 항상 저장 (빠른 조회)
                cache_key = f"biographical:{user_id}:{fact.entity}"
                await redis_client.set_json(
                    cache_key,
                    fact_data,
                    ttl=86400 * 365,  # 1년
                )

                # Qdrant에도 저장 (의미 검색)
                if client is not None:
                    try:
                        embed_text = f"{fact.entity}: {fact.value}"
                        vector = await self.embedder.embed(embed_text)
                        point_id = str(uuid4())
                        await client.upsert(
                            collection_name=BIOGRAPHICAL_COLLECTION,
                            points=[PointStruct(
                                id=point_id,
                                vector=vector.tolist(),
                                payload=fact_data,
                            )],
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to store biographical fact to Qdrant: {e}"
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
        """
        Biographical Memory 검색

        Redis에서 해당 사용자의 모든 biographical 키를 가져옵니다.
        """
        try:
            facts = {}

            # Redis에서 패턴 매칭으로 검색
            pattern = f"biographical:{user_id}:*"
            keys = await redis_client.keys(pattern)

            for key in keys:
                fact_data = await redis_client.get_json(key)
                if fact_data:
                    entity = fact_data.get("entity", "")
                    facts[entity] = fact_data

            logger.debug(f"Retrieved {len(facts)} biographical facts for {user_id}")
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

    async def get_mcdi_analytics(
        self,
        user_id: str,
        days: int = 14
    ) -> Dict[str, Any]:
        """
        MCDI 분석 데이터 조회 (어댑티브 대화용)

        최신 MCDI 점수, 위험도, 6개 지표 점수, 추이 등을 반환.

        Args:
            user_id: 사용자 ID
            days: 조회 기간 (기본 14일)

        Returns:
            {
                "latest_risk_level": "GREEN",
                "latest_mcdi_score": 78.5,
                "score_trend": "stable",  # improving, stable, declining
                "slope_per_week": -0.5,
                "latest_scores": {
                    "LR": 80.0, "SD": 75.0, "NC": 82.0,
                    "TO": 78.0, "ER": 76.0, "RT": 70.0
                },
                "has_data": True
            }

        Example:
            >>> manager = MemoryManager()
            >>> analytics = await manager.get_mcdi_analytics("user123")
            >>> print(analytics["latest_risk_level"])
            'GREEN'
        """
        logger.debug(f"Retrieving MCDI analytics for user {user_id} (last {days} days)")

        analytics_data = {
            "latest_risk_level": "GREEN",
            "latest_mcdi_score": None,
            "score_trend": "stable",
            "slope_per_week": 0.0,
            "latest_scores": {},
            "has_data": False
        }

        try:
            # TimescaleDB에서 최신 MCDI 데이터 조회
            from database.timescale import get_timescale
            timescale = await get_timescale()

            # 최신 분석 결과 조회
            latest_result = await timescale.get_latest_mcdi(user_id)

            if latest_result:
                analytics_data["latest_risk_level"] = latest_result.get("risk_level", "GREEN")
                analytics_data["latest_mcdi_score"] = latest_result.get("mcdi_score")
                analytics_data["latest_scores"] = {
                    "LR": latest_result.get("lr_score"),
                    "SD": latest_result.get("sd_score"),
                    "NC": latest_result.get("nc_score"),
                    "TO": latest_result.get("to_score"),
                    "ER": latest_result.get("er_score"),
                    "RT": latest_result.get("rt_score")
                }
                analytics_data["has_data"] = True

                # 최근 N일 점수 추이 계산
                recent_scores = await timescale.get_mcdi_history(user_id, days=days)
                if len(recent_scores) >= 2:
                    # 단순 선형 회귀로 추이 추정 (첫 점수 vs 마지막 점수)
                    first_score = recent_scores[0].get("mcdi_score", 0)
                    last_score = recent_scores[-1].get("mcdi_score", 0)

                    if last_score > first_score + 2:
                        analytics_data["score_trend"] = "improving"
                    elif last_score < first_score - 2:
                        analytics_data["score_trend"] = "declining"

                    # 주당 변화율 (slope)
                    days_span = max(1, days)  # 0으로 나누기 방지
                    analytics_data["slope_per_week"] = round(
                        (last_score - first_score) / days_span * 7, 2
                    )

                logger.info(
                    f"MCDI analytics retrieved for {user_id}",
                    extra={
                        "risk_level": analytics_data["latest_risk_level"],
                        "mcdi_score": analytics_data["latest_mcdi_score"],
                        "trend": analytics_data["score_trend"]
                    }
                )
            else:
                logger.debug(f"No MCDI data found for user {user_id}")

        except Exception as e:
            logger.warning(f"Failed to retrieve MCDI analytics for {user_id}: {e}")

        return analytics_data


# ============================================
# 8. Export
# ============================================
__all__ = [
    "MemoryManager",
]

logger.info("Memory manager module loaded")
