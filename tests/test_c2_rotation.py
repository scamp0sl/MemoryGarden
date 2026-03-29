"""
Phase C2 통합 테스트 스크립트

치매 탐지 분산 전략 (Domain Rotation) 기능 검증
- DOMAIN_ROTATION 상수 정의
- 6개 MCDI 도메인 순회
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.dialogue.prompt_builder import DOMAIN_ROTATION, _get_probe_question, DEMENTIA_PROBE_QUESTIONS


class C2IntegrationTester:
    """C2 통합 테스터"""

    def __init__(self):
        self.results = {
            "C2-1": {"passed": 0, "failed": 0, "details": []},
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

    def test_c2_1_domain_rotation_constant(self):
        """C2-1: DOMAIN_ROTATION 상수 정의 검증"""
        print("\n" + "="*70)
        print("C2-1: DOMAIN_ROTATION 상수 정의 검증")
        print("="*70)

        try:
            # 상수 존재 확인
            has_constant = DOMAIN_ROTATION is not None
            self._log("C2-1-1", f"DOMAIN_ROTATION 상수 존재: {has_constant}", has_constant)

            # 6개 도메인 포함 확인
            has_all_domains = (
                "LR" in DOMAIN_ROTATION and
                "SD" in DOMAIN_ROTATION and
                "NC" in DOMAIN_ROTATION and
                "TO" in DOMAIN_ROTATION and
                "ER" in DOMAIN_ROTATION and
                "RT" in DOMAIN_ROTATION
            )
            self._log("C2-1-2", f"6개 MCDI 도메인 포함: {has_all_domains}", has_all_domains)

            # 순서 확인 (LR → SD → NC → TO → ER → RT)
            expected_order = ["LR", "SD", "NC", "TO", "ER", "RT"]
            is_correct_order = DOMAIN_ROTATION == expected_order
            self._log("C2-1-3", f"도메인 순서 올바름: {is_correct_order}", is_correct_order)

            # 각 도메인별 질문 풀 존재 확인
            all_domains_have_questions = True
            for domain in DOMAIN_ROTATION:
                if domain not in DEMENTIA_PROBE_QUESTIONS:
                    all_domains_have_questions = False
                    self._log(f"C2-1-{domain}", f"{domain} 도메인 질문 풀 누락", False)
                else:
                    questions = DEMENTIA_PROBE_QUESTIONS[domain]
                    if domain == "RT":
                        # RT는 None이어야 함 (응답 속도로 분석)
                        has_none = questions is None
                        self._log(f"C2-1-{domain}", f"{domain} 도메인 None 처리: {has_none}", has_none)
                    else:
                        has_questions = questions and len(questions) > 0
                        self._log(f"C2-1-{domain}", f"{domain} 도메인 질문 존재: {has_questions}", has_questions)

            self._log("C2-1-4", f"모든 도메인 질문 풀 정상: {all_domains_have_questions}", all_domains_have_questions)

        except Exception as e:
            self._log("C2-1-1", f"DOMAIN_ROTATION 테스트 실패: {e}", False)

    async def test_c2_1_probe_question_generation(self):
        """C2-1: 탐침 질문 생성 (async) 테스트"""
        print("\n" + "="*70)
        print("C2-1: 탐침 질문 async 생성 테스트")
        print("="*70)

        test_user_id = "test_c2_user"

        try:
            # 각 도메인별 질문 생성 테스트
            for domain in DOMAIN_ROTATION:
                if domain == "RT":
                    # RT는 빈 문자열 반환
                    question = await _get_probe_question(domain, test_user_id)
                    is_empty = question == ""
                    self._log(f"C2-1-Q-{domain}", f"{domain} 질문 빈 문자열: {is_empty}", is_empty)
                else:
                    question = await _get_probe_question(domain, test_user_id)
                    has_question = bool(question)
                    self._log(f"C2-1-Q-{domain}", f"{domain} 질문 생성: {has_question} ('{question[:30]}...')", has_question)

        except Exception as e:
            self._log("C2-1-Q", f"탐침 질문 생성 테스트 실패: {e}", False)

    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*70)
        print("C2 통합 테스트 결과 요약")
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
            print("🎉 모든 테스트 통과! C2 구현 완료.")
        else:
            print(f"⚠️ {total_failed}개 테스트 실패 - 확인 필요.")
        print("="*70)


async def main():
    tester = C2IntegrationTester()

    print("Phase C2 통합 테스트 시작...\n")

    tester.test_c2_1_domain_rotation_constant()
    await tester.test_c2_1_probe_question_generation()

    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
