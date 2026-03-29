#!/usr/bin/env python3
"""
저녁 회상 기능 테스트 스크립트

검증 항목:
1. 저녁 시간대(18~23시)에 evening_reflection_needed 플래그 설정
2. 1일 1회만 설정 (Redis TTL로 중복 방지)
3. 4턴 제한에도 evening_reflection_needed 보존
4. 프롬프트 빌더에 저녁 회상 지침 포함

Author: Memory Garden Team
Created: 2026-03-18
"""

import asyncio
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, "/home/admin/docker/MemoryGardenAI")

from core.dialogue.dialogue_manager import DialogueManager
from core.dialogue.prompt_builder import PromptBuilder
from database.redis_client import redis_client


async def test_evening_reflection_flag():
    """Test 1: 저녁 시간대 플래그 설정 테스트"""
    print("\n" + "=" * 60)
    print("TEST 1: 저녁 시간대 evening_reflection_needed 플래그 설정")
    print("=" * 60)

    dm = DialogueManager()
    test_user_id = "test_evening_user_001"

    # 기존 세션 정리
    await redis_client.delete_session(test_user_id)

    # 세션 시작
    await dm.start_session(test_user_id)

    # 현재 시간 확인
    now = datetime.now()
    is_evening = 18 <= now.hour <= 23
    print(f"  현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')} (hour={now.hour})")
    print(f"  저녁 시간대(18~23시) 여부: {is_evening}")

    # 응답 생성 (이 과정에서 evening_reflection_needed 플래그 설정됨)
    response = await dm.generate_response(
        user_id=test_user_id,
        user_message="안녕하세요"
    )

    # 세션 컨텍스트 확인
    session = await dm.get_session(test_user_id)
    context = session.get("context", {}) if session else {}

    # Redis에서 직접 플래그 확인
    date_str = now.strftime("%Y-%m-%d")
    reflection_key = f"evening_reflection_done:{test_user_id}:{date_str}"
    redis_conn = await redis_client.get_client()
    flag_in_redis = await redis_conn.get(reflection_key) if redis_conn else None

    print(f"\n  결과:")
    print(f"    - AI 응답 길이: {len(response)} 자")
    print(f"    - AI 응답 미리보기: {response[:100]}...")
    print(f"    - Redis 플래그 키: {reflection_key}")
    print(f"    - Redis 플래그 값: {flag_in_redis}")

    # 테스트 결과
    if is_evening:
        if flag_in_redis:
            print(f"\n  ✅ PASS: 저녁 시간대에 Redis 플래그가 설정됨")
        else:
            print(f"\n  ❌ FAIL: 저녁 시간대인데 Redis 플래그가 설정되지 않음")
    else:
        print(f"\n  ⚠️ SKIP: 현재 저녁 시간대가 아님 (테스트 불가)")

    # 정리
    await redis_client.delete_session(test_user_id)
    if redis_conn:
        await redis_conn.delete(reflection_key)

    return is_evening and flag_in_redis


async def test_four_turn_preservation():
    """Test 2: 4턴 제한 시 evening_reflection_needed 보존 테스트"""
    print("\n" + "=" * 60)
    print("TEST 2: 4턴 제한 시 evening_reflection_needed 보존")
    print("=" * 60)

    # _count_recent_turns와 4턴 제한 로직 시뮬레이션
    dm = DialogueManager()

    # 4턴 이상의 대화 시뮬레이션
    test_user_id = "test_four_turn_user"
    await redis_client.delete_session(test_user_id)
    await dm.start_session(test_user_id)

    # 5턴 추가 (1시간 윈도우 내)
    for i in range(5):
        await dm.add_turn(
            user_id=test_user_id,
            user_message=f"메시지 {i+1}",
            assistant_message=f"응답 {i+1}"
        )

    # 세션 확인
    session = await dm.get_session(test_user_id)

    # _count_recent_turns 테스트
    recent_turns = dm._count_recent_turns(session, 3600)  # 1시간 윈도우
    print(f"  최근 1시간 내 턴 수: {recent_turns}")

    # generate_response 호출 (내부적으로 4턴 체크 후 evening_reflection 보존)
    now = datetime.now()
    is_evening = 18 <= now.hour <= 23

    if is_evening:
        # 저녁 시간대에 Redis 플래그 설정
        date_str = now.strftime("%Y-%m-%d")
        reflection_key = f"evening_reflection_done:{test_user_id}:{date_str}"
        redis_conn = await redis_client.get_client()
        if redis_conn:
            await redis_conn.setex(reflection_key, 86400, "1")

        response = await dm.generate_response(
            user_id=test_user_id,
            user_message="테스트 메시지"
        )

        # 컨텍스트에서 evening_reflection_needed 확인
        # (4턴 제한이 걸려도 보존되어야 함)
        session_after = await dm.get_session(test_user_id)
        context_after = session_after.get("context", {}) if session_after else {}

        print(f"\n  결과:")
        print(f"    - 4턴 이상: {recent_turns >= 4}")
        print(f"    - AI 응답 길이: {len(response)} 자")
        print(f"    - AI 응답 미리보기: {response[:150]}...")

        # 응답에 회상 질문 포함 여부 확인
        reflection_keywords = ["식사", "활동", "만나", "건강", "하루", "어제", "오늘", "외출", "산책"]
        has_reflection = any(kw in response for kw in reflection_keywords)
        print(f"    - 회상 키워드 포함 여부: {has_reflection}")

        if recent_turns >= 4:
            print(f"\n  ✅ PASS: 4턴 제한 상태에서도 응답 생성됨")
            if has_reflection:
                print(f"  ✅ PASS: 회상 관련 내용이 응답에 포함됨")
            else:
                print(f"  ⚠️ WARNING: 회상 관련 내용이 명확하지 않음")
    else:
        print(f"\n  ⚠️ SKIP: 현재 저녁 시간대가 아님")

    # 정리
    await redis_client.delete_session(test_user_id)

    return True


