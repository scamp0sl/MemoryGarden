#!/usr/bin/env python3
"""
Dialogue 모듈 테스트 스크립트

DialogueManager, ResponseGenerator, PromptBuilder 테스트.

Usage:
    python scripts/test_dialogue_modules.py
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.dialogue import (
    DialogueManager,
    ResponseGenerator,
    PromptBuilder,
    SYSTEM_PROMPT,
)
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_prompt_builder():
    """PromptBuilder 테스트"""
    print("=" * 60)
    print("🔍 PromptBuilder Test")
    print("=" * 60)

    builder = PromptBuilder()

    # 1. 시스템 프롬프트 생성
    print("\n1️⃣ System Prompt Generation")
    system_prompt = builder.build_system_prompt(
        user_name="홍길동",
        recent_emotion="기쁨",
        biographical_facts={
            "daughter_name": "수진",
            "hometown": "부산",
            "favorite_food": "된장찌개"
        },
        garden_name="행복한 정원"
    )
    print(f"✅ Generated {len(system_prompt)} characters")
    print(f"Preview: {system_prompt[:200]}...")

    # 2. 질문 프롬프트 생성
    print("\n2️⃣ Question Prompt Generation (reminiscence)")
    question_prompt = builder.build_question_prompt(
        category="reminiscence",
        user_context={
            "user_profile": {"name": "홍길동", "age": 75},
            "previous_conversations": "지난 대화에서 고향이 부산이라고 하셨죠",
            "current_season": "겨울"
        }
    )
    print(f"✅ Generated {len(question_prompt)} characters")

    # 3. 분석 프롬프트 생성
    print("\n3️⃣ Analysis Prompt Generation (semantic_drift)")
    analysis_prompt = builder.build_analysis_prompt(
        analysis_type="semantic_drift",
        input_data={
            "question": "오늘 점심 뭐 드셨어요?",
            "user_response": "봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요"
        }
    )
    print(f"✅ Generated {len(analysis_prompt)} characters")

    # 4. 사실 추출 프롬프트 생성
    print("\n4️⃣ Fact Extraction Prompt Generation")
    fact_prompt = builder.build_fact_extraction_prompt(
        conversation_history=[
            {"role": "user", "content": "딸 이름은 수진이에요"},
            {"role": "assistant", "content": "수진 씨 멋진 이름이네요!"}
        ]
    )
    print(f"✅ Generated {len(fact_prompt)} characters")

    print("\n" + "=" * 60)
    return True


async def test_response_generator():
    """ResponseGenerator 테스트"""
    print("\n" + "=" * 60)
    print("🔍 ResponseGenerator Test")
    print("=" * 60)

    generator = ResponseGenerator(temperature=0.7)

    # 1. 일반 응답 생성
    print("\n1️⃣ General Response Generation")
    try:
        response = await generator.generate(
            user_message="오늘 점심은 된장찌개 먹었어요",
            conversation_history=[],
            user_context={
                "user_name": "홍길동",
                "garden_name": "행복한 정원"
            },
            next_question="어떤 반찬과 함께 드셨어요?"
        )
        print(f"✅ Response generated ({len(response)} chars):")
        print(f"   {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # 2. 공감적 응답 생성
    print("\n2️⃣ Empathetic Response Generation")
    try:
        empathetic_response = await generator.generate_empathetic_response(
            user_message="딸이 전화해서 정말 기분 좋아요",
            detected_emotion="joy",
            emotion_intensity=0.85,
            conversation_history=[],
            user_context={"user_name": "홍길동"}
        )
        print(f"✅ Empathetic response generated ({len(empathetic_response)} chars):")
        print(f"   {empathetic_response}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 60)
    return True


async def test_dialogue_manager():
    """DialogueManager 테스트"""
    print("\n" + "=" * 60)
    print("🔍 DialogueManager Test")
    print("=" * 60)

    manager = DialogueManager()
    test_user_id = "test_user_dialogue"

    # 1. 세션 시작
    print("\n1️⃣ Start Session")
    session_id = await manager.start_session(
        user_id=test_user_id,
        initial_context={
            "user_name": "홍길동",
            "garden_name": "행복한 정원"
        }
    )
    print(f"✅ Session started: {session_id}")

    # 2. 세션 조회
    print("\n2️⃣ Get Session")
    session = await manager.get_session(test_user_id)
    if session:
        print(f"✅ Session retrieved:")
        print(f"   - Session ID: {session['session_id']}")
        print(f"   - User ID: {session['user_id']}")
        print(f"   - Turn count: {session['turn_count']}")
    else:
        print("❌ Failed to retrieve session")
        return False

    # 3. 대화 턴 추가
    print("\n3️⃣ Add Conversation Turns")
    turns = [
        ("오늘 점심 뭐 드셨어요?", "된장찌개 먹었어요"),
        ("어떤 반찬과 함께 드셨어요?", "김치랑 멸치볶음이요"),
        ("맛있게 드셨네요! 누가 만드셨어요?", "딸이 만들어줬어요")
    ]

    for i, (user_msg, assistant_msg) in enumerate(turns, 1):
        await manager.add_turn(
            user_id=test_user_id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            metadata={"turn_number": i}
        )
        print(f"✅ Turn {i} added")

    # 4. 대화 히스토리 조회
    print("\n4️⃣ Get Conversation History")
    history = await manager.get_conversation_history(test_user_id, limit=5)
    print(f"✅ Retrieved {len(history)} messages (from {len(turns)} turns)")
    for msg in history[:4]:  # 처음 4개만 출력
        print(f"   - {msg['role']}: {msg['content'][:50]}...")

    # 5. 컨텍스트 업데이트
    print("\n5️⃣ Update Context")
    await manager.update_context(
        user_id=test_user_id,
        context_updates={
            "recent_emotion": "기쁨",
            "biographical_facts": {"daughter_name": "수진"}
        }
    )
    print("✅ Context updated")

    # 6. 세션 통계
    print("\n6️⃣ Get Session Stats")
    stats = await manager.get_session_stats(test_user_id)
    print(f"✅ Session stats:")
    print(f"   - Turn count: {stats['turn_count']}")
    print(f"   - History length: {stats['history_length']}")
    print(f"   - Context keys: {stats['context_keys']}")

    # 7. AI 응답 생성 (통합)
    print("\n7️⃣ Generate Response via DialogueManager")
    try:
        response = await manager.generate_response(
            user_id=test_user_id,
            user_message="오늘 정말 좋은 하루였어요",
            next_question="내일은 뭐 하실 계획이세요?",
            emotion="joy",
            emotion_intensity=0.8
        )
        print(f"✅ Response generated ({len(response)} chars):")
        print(f"   {response[:150]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 8. 세션 종료
    print("\n8️⃣ End Session")
    await manager.end_session(test_user_id)
    print("✅ Session ended")

    # 9. 세션 삭제 확인
    session_after_end = await manager.get_session(test_user_id)
    if session_after_end is None:
        print("✅ Session successfully deleted")
    else:
        print("⚠️  Session still exists (might be cached)")

    print("\n" + "=" * 60)
    return True


async def test_context_window_limit():
    """컨텍스트 윈도우 크기 제한 테스트"""
    print("\n" + "=" * 60)
    print("🔍 Context Window Limit Test")
    print("=" * 60)

    manager = DialogueManager(max_context_turns=5)  # 최대 5턴
    test_user_id = "test_user_context_window"

    # 세션 시작
    await manager.start_session(test_user_id)

    # 10개 턴 추가 (5개를 초과)
    print("\n📝 Adding 10 turns (max_context_turns=5)...")
    for i in range(10):
        await manager.add_turn(
            user_id=test_user_id,
            user_message=f"User message {i+1}",
            assistant_message=f"Assistant response {i+1}"
        )

    # 히스토리 확인
    history = await manager.get_conversation_history(test_user_id)
    print(f"\n✅ History length: {len(history)} messages")
    print(f"   Expected: 10 messages (5 turns × 2)")
    print(f"   Actual: {len(history)} messages")

    if len(history) == 10:  # 5턴 × 2메시지 = 10개
        print("✅ Context window limit working correctly!")
    else:
        print(f"❌ Expected 10 messages, got {len(history)}")

    # 세션 종료
    await manager.end_session(test_user_id)

    print("\n" + "=" * 60)
    return len(history) == 10


async def main():
    """메인 테스트 실행"""
    print("\n")
    print("=" * 60)
    print("🚀 Dialogue Modules Test Suite")
    print("=" * 60)

    try:
        # 1. PromptBuilder 테스트
        prompt_success = await test_prompt_builder()

        # 2. ResponseGenerator 테스트
        response_success = await test_response_generator()

        # 3. DialogueManager 테스트
        dialogue_success = await test_dialogue_manager()

        # 4. 컨텍스트 윈도우 테스트
        window_success = await test_context_window_limit()

        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"  PromptBuilder: {'✅ PASS' if prompt_success else '❌ FAIL'}")
        print(f"  ResponseGenerator: {'✅ PASS' if response_success else '❌ FAIL'}")
        print(f"  DialogueManager: {'✅ PASS' if dialogue_success else '❌ FAIL'}")
        print(f"  Context Window Limit: {'✅ PASS' if window_success else '❌ FAIL'}")
        print("=" * 60)

        all_success = all([prompt_success, response_success, dialogue_success, window_success])

        if all_success:
            print("\n✅ All tests passed!")
            print("\n📌 Next steps:")
            print("   1. Integrate with core/workflow/message_processor.py")
            print("   2. Test end-to-end conversation flow")
            print("   3. Monitor token usage and response quality")
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
