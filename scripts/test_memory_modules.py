#!/usr/bin/env python3
"""
Memory 모듈 테스트 스크립트

MemoryExtractor, MemoryManager, ContextBuilder 테스트.

Usage:
    python scripts/test_memory_modules.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.memory import (
    MemoryExtractor,
    MemoryManager,
    ContextBuilder,
    MemoryType,
    FactType,
    EntityCategory,
)
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_memory_extractor():
    """MemoryExtractor 테스트"""
    print("=" * 60)
    print("🔍 MemoryExtractor Test")
    print("=" * 60)

    extractor = MemoryExtractor()

    # 테스트 대화
    conversation_history = [
        {"role": "user", "content": "오늘 점심에 딸이랑 같이 된장찌개 먹었어요"},
        {"role": "assistant", "content": "딸분과 함께 식사하셨군요! 맛있게 드셨나요?"},
        {"role": "user", "content": "네, 딸 이름은 수진이에요. 고향은 부산이고요"},
        {"role": "assistant", "content": "수진 씨 멋진 이름이네요! 부산 좋은 곳이죠"}
    ]

    print("\n1️⃣ Extract from Conversation")
    try:
        result = await extractor.extract(
            conversation_history=conversation_history,
            current_emotion="joy"
        )

        print(f"✅ Extraction completed")
        print(f"   - Episodic memories: {len(result.episodic_memories)}")
        print(f"   - Biographical facts: {len(result.biographical_facts)}")
        print(f"   - Emotional memories: {len(result.emotional_memories)}")
        print(f"   - Summary: {result.summary}")

        # 상세 출력
        if result.biographical_facts:
            print("\n   📋 Biographical Facts:")
            for fact in result.biographical_facts:
                print(f"      - {fact.entity}: {fact.value} (confidence: {fact.confidence:.2f})")

        if result.episodic_memories:
            print("\n   📝 Episodic Memories:")
            for memory in result.episodic_memories[:3]:  # 최대 3개
                print(f"      - {memory.content[:50]}... (importance: {memory.importance:.2f})")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n2️⃣ Extract from Single Message")
    try:
        result = await extractor.extract_from_message(
            user_message="고향은 부산이고, 좋아하는 음식은 된장찌개예요",
            assistant_message="부산 출신이시군요! 된장찌개 정말 맛있죠",
            context={"emotion": "neutral"}
        )

        print(f"✅ Extracted from single message")
        print(f"   - Facts: {len(result.biographical_facts)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n3️⃣ Calculate Importance Score")
    if result.episodic_memories:
        memory = result.episodic_memories[0]
        importance = extractor.calculate_importance(memory)
        print(f"✅ Importance calculated: {importance:.3f}")

    print("\n" + "=" * 60)
    return True


async def test_memory_manager():
    """MemoryManager 테스트"""
    print("\n" + "=" * 60)
    print("🔍 MemoryManager Test")
    print("=" * 60)

    manager = MemoryManager()
    test_user_id = "test_user_memory"

    print("\n1️⃣ Store Memories")
    try:
        result = await manager.store_all(
            user_id=test_user_id,
            message="오늘 점심에 딸 수진이랑 된장찌개 먹었어요",
            response="수진 씨와 함께 식사하셨군요! 맛있게 드셨나요?",
            analysis={
                "emotion": "joy",
                "mcdi_score": 78.5,
                "lr_score": 80.0
            }
        )

        print(f"✅ Memories stored:")
        print(f"   - Session: {result['session_stored']}")
        print(f"   - Episodic: {result['episodic_stored']} items")
        print(f"   - Biographical: {result['biographical_stored']} items")
        print(f"   - Analytical: {result['analytical_stored']}")
        print(f"   - Summary: {result['extraction_summary']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n2️⃣ Retrieve All Memories")
    try:
        memories = await manager.retrieve_all(
            user_id=test_user_id,
            query="점심"
        )

        print(f"✅ Memories retrieved:")
        print(f"   - Session data: {bool(memories['session'])}")
        print(f"   - Episodic: {len(memories['episodic'])} items")
        print(f"   - Biographical: {len(memories['biographical'])} facts")
        print(f"   - Retrieved at: {memories['retrieved_at']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n3️⃣ Search by Keyword")
    try:
        results = await manager.search_memories_by_keyword(
            user_id=test_user_id,
            keyword="딸",
            limit=5
        )

        print(f"✅ Search results: {len(results)} items")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n4️⃣ Search by Time Range")
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        results = await manager.search_memories_by_time_range(
            user_id=test_user_id,
            start_date=start_date,
            end_date=end_date
        )

        print(f"✅ Time range search: {len(results)} items (last 7 days)")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n5️⃣ Search by Emotion")
    try:
        results = await manager.search_memories_by_emotion(
            user_id=test_user_id,
            emotion="joy",
            limit=5
        )

        print(f"✅ Emotion search (joy): {len(results)} items")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n6️⃣ Get Recent Memories")
    try:
        results = await manager.get_recent_memories(
            user_id=test_user_id,
            days=7,
            limit=10
        )

        print(f"✅ Recent memories (7 days): {len(results)} items")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 60)
    return True


async def test_context_builder():
    """ContextBuilder 테스트"""
    print("\n" + "=" * 60)
    print("🔍 ContextBuilder Test")
    print("=" * 60)

    # 먼저 기억 저장
    manager = MemoryManager()
    test_user_id = "test_user_context"

    print("\n0️⃣ Setup: Store test memories")
    await manager.store_all(
        user_id=test_user_id,
        message="딸 수진이가 오늘 전화했어요. 고향은 부산이에요.",
        response="수진 씨가 전화하셨군요! 좋으셨겠어요",
        analysis={"emotion": "joy"}
    )
    print("✅ Test memories stored")

    builder = ContextBuilder(memory_manager=manager)

    print("\n1️⃣ Build Context")
    try:
        context = await builder.build_context(
            user_id=test_user_id,
            query="딸",
            current_emotion="joy",
            max_memories=5
        )

        print(f"✅ Context built:")
        print(f"   - Relevant memories: {len(context['relevant_memories'])}")
        print(f"   - Biographical facts: {len(context['biographical_facts'])}")
        print(f"   - Recent conversation: {len(context['recent_conversation'])}")
        print(f"   - Built at: {context['built_at']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n2️⃣ Build Prompt Context")
    try:
        context_str = await builder.build_prompt_context(
            user_id=test_user_id,
            query="점심"
        )

        print(f"✅ Prompt context generated ({len(context_str)} chars)")
        print(f"\n   Preview:")
        print("   " + "\n   ".join(context_str.split("\n")[:10]))
        if len(context_str.split("\n")) > 10:
            print("   ...")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n3️⃣ Get Conversation Context")
    try:
        history = await builder.get_conversation_context(
            user_id=test_user_id,
            last_n_turns=3
        )

        print(f"✅ Conversation context: {len(history)} messages")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n4️⃣ Build Enriched Context")
    try:
        enriched_context = await builder.build_enriched_context(
            user_id=test_user_id,
            user_message="오늘 점심에 딸이랑 같이 밥 먹었어요",
            current_emotion="joy"
        )

        print(f"✅ Enriched context built:")
        print(f"   - Query extracted: {enriched_context['query']}")
        print(f"   - Memories: {len(enriched_context['relevant_memories'])}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 60)
    return True


async def test_integration():
    """통합 테스트 (전체 플로우)"""
    print("\n" + "=" * 60)
    print("🔍 Integration Test (Full Flow)")
    print("=" * 60)

    test_user_id = "test_user_integration"

    # 1. MemoryManager 생성
    manager = MemoryManager()

    # 2. 여러 대화 저장
    print("\n1️⃣ Store Multiple Conversations")
    conversations = [
        ("오늘 점심은 된장찌개 먹었어요", "맛있게 드셨나요?", {"emotion": "neutral"}),
        ("딸 수진이가 전화했어요", "수진 씨 연락 주셨군요!", {"emotion": "joy"}),
        ("고향은 부산이에요", "부산 좋은 곳이죠!", {"emotion": "neutral"}),
    ]

    for i, (msg, resp, analysis) in enumerate(conversations, 1):
        await manager.store_all(
            user_id=test_user_id,
            message=msg,
            response=resp,
            analysis=analysis
        )
        print(f"   ✅ Conversation {i} stored")

    # 3. ContextBuilder로 컨텍스트 구성
    print("\n2️⃣ Build Context for Next Response")
    builder = ContextBuilder(memory_manager=manager)

    context = await builder.build_context(
        user_id=test_user_id,
        query="딸",
        current_emotion="joy"
    )

    print(f"✅ Context built for next response")
    print(f"   - Total memories: {len(context['relevant_memories'])}")

    # 4. 포맷팅된 컨텍스트 출력
    print("\n3️⃣ Formatted Context Preview")
    formatted = context["formatted_context"]
    print(formatted[:300] if formatted else "(empty)")

    print("\n" + "=" * 60)
    return True


async def main():
    """메인 테스트 실행"""
    print("\n")
    print("=" * 60)
    print("🚀 Memory Modules Test Suite")
    print("=" * 60)

    try:
        # 1. MemoryExtractor 테스트
        extractor_success = await test_memory_extractor()

        # 2. MemoryManager 테스트
        manager_success = await test_memory_manager()

        # 3. ContextBuilder 테스트
        context_success = await test_context_builder()

        # 4. 통합 테스트
        integration_success = await test_integration()

        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"  MemoryExtractor: {'✅ PASS' if extractor_success else '❌ FAIL'}")
        print(f"  MemoryManager: {'✅ PASS' if manager_success else '❌ FAIL'}")
        print(f"  ContextBuilder: {'✅ PASS' if context_success else '❌ FAIL'}")
        print(f"  Integration Test: {'✅ PASS' if integration_success else '❌ FAIL'}")
        print("=" * 60)

        all_success = all([
            extractor_success,
            manager_success,
            context_success,
            integration_success
        ])

        if all_success:
            print("\n✅ All tests passed!")
            print("\n📌 Next steps:")
            print("   1. Integrate Qdrant for vector storage")
            print("   2. Integrate PostgreSQL for biographical facts")
            print("   3. Integrate TimescaleDB for analytical data")
            print("   4. Integrate with core/workflow/message_processor.py")
            print("=" * 60)
            return True
        else:
            print("\n⚠️  Some tests failed. Check logs for details.")
            return False

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
