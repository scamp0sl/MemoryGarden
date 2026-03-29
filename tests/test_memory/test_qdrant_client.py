"""
QdrantManager 및 메모리 저장/검색 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np


# ============================================
# Test 1: QdrantManager 초기화
# ============================================

@pytest.mark.asyncio
async def test_qdrant_manager_init_success():
    """Qdrant 정상 연결 → client 반환"""
    from database.qdrant_client import QdrantManager

    manager = QdrantManager()

    mock_client = AsyncMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])
    mock_client.create_collection = AsyncMock()
    mock_client.create_payload_index = AsyncMock()

    with patch("database.qdrant_client.AsyncQdrantClient", return_value=mock_client):
        result = await manager.initialize()

    assert result is True
    print("✅ Qdrant init success")


@pytest.mark.asyncio
async def test_qdrant_manager_init_failure():
    """Qdrant 연결 실패 → graceful degradation (client=None)"""
    from database.qdrant_client import QdrantManager

    manager = QdrantManager()

    with patch(
        "database.qdrant_client.AsyncQdrantClient",
        side_effect=Exception("Connection refused")
    ):
        result = await manager.initialize()

    assert result is False
    assert manager.client is None
    print("✅ Qdrant init failure → graceful degradation")


@pytest.mark.asyncio
async def test_qdrant_manager_existing_collections():
    """컬렉션이 이미 있으면 create_collection 호출 안 함"""
    from database.qdrant_client import (
        QdrantManager, EPISODIC_COLLECTION, BIOGRAPHICAL_COLLECTION
    )

    manager = QdrantManager()

    existing_col = MagicMock()
    existing_col.name = EPISODIC_COLLECTION
    existing_col2 = MagicMock()
    existing_col2.name = BIOGRAPHICAL_COLLECTION

    mock_client = AsyncMock()
    mock_client.get_collections.return_value = MagicMock(
        collections=[existing_col, existing_col2]
    )
    mock_client.create_collection = AsyncMock()

    with patch("database.qdrant_client.AsyncQdrantClient", return_value=mock_client):
        await manager.initialize()

    mock_client.create_collection.assert_not_called()
    print("✅ Existing collections skipped")


# ============================================
# Test 2: _store_episodic_memories (Qdrant 경로)
# ============================================

@pytest.mark.asyncio
async def test_store_episodic_memories_qdrant():
    """에피소딕 메모리 Qdrant 저장"""
    from core.memory.memory_manager import MemoryManager
    from core.memory.memory_extractor import (
        MemoryExtractionResult, ExtractedMemory, MemoryType, EntityCategory
    )
    from datetime import datetime

    mock_memory = MagicMock(spec=ExtractedMemory)
    mock_memory.content = "오늘 된장찌개를 먹었어요"
    mock_memory.category = MagicMock()
    mock_memory.category.value = "episodic"
    mock_memory.confidence = 0.9
    mock_memory.importance = 0.7
    mock_memory.timestamp = datetime.now().isoformat()
    mock_memory.metadata = {}

    extraction = MagicMock(spec=MemoryExtractionResult)
    extraction.episodic_memories = [mock_memory]
    extraction.biographical_facts = []

    mock_embedder = AsyncMock()
    mock_embedder.embed = AsyncMock(return_value=np.zeros(1536, dtype=np.float32))

    mock_qdrant_client = AsyncMock()
    mock_qdrant_client.upsert = AsyncMock()

    with patch("core.memory.memory_manager.qdrant_manager") as mock_mgr:
        mock_mgr.client = mock_qdrant_client

        manager = MemoryManager(embedder=mock_embedder)
        count = await manager._store_episodic_memories("user_123", extraction)

    assert count == 1
    mock_qdrant_client.upsert.assert_called_once()
    print(f"✅ Episodic stored to Qdrant: {count}")


@pytest.mark.asyncio
async def test_store_episodic_memories_redis_fallback():
    """Qdrant 없으면 Redis에 저장"""
    from core.memory.memory_manager import MemoryManager
    from core.memory.memory_extractor import MemoryExtractionResult, ExtractedMemory
    from datetime import datetime

    mock_memory = MagicMock(spec=ExtractedMemory)
    mock_memory.content = "오늘 산책을 했어요"
    mock_memory.category = MagicMock()
    mock_memory.category.value = "episodic"
    mock_memory.confidence = 0.8
    mock_memory.importance = 0.6
    mock_memory.timestamp = datetime.now().isoformat()
    mock_memory.metadata = {}

    extraction = MagicMock(spec=MemoryExtractionResult)
    extraction.episodic_memories = [mock_memory]
    extraction.biographical_facts = []

    mock_embedder = AsyncMock()

    with patch("core.memory.memory_manager.qdrant_manager") as mock_mgr, \
         patch("core.memory.memory_manager.redis_client") as mock_redis:

        mock_mgr.client = None  # Qdrant 없음
        mock_redis.set_json = AsyncMock(return_value=True)

        manager = MemoryManager(embedder=mock_embedder)
        count = await manager._store_episodic_memories("user_123", extraction)

    assert count == 1
    mock_redis.set_json.assert_called_once()
    print(f"✅ Episodic stored to Redis (fallback): {count}")


# ============================================
# Test 3: _retrieve_episodic_memories (Qdrant 경로)
# ============================================

@pytest.mark.asyncio
async def test_retrieve_episodic_with_query():
    """쿼리 있을 때 벡터 검색"""
    from core.memory.memory_manager import MemoryManager

    mock_hit = MagicMock()
    mock_hit.payload = {
        "content": "된장찌개를 먹었어요",
        "timestamp": "2026-02-27T10:00:00",
        "category": "episodic",
        "confidence": 0.9,
        "importance": 0.7,
        "metadata": {},
    }
    mock_hit.score = 0.85

    mock_qdrant_client = AsyncMock()
    mock_qdrant_client.search = AsyncMock(return_value=[mock_hit])

    mock_embedder = AsyncMock()
    mock_embedder.embed = AsyncMock(return_value=np.zeros(1536, dtype=np.float32))

    with patch("core.memory.memory_manager.qdrant_manager") as mock_mgr:
        mock_mgr.client = mock_qdrant_client

        manager = MemoryManager(embedder=mock_embedder)
        results = await manager._retrieve_episodic_memories("user_123", "된장찌개", 5)

    assert len(results) == 1
    assert results[0]["content"] == "된장찌개를 먹었어요"
    assert results[0]["score"] == 0.85
    print(f"✅ Episodic retrieved with query: {len(results)}")


@pytest.mark.asyncio
async def test_retrieve_episodic_no_query():
    """쿼리 없을 때 scroll (최근순)"""
    from core.memory.memory_manager import MemoryManager

    mock_point = MagicMock()
    mock_point.payload = {
        "content": "산책을 했어요",
        "timestamp": "2026-02-27T09:00:00",
        "category": "episodic",
        "confidence": 0.8,
        "importance": 0.6,
        "metadata": {},
    }

    mock_qdrant_client = AsyncMock()
    mock_qdrant_client.scroll = AsyncMock(return_value=([mock_point], None))

    mock_embedder = AsyncMock()

    with patch("core.memory.memory_manager.qdrant_manager") as mock_mgr:
        mock_mgr.client = mock_qdrant_client

        manager = MemoryManager(embedder=mock_embedder)
        results = await manager._retrieve_episodic_memories("user_123", None, 10)

    assert len(results) == 1
    assert results[0]["content"] == "산책을 했어요"
    print(f"✅ Episodic retrieved without query: {len(results)}")


@pytest.mark.asyncio
async def test_retrieve_episodic_no_qdrant():
    """Qdrant 없으면 빈 리스트"""
    from core.memory.memory_manager import MemoryManager

    mock_embedder = AsyncMock()

    with patch("core.memory.memory_manager.qdrant_manager") as mock_mgr:
        mock_mgr.client = None

        manager = MemoryManager(embedder=mock_embedder)
        results = await manager._retrieve_episodic_memories("user_123", "test", 5)

    assert results == []
    print("✅ No Qdrant → empty list returned")


# ============================================
# Test 4: _retrieve_biographical_facts
# ============================================

@pytest.mark.asyncio
async def test_retrieve_biographical_from_redis():
    """Redis에서 biographical 조회"""
    from core.memory.memory_manager import MemoryManager

    mock_embedder = AsyncMock()
    mock_redis_conn = AsyncMock()
    mock_redis_conn.keys = AsyncMock(return_value=[b"biographical:user_123:daughter_name"])

    with patch("core.memory.memory_manager.qdrant_manager") as mock_mgr, \
         patch("core.memory.memory_manager.redis_client") as mock_redis:

        mock_mgr.client = None
        mock_redis.get_client = AsyncMock(return_value=mock_redis_conn)
        mock_redis.get_json = AsyncMock(return_value={
            "entity": "daughter_name",
            "value": "수진",
            "category": "person",
        })

        manager = MemoryManager(embedder=mock_embedder)
        facts = await manager._retrieve_biographical_facts("user_123")

    assert "daughter_name" in facts
    assert facts["daughter_name"]["value"] == "수진"
    print(f"✅ Biographical from Redis: {list(facts.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