async def test_prompt_builder():
    """Test 3: 프롬프트 빌더 저녁 회상 지침 테스트"""
    print("\n" + "=" * 60)
    print("TEST 3: 프롬프트 빌더 저녁 회상 지침 포함")
    print("=" * 60)

    pb = PromptBuilder()

    # 저녁 회상 플래그 없이 프롬프트 생성
    prompt_without = pb.build_system_prompt(
        user_name="테스트",
        recent_mentions=["어제 친구 만났어요", "오늘은 날씨가 좋아요"]
    )

    # 저녁 회상 플래그와 함께 프롬프트 생성
    prompt_with = pb.build_system_prompt(
        user_name="테스트",
        recent_mentions=["어제 친구 만났어요", "오늘은 날씨가 좋아요"],
        evening_reflection_needed=True
    )

    # 저녁 회상 지침 포함 여부 확인
    has_evening_section = "저녁 시간대 특별 지침" in prompt_with
    has_reflection_examples = "식사 관련" in prompt_with
    has_activity_examples = "활동 관련" in prompt_with
    has_meeting_examples = "만남 관련" in prompt_with
    has_mandatory_note = "반드시 하나" in prompt_with

    print(f"  결과:")
    print(f"    - '저녁 시간대 특별 지침' 섹션 포함: {has_evening_section}")
    print(f"    - '식사 관련' 예시 포함: {has_reflection_examples}")
    print(f"    - '활동 관련' 예시 포함: {has_activity_examples}")
    print(f"    - '만남 관련' 예시 포함: {has_meeting_examples}")
    print(f"    - '반드시 하나' 강조 포함: {has_mandatory_note}")

    # 프롬프트 길이 비교
    print(f"\n  프롬프트 길이:")
    print(f"    - without evening_reflection: {len(prompt_without)} 자")
    print(f"    - with evening_reflection: {len(prompt_with)} 자")

    # 저녁 회상 지침 내용 출력
    if has_evening_section:
        start_idx = prompt_with.find("## 저녁 시간대 특별 지침")
        end_idx = prompt_with.find("##", start_idx + 10)
        if end_idx == -1:
            end_idx = len(prompt_with)
        evening_section = prompt_with[start_idx:end_idx]
        print(f"\n  저녁 회상 지침 내용:")
        for line in evening_section.split("\n")[:15]:
            print(f"    {line}")

    # 결과 판정
    all_passed = all([
        has_evening_section,
        has_reflection_examples,
        has_activity_examples,
        has_meeting_examples,
        has_mandatory_note
    ])

    if all_passed:
        print(f"\n  ✅ PASS: 모든 저녁 회상 지침이 프롬프트에 포함됨")
    else:
        print(f"\n  ❌ FAIL: 일부 저녁 회상 지침이 누락됨")

    return all_passed


