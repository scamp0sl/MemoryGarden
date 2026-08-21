"""
Action01 테스트 시나리오 검증

Section 5.1 정상 케이스 & Section 5.2 경계 케이스 테스트
"""

import asyncio
from datetime import datetime
from core.memory.memory_extractor import MemoryExtractor

# 테스트 케이스 정의
TEST_CASES = {
    "정상1_이름_선언": {
        "user": "나는 홍길동이야",
        "assistant": "홍길동님이군요! 만나서 반가워요.",
        "expected_bio": [{"entity": "name", "value": "홍길동"}],
        "expected_episodic": ["홍길동", "소개"]
    },
    "정상2_딸_이름": {
        "user": "딸은 수진이야",
        "assistant": "수진 씨 멋진 이름이네요!",
        "expected_bio": [{"entity": "daughter_name", "value": "수진"}],
        "expected_episodic": ["수진", "언급"]
    },
    "정상3_음식_선호": {
        "user": "제육 좋아해",
        "assistant": "저도 제육 좋아해요! ㅎㅎ",
        "expected_bio": [{"entity": "favorite_food", "value": "제육"}],
        "expected_episodic": ["좋아"]
    },
    "정상4_진달래_꽃": {
        "user": "산에서 진달래를 봤어",
        "assistant": "아, 진달래 꽃 폈나 봐요? ㅎㅎ",
        "expected_bio": [],  # 비어있어야 함 (제외 키워드)
        "expected_episodic": ["진달래", "꽃"]
    },
    "정상5_쑥_캐기": {
        "user": "엄마가 쑥을 캐갔어",
        "assistant": "쑥떡 해먹으셨나 보네요?",
        "expected_bio": [],  # 비어있어야 함 (제외 키워드)
        "expected_episodic": ["쑥", "캐다"]
    },
    "경계1_봄_계절": {
        "user": "봄이 왔어",
        "assistant": "그러게요, 따뜻해지네요!",
        "expected_bio": [],  # 비어있어야 함 (계절)
        "expected_episodic": ["봄"]
    },
    "경계2_바람_자연": {
        "user": "바람이 분다",
        "assistant": "쌀쌀하네요.",
        "expected_bio": [],  # 비어있어야 함 (자연)
        "expected_episodic": ["바람"]
    },
    "경계3_인왕산_장소": {
        "user": "인왕산 갔었어",
        "assistant": "산책하셨군요!",
        "expected_bio": [],  # 장소 언급만으로는 biographical 아님
        "expected_episodic": ["인왕산"]
    },
    "경계4_맛_표현": {
        "user": "쑥 떡 맛있다",
        "assistant": "그렇죠? 쫀깃하니까 맛있어요.",
        "expected_bio": [],  # "맛있다"는 favorite_food 승격 조건 미충족
        "expected_episodic": ["쑥떡", "맛"]
    },
}


async def run_test(case_name: str, test_data: dict, extractor: MemoryExtractor):
    """단일 테스트 케이스 실행"""
    print(f"\n{'='*60}")
    print(f"테스트: {case_name}")
    print(f"입력: {test_data['user']}")
    print(f"{'='*60}")

    result = await extractor.extract_from_message(
        user_message=test_data['user'],
        assistant_message=test_data['assistant'],
        context={"emotion": "neutral"}
    )

    # Biographical Facts 검증
    bio_facts = result.biographical_facts
    print(f"\n[결과] Biographical Facts: {len(bio_facts)}개")
    for fact in bio_facts:
        print(f"  - entity={fact.entity}, value={fact.value}, confidence={fact.confidence}")

    # Episodic Memories 검증
    epi_memories = result.episodic_memories
    print(f"\n[결과] Episodic Facts: {len(epi_memories)}개")
    for mem in epi_memories:
        print(f"  - {mem.content[:50]}...")

    # 검증
    expected_bio = test_data['expected_bio']
    if len(expected_bio) == 0:
        # 비어있어야 함
        if len(bio_facts) == 0:
            print(f"\n✅ PASS: biographical fact가 저장되지 않음 (제외 키워드 작동)")
        else:
            print(f"\n❌ FAIL: biographical fact가 {len(bio_facts)}개 저장됨 (0개 예상)")
    else:
        # 특정 entity가 있어야 함
        found = False
        for exp in expected_bio:
            for fact in bio_facts:
                if fact.entity == exp['entity'] and fact.value == exp['value']:
                    print(f"\n✅ PASS: {exp['entity']}={exp['value']} 저장됨")
                    found = True
                    break
            if not found:
                print(f"\n❌ FAIL: {exp['entity']}={exp['value']} 찾을 수 없음")

    # Episodic 확인
    if len(epi_memories) > 0:
        print(f"✅ Episodic fact 저장됨: {epi_memories[0].content[:40]}...")
    else:
        print(f"⚠️  Episodic fact가 저장되지 않음")

    return {
        "bio_count": len(bio_facts),
        "epi_count": len(epi_memories),
        "pass": len(expected_bio) == 0 and len(bio_facts) == 0
    }


async def main():
    """모든 테스트 실행"""
    extractor = MemoryExtractor()

    print("="*60)
    print("Action01 테스트 시나리오 검증")
    print("="*60)

    results = {}
    for case_name, test_data in TEST_CASES.items():
        result = await run_test(case_name, test_data, extractor)
        results[case_name] = result

    # 요약
    print(f"\n\n{'='*60}")
    print("테스트 요약")
    print(f"{'='*60}")

    total = len(results)
    pass_count = sum(1 for r in results.values() if r.get('pass', False))

    print(f"\n총 {total}개 테스트 중 {pass_count}개 PASS")

    for case_name, result in results.items():
        status = "✅ PASS" if result.get('pass', False) else "⚠️  CHECK"
        print(f"{status} | {case_name}: bio={result['bio_count']}, epi={result['epi_count']}")

    # 핵심 확인사항
    print(f"\n{'='*60}")
    print("핵심 확인사항")
    print(f"{'='*60}")

    critical_cases = [
        ("정상4_진달래_꽃", results["정상4_진달래_꽃"]),
        ("정상5_쑥_캐기", results["정상5_쑥_캐기"]),
        ("경계1_봄_계절", results["경계1_봄_계절"]),
        ("경계2_바람_자연", results["경계2_바람_자연"]),
    ]

    all_pass = True
    for case_name, result in critical_cases:
        if result['bio_count'] == 0:
            print(f"✅ {case_name}: 제외 키워드 정상 작동 (bio={result['bio_count']})")
        else:
            print(f"❌ {case_name}: 제외 키워드 미작동 (bio={result['bio_count']})")
            all_pass = False

    if all_pass:
        print(f"\n🎉 Action01 검증 완료! 제외 키워드가 정상 작동합니다.")
    else:
        print(f"\n⚠️  일부 테스트가 실패했습니다. 로그를 확인하세요.")


if __name__ == "__main__":
    asyncio.run(main())
