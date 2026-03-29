#!/usr/bin/env python3
"""
Redis 연결 테스트 스크립트

Redis 연결 및 기본 연산 테스트.

Usage:
    python scripts/test_redis_connection.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.redis_client import redis_client
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_redis():
    """Redis 연결 및 기능 테스트"""
    print("=" * 60)
    print("🔍 Redis Connection Test")
    print("=" * 60)

    # 1. 연결 테스트
    print("\n1️⃣ Testing Redis connection...")
    is_connected = await redis_client.check_connection()

    if is_connected:
        print("✅ Redis connection successful!")
    else:
        print("❌ Redis connection failed!")
        return False

    # 2. 기본 연산 테스트 (get/set/delete)
    print("\n2️⃣ Testing basic operations...")
    try:
        # SET
        test_key = "test:hello"
        test_value = "Hello, Redis!"
        await redis_client.set(test_key, test_value, ttl=60)
        print(f"✅ SET: {test_key} = {test_value}")

        # GET
        retrieved = await redis_client.get(test_key)
        assert retrieved == test_value, f"Expected '{test_value}', got '{retrieved}'"
        print(f"✅ GET: {test_key} = {retrieved}")

        # EXISTS
        exists = await redis_client.exists(test_key)
        assert exists == 1, f"Expected 1, got {exists}"
        print(f"✅ EXISTS: {test_key} -> {exists}")

        # TTL
        ttl = await redis_client.ttl(test_key)
        print(f"✅ TTL: {test_key} -> {ttl}s remaining")

        # DELETE
        deleted = await redis_client.delete(test_key)
        assert deleted == 1, f"Expected 1, got {deleted}"
        print(f"✅ DELETE: {test_key} -> {deleted} keys deleted")

    except AssertionError as e:
        print(f"❌ Basic operations test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Basic operations test error: {e}")
        return False

    # 3. JSON 직렬화 테스트
    print("\n3️⃣ Testing JSON serialization...")
    try:
        json_key = "test:json"
        json_data = {
            "name": "John Doe",
            "age": 30,
            "active": True,
            "tags": ["python", "redis", "fastapi"]
        }

        # SET JSON
        await redis_client.set_json(json_key, json_data, ttl=60)
        print(f"✅ SET JSON: {json_key}")

        # GET JSON
        retrieved_json = await redis_client.get_json(json_key)
        assert retrieved_json == json_data, f"JSON mismatch"
        print(f"✅ GET JSON: {json_key} -> {retrieved_json}")

        # Cleanup
        await redis_client.delete(json_key)

    except Exception as e:
        print(f"❌ JSON serialization test failed: {e}")
        return False

    # 4. 세션 관리 테스트
    print("\n4️⃣ Testing session management...")
    try:
        user_id = "test_user_123"
        session_data = {
            "last_message": "안녕하세요",
            "turn": 5,
            "category": "reminiscence",
            "timestamp": datetime.now().isoformat()
        }

        # SET SESSION
        await redis_client.set_session(user_id, session_data, ttl=60)
        print(f"✅ SET SESSION: {user_id}")

        # GET SESSION
        retrieved_session = await redis_client.get_session(user_id)
        assert retrieved_session["turn"] == 5
        print(f"✅ GET SESSION: {user_id} -> turn={retrieved_session['turn']}")

        # DELETE SESSION
        deleted = await redis_client.delete_session(user_id)
        assert deleted is True
        print(f"✅ DELETE SESSION: {user_id}")

        # Verify deletion
        empty_session = await redis_client.get_session(user_id)
        assert empty_session is None
        print(f"✅ VERIFY DELETION: {user_id} -> None")

    except Exception as e:
        print(f"❌ Session management test failed: {e}")
        return False

    # 5. 대화 컨텍스트 테스트
    print("\n5️⃣ Testing context management...")
    try:
        user_id = "test_user_456"
        context_data = {
            "recent_turns": [
                {"role": "user", "message": "안녕하세요"},
                {"role": "bot", "message": "반가워요!"}
            ],
            "current_category": "daily_episodic",
            "next_question": "오늘 점심 뭐 드셨어요?"
        }

        # SET CONTEXT
        await redis_client.set_context(user_id, context_data, ttl=60)
        print(f"✅ SET CONTEXT: {user_id}")

        # GET CONTEXT
        retrieved_context = await redis_client.get_context(user_id)
        assert len(retrieved_context["recent_turns"]) == 2
        print(f"✅ GET CONTEXT: {user_id} -> {len(retrieved_context['recent_turns'])} turns")

        # DELETE CONTEXT
        await redis_client.delete_context(user_id)
        print(f"✅ DELETE CONTEXT: {user_id}")

    except Exception as e:
        print(f"❌ Context management test failed: {e}")
        return False

    # 6. 캐싱 테스트
    print("\n6️⃣ Testing caching...")
    try:
        # 문자열 캐시
        await redis_client.set_cache("test_str", "cached_value", ttl=60)
        str_cache = await redis_client.get_cache("test_str")
        assert str_cache == "cached_value"
        print(f"✅ STRING CACHE: test_str = {str_cache}")

        # 딕셔너리 캐시
        await redis_client.set_cache("test_dict", {"score": 85.5}, ttl=60)
        dict_cache = await redis_client.get_cache("test_dict")
        assert dict_cache["score"] == 85.5
        print(f"✅ DICT CACHE: test_dict = {dict_cache}")

        # Cleanup
        await redis_client.delete("cache:test_str", "cache:test_dict")

    except Exception as e:
        print(f"❌ Caching test failed: {e}")
        return False

    # 7. 성능 테스트 (간단)
    print("\n7️⃣ Testing performance...")
    try:
        import time

        # 100번 SET/GET
        start = time.time()
        for i in range(100):
            await redis_client.set(f"perf:test:{i}", f"value_{i}", ttl=60)
        set_time = time.time() - start

        start = time.time()
        for i in range(100):
            await redis_client.get(f"perf:test:{i}")
        get_time = time.time() - start

        print(f"✅ SET 100 keys: {set_time:.3f}s ({100/set_time:.0f} ops/s)")
        print(f"✅ GET 100 keys: {get_time:.3f}s ({100/get_time:.0f} ops/s)")

        # Cleanup
        keys_to_delete = [f"perf:test:{i}" for i in range(100)]
        await redis_client.delete(*keys_to_delete)

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\n📌 Redis is ready for use!")
    print("   - Session storage: ✅")
    print("   - Context storage: ✅")
    print("   - Caching: ✅")
    print("=" * 60)

    return True


async def cleanup():
    """테스트 후 정리"""
    try:
        await redis_client.close()
        print("\n🧹 Redis connection closed")
    except Exception as e:
        print(f"⚠️  Error during cleanup: {e}")


if __name__ == "__main__":
    try:
        result = asyncio.run(test_redis())
        sys.exit(0 if result else 1)
    finally:
        # asyncio.run이 자동으로 cleanup을 호출하지 않으므로 별도 실행
        asyncio.run(cleanup())