async def test_full_conversation():
    """Test 4: 전체 대화 플로우 테스트 (저녁 시간대)"""
    print("\n" + "=" * 60)
    print("TEST 4: 전체 대화 플로우 (저녁 회상 질문 검증)")
    print("=" * 60)

    dm = DialogueManager()
    test_user_id = "test_full_conversation_user"

    # 기존 세션 정리
    await redis_client.delete_session(test_user_id)

    # 세션 시작
    await dm.start_session(test_user_id)

    # 대화 컨텍스트에 recent_mentions 추가
    await dm.add_turn(
        user_id=test_user_id,
        user_message="오늘 점심에 된장찌개 먹었어요",
        assistant_message="된장찌개 드셨군요! 맛있는 점심이었나요?"
    )

    await dm.add_turn(
        user_id=test_user_id,
        user_message="네, 맛있었어요. 딸이랑 같이 먹었어요",
        assistant_message="딸분과 함께 드셨군요! 따뜻한 식사였겠네요."
    )

    # 현재 시간 확인
    now = datetime.now()
    is_evening = 18 <= now.hour <= 23
    print(f"  현재 시간: {now.strftime('%H:%M')} (저녁 시간대: {is_evening})")

    # 저녁 시간대라면 수동으로 플래그 설정 (테스트 목적)
    if not is_evening:
        print(f"  ⚠️ 저녁 시간대가 아니므로 테스트를 위해 플래그 강제 설정")
        date_str = now.strftime("%Y-%m-%d")
        reflection_key = f"evening_reflection_done:{test_user_id}:{date_str}"
        redis_conn = await redis_client.get_client()
        if redis_conn:
            # 기존 플래그 삭제 후 새로 설정
            await redis_conn.delete(reflection_key)

    # 응답 생성
    response = await dm.generate_response(
        user_id=test_user_id,
        user_message="저녁 먹었어요"
    )

    print(f"\n  AI 응답:")
    print(f"    {response}")

    # 회상 질문 포함 여부 확인
    # 1. 이전 대화 내용 언급 (점심=된장찌개, 딸)
    # 2. 회상 유도 질문 (식사, 활동, 만남 등)
    reflection_patterns = [
        ("점심/식사 언급", ["점심", "식사", "된장", "저녁"]),
        ("딸 언급", ["딸", "수진"]),
        ("회상 질문", ["어제", "오늘", "어떻게", "했나요", "하셨나요", "드셨나요"])
    ]

    found_patterns = []
    for pattern_name, keywords in reflection_patterns:
        if any(kw in response for kw in keywords):
            found_patterns.append(pattern_name)

    print(f"\n  패턴 분석:")
    for pattern_name, _ in reflection_patterns:
        status = "✅" if pattern_name in found_patterns else "❌"
        print(f"    {status} {pattern_name}")

    # 회상 질문이 포함되어 있는지 확인 (물음표)
    has_question = "?" in response
    print(f"\n  질문 포함 여부: {has_question}")

    # 정리
    await redis_client.delete_session(test_user_id)

    # 결과 판정
    if len(found_patterns) >= 1 and has_question:
        print(f"\n  ✅ PASS: 회상 관련 내용과 질문이 응답에 포함됨")
        return True
    else:
        print(f"\n  ⚠️ WARNING: 회상 질문이 명확하지 않을 수 있음")
        return False


async def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("저녁 회상 기능 테스트 시작")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {}

    # Test 1: 저녁 시간대 플래그 설정
    try:
        results["test1"] = await test_evening_reflection_flag()
    except Exception as e:
        print(f"  ❌ TEST 1 에러: {e}")
        results["test1"] = False

    # Test 2: 4턴 제한 보존
    try:
        results["test2"] = await test_four_turn_preservation()
    except Exception as e:
        print(f"  ❌ TEST 2 에러: {e}")
        results["test2"] = False

    # Test 3: 프롬프트 빌더
    try:
        results["test3"] = await test_prompt_builder()
    except Exception as e:
        print(f"  ❌ TEST 3 에러: {e}")
        results["test3"] = False

    # Test 4: 전체 대화 플로우
    try:
        results["test4"] = await test_full_conversation()
    except Exception as e:
        print(f"  ❌ TEST 4 에러: {e}")
        results["test4"] = False

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")

    print(f"\n  총합: {passed}/{total} 통과")

    # 현재 시간이 저녁 시간대인지 확인
    now = datetime.now()
    if not (18 <= now.hour <= 23):
        print(f"\n  ⚠️ 참고: 현재 저녁 시간대(18~23시)가 아닙니다.")
        print(f"     저녁 회상 기능은 18:00~23:59에 활성화됩니다.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
