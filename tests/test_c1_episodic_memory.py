"""
Phase C1 통합 테스트 스크립트

에피소드 기억 데이터 모델 확장 기능 검증
- ExtractedMemory 신규 필드 (samantha_emotion, follow_up_notes, relationship_impact)
- _generate_follow_up_note_async() LLM 기반 메모 생성
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.memory.memory_extractor import ExtractedMemory, MemoryType, EntityCategory
from core.memory.memory_manager import MemoryManager


class C1IntegrationTester:
    """C1 통합 테스터"""

    def __init__(self):
        self.mm = MemoryManager()
        self.results = {
            "C1-1": {"passed": 0, "failed": 0, "details": []},
            "C1-2": {"passed": 0, "failed": 0, "details": []},
            "C1-3": {"passed": 0, "failed": 0, "details": []},
        }

    def _log(self, test_name: str, message: str, passed: bool = None):
        """테스트 결과 로그"""
        status = "✅" if passed else "❌" if passed is not None else "ℹ️"
        print(f"{status} [{test_name}] {message}")

        if passed is not None:
            parts = test_name.split("-")
            if len(parts) >= 2:
                task_key = f"{parts[0]}-{parts[1]}"
            else:
                task_key = parts[0]

            if task_key not in self.results:
                self.results[task_key] = {"passed": 0, "failed": 0, "details": []}

            if passed:
                self.results[task_key]["passed"] += 1
            else:
                self.results[task_key]["failed"] += 1
            self.results[task_key]["details"].append(f"{status} {message}")

    def test_c1_1_extracted_memory_new_fields(self):
        """C1-1: ExtractedMemory 신규 필드 검증"""
        print("\n" + "="*70)
        print("C1-1: ExtractedMemory 신규 필드 검증")
        print("="*70)

        try:
            # 기본 필드 + 신규 필드 포함하여 생성
            memory = ExtractedMemory(
                memory_type=MemoryType.EPISODIC,
                content="어제 딸 수진이와 함께 저녁 먹었어요",
                category=EntityCategory.PERSON,
                confidence=0.9,
                importance=0.8,
                samantha_emotion="기쁨",  # C1 신규 필드
                follow_up_notes="딸과의 식사 경험에 대해 다시 물어보기",  # C1 신규 필드
                relationship_impact=0.7  # C1 신규 필드
            )

            has_samantha = memory.samantha_emotion == "기쁨"
            has_follow_up = memory.follow_up_notes == "딸과의 식사 경험에 대해 다시 물어보기"
            has_impact = memory.relationship_impact == 0.7

            self._log("C1-1-1", f"samantha_emotion 필드 존재 및 값 확인: {has_samantha}", has_samantha)
            self._log("C1-1-2", f"follow_up_notes 필드 존재 및 값 확인: {has_follow_up}", has_follow_up)
            self._log("C1-1-3", f"relationship_impact 필드 존재 및 값 확인: {has_impact}", has_impact)

        except Exception as e:
            self._log("C1-1-1", f"ExtractedMemory 신규 필드 테스트 실패: {e}", False)

    async def test_c1_2_generate_follow_up_note(self):
        """C1-2: _generate_follow_up_note_async() LLM 메모 생성"""
        print("\n" + "="*70)
        print("C1-2: LLM 기반 후속 추적 메모 생성")
        print("="*70)

        try:
            # 기본 케이스
            note1 = await self.mm._generate_follow_up_note_async(
                memory_content="어제 딸 수진이와 함께 저녁 먹었어요",
                user_emotion="기쁨"
            )
            has_note1 = note1 is not None and len(note1) >= 5
            self._log("C1-2-1", f"후속 메모 생성 성공: {has_note1}", has_note1)
            if note1:
                self._log("C1-2-1-detail", f"생성된 메모: {note1}", True)

            # 빈 내용 처리
            note2 = await self.mm._generate_follow_up_note_async(
                memory_content="",
                user_emotion=None
            )
            is_none_or_valid = note2 is None or (note2 and len(note2) >= 5)
            self._log("C1-2-2", f"빈 내용 처리: {is_none_or_valid}", is_none_or_valid)

        except Exception as e:
            self._log("C1-2-1", f"LLM 후속 메모 생성 테스트 실패: {e}", False)

    async def test_c1_3_metadata_integration(self):
        """C1-3: 메타데이터 통합 테스트"""
        print("\n" + "="*70)
        print("C1-3: 메타데이터 통합 테스트")
        print("="*70)

        try:
            # ExtractedMemory 생성 및 메타데이터 검증
            memory = ExtractedMemory(
                memory_type=MemoryType.EPISODIC,
                content="어제 운동하러 갔어요",
                category=EntityCategory.ACTIVITY,
                confidence=0.85,
                importance=0.7,
                samantha_emotion="무관심",
                follow_up_notes="운동 루틴에 대해 더 물어보기",
                relationship_impact=0.3,
                metadata={"source": "webhook", "has_image": False}
            )

            # metadata에 새 필드가 포함되어 있는지 확인
            base_metadata = memory.metadata
            has_base_meta = "source" in base_metadata
            self._log("C1-3-1", f"기존 metadata 유지: {has_base_meta}", has_base_meta)

            # 새 필드 직접 접근 확인
            direct_fields = (
                memory.samantha_emotion == "무관심" and
                memory.follow_up_notes == "운동 루틴에 대해 더 물어보기" and
                memory.relationship_impact == 0.3
            )
            self._log("C1-3-2", f"신규 필드 직접 접근 가능: {direct_fields}", direct_fields)

        except Exception as e:
            self._log("C1-3-1", f"메타데이터 통합 테스트 실패: {e}", False)

    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*70)
        print("C1 통합 테스트 결과 요약")
        print("="*70)

        total_passed = 0
        total_failed = 0

        for task_name, result in self.results.items():
            passed = result["passed"]
            failed = result["failed"]
            total = passed + failed
            total_passed += passed
            total_failed += failed

            status = "✅ PASS" if failed == 0 else "⚠️ PARTIAL" if passed > 0 else "❌ FAIL"
            print(f"\n{task_name}: {status} ({passed}/{total} passed)")

        print(f"\n{'='*70}")
        print(f"전체: {total_passed}/{total_passed + total_failed} 테스트 통과")

        if total_failed == 0:
            print("🎉 모든 테스트 통과! C1 구현 완료.")
        else:
            print(f"⚠️ {total_failed}개 테스트 실패 - 확인 필요.")
        print("="*70)


async def main():
    tester = C1IntegrationTester()

    print("Phase C1 통합 테스트 시작...\n")

    tester.test_c1_1_extracted_memory_new_fields()
    await tester.test_c1_2_generate_follow_up_note()
    await tester.test_c1_3_metadata_integration()

    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
