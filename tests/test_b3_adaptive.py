"""
Phase B3 통합 테스트 스크립트

MCDI → 사만다 어댑티브 통합 전체 검증
8가지 시나리오로 모든 B3 기능 테스트
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes.kakao_webhook import _get_mcdi_context, _detect_repetition
from core.dialogue.prompt_builder import PromptBuilder, _get_probe_question, DEMENTIA_PROBE_QUESTIONS, DOMAIN_ROTATION, PROBE_QUESTION_COOLDOWN
from core.dialogue.response_generator import ResponseGenerator
from core.dialogue.dialogue_manager import DialogueManager
from database.redis_client import redis_client


class B3IntegrationTester:
    """B3 통합 테스터"""

    def __init__(self):
        self.pb = PromptBuilder()
        self.rg = ResponseGenerator()
        self.dm = DialogueManager()
        self.results = {
            "B3-1": {"passed": 0, "failed": 0, "details": []},
            "B3-2": {"passed": 0, "failed": 0, "details": []},
            "B3-3": {"passed": 0, "failed": 0, "details": []},
            "B3-4": {"passed": 0, "failed": 0, "details": []},
            "B3-5": {"passed": 0, "failed": 0, "details": []},
            "B3-6": {"passed": 0, "failed": 0, "details": []},
        }

    def _log(self, test_name: str, message: str, passed: bool = None):
        """테스트 결과 로그"""
        status = "✅" if passed else "❌" if passed is not None else "ℹ️"
        print(f"{status} [{test_name}] {message}")

        if passed is not None:
            task_key = test_name.split("-")[0]  # B3-1, B3-2 등
            if task_key in self.results:
                if passed:
                    self.results[task_key]["passed"] += 1
                else:
                    self.results[task_key]["failed"] += 1
                self.results[task_key]["details"].append(f"{status} {message}")

    async def test_b3_1_mcdi_context_cache(self):
        """B3-1: MCDI 컨텍스트 캐시 동작 테스트"""
        print("\n" + "="*70)
        print("B3-1: MCDI 컨텍스트 캐시 테스트")
        print("="*70)

        test_user_id = "test_b3_user_1"

        # 캐시 삭제 후 첫 조회
        try:
            await redis_client.delete(f"mcdi_context:{test_user_id}")
            self._log("B3-1-1", "캐시 삭제 완료", True)
        except Exception as e:
            self._log("B3-1-1", f"캐시 삭제 실패: {e}", False)
            return

        # 첫 번째 호출 (DB 조회)
        try:
            ctx1 = await _get_mcdi_context(test_user_id)
            self._log("B3-1-2", "첫 번째 MCDI 컨텍스트 조회 성공", True)
            self._log("B3-1-3", f"초기 risk_level: {ctx1.get('latest_risk_level')}", True)
        except Exception as e:
            self._log("B3-1-2", f"첫 번째 조회 실패: {e}", False)
            return

        # 캐시 확인
        try:
            cached = await redis_client.get_json(f"mcdi_context:{test_user_id}")
            if cached:
                self._log("B3-1-4", "Redis 캐시 저장 확인", True)
            else:
                self._log("B3-1-4", "Redis 캐시 저장 실패", False)
        except Exception as e:
            self._log("B3-1-4", f"캐시 확인 실패: {e}", False)

        # 두 번째 호출 (캐시에서 읽기)
        try:
            ctx2 = await _get_mcdi_context(test_user_id)
            self._log("B3-1-5", "두 번째 MCDI 컨텍스트 조회 성공 (캐시)", True)
        except Exception as e:
            self._log("B3-1-5", f"두 번째 조회 실패: {e}", False)

        # 정리
        await redis_client.delete(f"mcdi_context:{test_user_id}")

    async def test_b3_2_adaptive_strategy_texts(self):
        """B3-2: 어댑티브 전략 텍스트 검증"""
        print("\n" + "="*70)
        print("B3-2: 어댑티브 대화 전략 텍스트 테스트")
        print("="*70)

        # YELLOW 모드 테스트
        yellow_ctx = {
            "latest_risk_level": "YELLOW",
            "latest_mcdi_score": 65.0,
            "score_trend": "declining",
            "slope_per_week": -1.5,
            "latest_scores": {"LR": 70.0, "TO": 60.0},
            "has_data": True
        }

        try:
            prompt = await self.pb.build_system_prompt(mcdi_context=yellow_ctx)
            has_yellow_block = "[인지 주의 모드 - YELLOW]" in prompt
            has_short_sentence = "짧고 명확하게" in prompt

            self._log("B3-2-1", f"YELLOW 모드 블록 포함: {has_yellow_block}", has_yellow_block)
            self._log("B3-2-2", f"짧은 문장 지침 포함: {has_short_sentence}", has_short_sentence)
        except Exception as e:
            self._log("B3-2-1", f"YELLOW 모드 테스트 실패: {e}", False)

        # ORANGE 모드 테스트
        orange_ctx = {
            "latest_risk_level": "ORANGE",
            "latest_mcdi_score": 45.0,
            "score_trend": "declining",
            "slope_per_week": -3.0,
            "latest_scores": {"LR": 50.0, "TO": 40.0},
            "has_data": True
        }

        try:
            prompt = await self.pb.build_system_prompt(mcdi_context=orange_ctx)
            has_orange_block = "[인지 집중 모드 - ORANGE]" in prompt
            has_10word_limit = "문장당 10단어 이하" in prompt
            has_confirm_question = "이해되셨어요?" in prompt or "괜찮으세요?" in prompt

            self._log("B3-2-3", f"ORANGE 모드 블록 포함: {has_orange_block}", has_orange_block)
            self._log("B3-2-4", f"10단어 제한 포함: {has_10word_limit}", has_10word_limit)
            self._log("B3-2-5", f"확인 질문 지침 포함: {has_confirm_question}", has_confirm_question)
        except Exception as e:
            self._log("B3-2-3", f"ORANGE 모드 테스트 실패: {e}", False)

        # RED 모드 테스트
        red_ctx = {
            "latest_risk_level": "RED",
            "latest_mcdi_score": 25.0,
            "score_trend": "declining",
            "slope_per_week": -5.0,
            "latest_scores": {"LR": 30.0, "TO": 20.0},
            "has_data": True
        }

        try:
            prompt = await self.pb.build_system_prompt(mcdi_context=red_ctx)
            has_red_block = "[돌봄 모드 - RED]" in prompt or "[긴급 돌봄 모드 - RED]" in prompt
            # 실제 코드: "- 어떤 형태의 인지 자극 질문도 하지 마세요"
            has_no_stimulus = "인지 자극 질문도 하지 마세요" in prompt
            has_emotional_only = "정서적 지지" in prompt

            self._log("B3-2-6", f"RED 모드 블록 포함: {has_red_block}", has_red_block)
            self._log("B3-2-7", f"인지 자극 금지 포함: {has_no_stimulus}", has_no_stimulus)
            self._log("B3-2-8", f"정서적 지지 지침 포함: {has_emotional_only}", has_emotional_only)
        except Exception as e:
            self._log("B3-2-6", f"RED 모드 테스트 실패: {e}", False)

    async def test_b3_3_prompt_integration(self):
        """B3-3: prompt_builder 어댑티브 블록 통합 테스트"""
        print("\n" + "="*70)
        print("B3-3: prompt_builder 어댑티브 블록 통합 테스트")
        print("="*70)

        # 기본 프롬프트 + MCDI 컨텍스트
        mcdi_ctx = {
            "latest_risk_level": "YELLOW",
            "latest_mcdi_score": 62.0,
            "score_trend": "stable",
            "slope_per_week": 0.0,
            "latest_scores": {"NC": 55.0, "TO": 68.0, "ER": 60.0},
            "has_data": True
        }

        try:
            prompt = await self.pb.build_system_prompt(
                user_name="테스트",
                garden_name="기억의 정원",
                mcdi_context=mcdi_ctx
            )

            has_base_prompt = "정원사" in prompt
            has_user_info = "테스트" in prompt or "기억의 정원" in prompt
            has_adaptive_block = "[인지 주의 모드" in prompt

            self._log("B3-3-1", f"기본 프롬프트 유지: {has_base_prompt}", has_base_prompt)
            self._log("B3-3-2", f"사용자 정보 포함: {has_user_info}", has_user_info)
            self._log("B3-3-3", f"어댑티브 블록 추가: {has_adaptive_block}", has_adaptive_block)

            # 프롬프트 길이 체크 (기존 대비 +15% 이내)
            base_prompt = await self.pb.build_system_prompt(user_name="테스트")
            base_len = len(base_prompt)
            adaptive_len = len(prompt)
            increase_ratio = (adaptive_len - base_len) / base_len if base_len > 0 else 0
            within_limit = increase_ratio <= 0.15

            self._log("B3-3-4", f"프롬프트 길이 증가율: {increase_ratio:.1%} (한계 15%)", within_limit)
        except Exception as e:
            self._log("B3-3-1", f"통합 테스트 실패: {e}", False)

        # 도메인 질문 힌트 테스트
        try:
            to_question = await _get_probe_question("TO")
            er_question = await _get_probe_question("ER")
            lr_question = await _get_probe_question("LR")

            # TO: 요일, 시간, 날짜, 월, 며칠, 몇 시 등 시간 관련 키워드
            has_to = any(kw in to_question for kw in ["요일", "시간", "날짜", "월", "며칠", "아침", "몇 시"])
            # ER: 기억, 생각, 회상 등 인지 관련 키워드
            has_er = any(kw in er_question for kw in ["기억", "생각", "회상", "기나"])
            # LR: 어릴, 젊었을, 학교, 옛날, 고향 등 과거 관련 키워드
            has_lr = any(kw in lr_question for kw in ["어릴", "젊었을", "학교", "옛날", "젊을", "고향"])

            self._log("B3-3-5", f"TO 질문 생성: {has_to} ('{to_question}')", has_to)
            self._log("B3-3-6", f"ER 질문 생성: {has_er} ('{er_question}')", has_er)
            self._log("B3-3-7", f"LR 질문 생성: {has_lr} ('{lr_question}')", has_lr)
        except Exception as e:
            self._log("B3-3-5", f"도메인 질문 테스트 실패: {e}", False)

    async def test_b3_4_probe_cooldown(self):
        """B3-4: 인지 도메인 질문 중복 삽입 방지 테스트 (inline cooldown)"""
        print("\n" + "="*70)
        print("B3-4: 인지 도메인 질문 쿨다운 테스트 (inline)")
        print("="*70)

        test_user_id = "test_b3_user_4"

        # 기존 쿨다운 정리
        try:
            await redis_client.delete(f"probe_cooldown:{test_user_id}:TO")
            await redis_client.delete(f"probe_cooldown:{test_user_id}:LR")
        except Exception:
            pass

        # 첫 번째 호출 - 질문 반환되어야 함
        try:
            result1 = await _get_probe_question("TO", test_user_id)
            has_question1 = bool(result1)
            self._log("B3-4-1", f"첫 TO 질문 반환: {has_question1} ('{result1}')", has_question1)
        except Exception as e:
            self._log("B3-4-1", f"첫 번째 질문 호출 실패: {e}", False)

        # 바로 두 번째 호출 - 빈 문자열 반환되어야 함 (쿨다운 중)
        try:
            result2 = await _get_probe_question("TO", test_user_id)
            is_empty = result2 == ""
            self._log("B3-4-2", f"연속 TO 질문 쿨다운 차단: {is_empty}", is_empty)
        except Exception as e:
            self._log("B3-4-2", f"두 번째 질문 호출 실패: {e}", False)

        # 다른 도메인 - 질문 반환되어야 함
        try:
            result3 = await _get_probe_question("LR", test_user_id)
            has_question3 = bool(result3)
            self._log("B3-4-3", f"다른 도메인(LR) 질문 허용: {has_question3} ('{result3}')", has_question3)
        except Exception as e:
            self._log("B3-4-3", f"다른 도메인 질문 호출 실패: {e}", False)

        # 정리
        await redis_client.delete(f"probe_cooldown:{test_user_id}:TO")
        await redis_client.delete(f"probe_cooldown:{test_user_id}:LR")

    async def test_b3_5_repetition_detection(self):
        """B3-5: 반복 발화 감지 테스트"""
        print("\n" + "="*70)
        print("B3-5: 반복 발화 감지 테스트")
        print("="*70)

        # 정상 케이스
        try:
            result1 = _detect_repetition("오늘 점심 뭐 드셨어요?", ["아침은 드셨어요?", "어제 저녁은"])
            self._log("B3-5-1", f"정상 발화: 반복 없음 = {not result1}", not result1)
        except Exception as e:
            self._log("B3-5-1", f"정상 발화 테스트 실패: {e}", False)

        # 70% 이상 중복 케이스
        try:
            result2 = _detect_repetition("배고파 배고파", ["배고파", "밥 먹을래"])
            self._log("B3-5-2", f"반복 발화 감지: {result2}", result2)
        except Exception as e:
            self._log("B3-5-2", f"반복 발화 테스트 실패: {e}", False)

        # 최근 발화 부족
        try:
            result3 = _detect_repetition("배고파", [])
            self._log("B3-5-3", f"히스토리 없음: 반복 없음 = {not result3}", not result3)
        except Exception as e:
            self._log("B3-5-3", f"히스토리 부족 테스트 실패: {e}", False)

    async def test_b3_6_slope_early_warning(self):
        """B3-6: slope < -2.0 조기 경보 테스트"""
        print("\n" + "="*70)
        print("B3-6: slope 조기 경보 테스트")
        print("="*70)

        # TimescaleDB 모킹 없이 캐시 직접 테스트
        test_user_id = "test_b3_user_6"
        cache_key = f"mcdi_context:{test_user_id}"

        # slope < -2.0 케이스 직접 설정
        warning_ctx = {
            "latest_risk_level": "GREEN",
            "latest_mcdi_score": 70.0,
            "score_trend": "declining",
            "slope_per_week": -3.0,  # 조기 경보 임계값 미달
            "latest_scores": {"LR": 72.0, "SD": 68.0},
            "has_data": True
        }

        try:
            # 캐시에 저장 (slope < -2.0 상태로)
            await redis_client.set_json(cache_key, warning_ctx, ttl=300)

            # 조회 후 risk_level 상향 확인
            retrieved = await _get_mcdi_context(test_user_id)
            upgraded = retrieved.get("latest_risk_level") == "YELLOW"  # GREEN → YELLOW

            self._log("B3-6-1", f"slope -3.0 → risk_level 상향: {upgraded}", upgraded)
            self._log("B3-6-2", f"변경된 risk_level: {retrieved.get('latest_risk_level')}", upgraded)
        except Exception as e:
            self._log("B3-6-1", f"조기 경보 테스트 실패: {e}", False)
        finally:
            await redis_client.delete(cache_key)

    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*70)
        print("B3 통합 테스트 결과 요약")
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
            print("🎉 모든 테스트 통과! B3 구현 완료.")
        else:
            print(f"⚠️ {total_failed}개 테스트 실패 - 확인 필요.")
        print("="*70)


async def main():
    tester = B3IntegrationTester()

    print("Phase B3 통합 테스트 시작...\n")

    await tester.test_b3_1_mcdi_context_cache()
    await tester.test_b3_2_adaptive_strategy_texts()
    await tester.test_b3_3_prompt_integration()
    await tester.test_b3_4_probe_cooldown()
    await tester.test_b3_5_repetition_detection()
    await tester.test_b3_6_slope_early_warning()

    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
