"""
Phase B2 통합 테스트 스크립트

감정 벡터 모델 (Emotion Vector) 기능 검증
3차원 감정 상태 추적 및 부드러운 전환 확인
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.dialogue.dialogue_manager import DialogueManager, EMOTION_VECTOR_MAP, MAX_DELTA_PER_TURN
from core.dialogue.prompt_builder import PromptBuilder, _vector_to_prompt_description
from core.dialogue.response_generator import ResponseGenerator
from database.redis_client import redis_client


class B2IntegrationTester:
    """B2 통합 테스터"""

    def __init__(self):
        self.dm = DialogueManager()
        self.pb = PromptBuilder()
        self.rg = ResponseGenerator()
        self.results = {
            "B2-1": {"passed": 0, "failed": 0, "details": []},
            "B2-2": {"passed": 0, "failed": 0, "details": []},
            "B2-3": {"passed": 0, "failed": 0, "details": []},
            "B2-4": {"passed": 0, "failed": 0, "details": []},
            "B2-5": {"passed": 0, "failed": 0, "details": []},
            "B2-6": {"passed": 0, "failed": 0, "details": []},
        }

    def _log(self, test_name: str, message: str, passed: bool = None):
        """테스트 결과 로그"""
        status = "✅" if passed else "❌" if passed is not None else "ℹ️"
        print(f"{status} [{test_name}] {message}")

        if passed is not None:
            # task_key 추출: "B2-1-1" → "B2-1", "B2-I1-1" → "B2-I1"
            parts = test_name.split("-")
            if len(parts) >= 2:
                task_key = f"{parts[0]}-{parts[1]}"  # "B2-1", "B2-I1" 등
            else:
                task_key = parts[0]

            if task_key not in self.results:
                # 통합 테스트용 결과 버킷 생성
                self.results[task_key] = {"passed": 0, "failed": 0, "details": []}

            if passed:
                self.results[task_key]["passed"] += 1
            else:
                self.results[task_key]["failed"] += 1
            self.results[task_key]["details"].append(f"{status} {message}")

    async def test_b2_1_emotion_vector_map(self):
        """B2-1~3: 감정 벡터 매핑 테이블 검증"""
        print("\n" + "="*70)
        print("B2-1~3: 감정 벡터 매핑 테이블 테스트")
        print("="*70)

        try:
            # 필수 감정 키 확인
            required_emotions = ["기쁨", "행복", "즐거움", "설렘", "평온", "만족",
                               "불안", "짜증", "스트레스", "분노", "우울", "슬픔", "피곤", "무기력", "중립"]

            has_all = all(emotion in EMOTION_VECTOR_MAP for emotion in required_emotions)
            self._log("B2-1-1", f"필수 감정 {len(required_emotions)}개 포함: {has_all}", has_all)

            # 각 벡터가 3차원인지 확인 (valence, arousal, intimacy)
            all_3d = all(
                isinstance(EMOTION_VECTOR_MAP[e], tuple) and len(EMOTION_VECTOR_MAP[e]) == 3
                for e in EMOTION_VECTOR_MAP
            )
            self._log("B2-1-2", f"모든 벡터가 3차원(v, a, i): {all_3d}", all_3d)

            # 값 범위 확인 (-1.0 ~ 1.0)
            all_valid = all(
                all(-1.0 <= v <= 1.0 for v in EMOTION_VECTOR_MAP[e])
                for e in EMOTION_VECTOR_MAP
            )
            self._log("B2-1-3", f"모든 값이 -1.0~1.0 범위: {all_valid}", all_valid)

            # 긍정/부정 감정 분류 확인 (valence 기준)
            positive_emotions = ["기쁨", "행복", "즐거움", "설렘", "만족"]
            negative_emotions = ["불안", "짜증", "스트레스", "분노", "우울", "슬픔", "무기력"]

            positive_correct = all(EMOTION_VECTOR_MAP[e][0] > 0 for e in positive_emotions)
            negative_correct = all(EMOTION_VECTOR_MAP[e][0] < 0 for e in negative_emotions)

            self._log("B2-2-1", f"긍정 감정 valence > 0: {positive_correct}", positive_correct)
            self._log("B2-2-2", f"부정 감정 valence < 0: {negative_correct}", negative_correct)

            # 중립 감정 확인
            neutral = EMOTION_VECTOR_MAP.get("중립")
            is_neutral = neutral == (0.0, 0.0, 0.0) or neutral == (0.0, 0.0, 0.5)
            self._log("B2-2-3", f"중립 감정 = (0, 0, ~0): {is_neutral}", is_neutral)

            # 피곤/무기력 감정 확인 (낮은 arousal)
            tired_emotions = ["피곤", "무기력"]
            tired_low_arousal = all(EMOTION_VECTOR_MAP[e][1] < -0.5 for e in tired_emotions)
            self._log("B2-3-1", f"피곤/무기력 arousal < -0.5: {tired_low_arousal}", tired_low_arousal)

            # 분노/스트레스 감정 확인 (높은 arousal)
            high_arousal_neg = ["분노", "스트레스", "짜증"]
            high_arousal_correct = all(EMOTION_VECTOR_MAP[e][1] > 0.3 for e in high_arousal_neg)
            self._log("B2-3-2", f"분노/스트레스 arousal > 0.3: {high_arousal_correct}", high_arousal_correct)

        except Exception as e:
            self._log("B2-1-1", f"감정 벡터 매핑 테스트 실패: {e}", False)

    async def test_b2_4_vector_update(self):
        """B2-4: 감정 벡터 업데이트 로직 테스트"""
        print("\n" + "="*70)
        print("B2-4: 감정 벡터 업데이트 로직 테스트")
        print("="*70)

        test_user_id = "test_b2_user_4"
        cache_key = f"emotion_vector:{test_user_id}"

        # 기존 데이터 삭제
        try:
            await redis_client.delete(cache_key)
        except:
            pass

        try:
            # 초기 상태 조회 (없으면 초기값 생성)
            initial = await self.dm.get_emotion_vector(test_user_id)
            is_initial = initial == {"v": 0.0, "a": 0.0, "i": 0.5}
            self._log("B2-4-1", f"초기 감정 벡터 확인: {is_initial}", is_initial)

            # 긍정 감정 입력 ("기쁨" = (0.8, 0.6, 0.1))
            updated_1 = await self.dm._update_emotion_vector(test_user_id, "기쁨")
            v_increased = updated_1["v"] > initial["v"]
            a_increased = updated_1["a"] > initial["a"]

            self._log("B2-4-2", f"'기쁨' 후 valence/arousal 증가: {v_increased and a_increased}", v_increased and a_increased)
            self._log("B2-4-3", f"valence: {initial['v']} → {updated_1['v']}", True)
            self._log("B2-4-4", f"arousal: {initial['a']} → {updated_1['a']}", True)

            # 부정 감정 입력 ("우울" = (-0.8, -0.6, 0.0))
            updated_2 = await self.dm._update_emotion_vector(test_user_id, "우울")
            v_decreased = updated_2["v"] < updated_1["v"]
            a_decreased = updated_2["a"] < updated_1["a"]

            self._log("B2-4-5", f"'우울' 후 valence/arousal 감소: {v_decreased and a_decreased}", v_decreased and a_decreased)

            # TTL 확인 (24시간 = 86400초)
            ttl = await redis_client.ttl(cache_key)
            ttl_valid = ttl > 86000  # 약간의 오차 허용
            self._log("B2-4-6", f"24시간 TTL 설정 확인: {ttl_valid}", ttl_valid)

        except Exception as e:
            self._log("B2-4-1", f"감정 벡터 업데이트 테스트 실패: {e}", False)

        # 정리
        await redis_client.delete(cache_key)

    async def test_b2_5_smooth_transition(self):
        """B2-5: 부드러운 전환 (MAX_DELTA_PER_TURN) 테스트"""
        print("\n" + "="*70)
        print("B2-5: 부드러운 전환 테스트")
        print("="*70)

        test_user_id = "test_b2_user_5"
        cache_key = f"emotion_vector:{test_user_id}"

        try:
            await redis_client.delete(cache_key)

            # 중립 상태에서 시작
            await self.dm._update_emotion_vector(test_user_id, "중립")
            current = await self.dm.get_emotion_vector(test_user_id)

            # 극단적 감정 변화: 중립(0,0,0.5) → 기쁨(0.8, 0.6, 0.1)
            after_joy = await self.dm._update_emotion_vector(test_user_id, "기쁨")

            # 변화량이 MAX_DELTA_PER_TURN 이내인지 확인
            delta_v = abs(after_joy["v"] - current["v"])
            delta_a = abs(after_joy["a"] - current["a"])

            v_within_limit = delta_v <= MAX_DELTA_PER_TURN
            a_within_limit = delta_a <= MAX_DELTA_PER_TURN

            self._log("B2-5-1", f"valence 변화량 {delta_v:.3f} ≤ {MAX_DELTA_PER_TURN}: {v_within_limit}", v_within_limit)
            self._log("B2-5-2", f"arousal 변화량 {delta_a:.3f} ≤ {MAX_DELTA_PER_TURN}: {a_within_limit}", a_within_limit)

            # 연속 호출로 점진적 도달 확인
            for _ in range(5):
                await self.dm._update_emotion_vector(test_user_id, "기쁨")

            final = await self.dm.get_emotion_vector(test_user_id)
            approaching_target = final["v"] > 0.5  # 목표 0.8에 근접

            self._log("B2-5-3", f"연속 호출 후 목표값 근접: {approaching_target} (v={final['v']:.3f})", approaching_target)

            # 경계값 테스트: -1.0 ~ 1.0 벗어나지 않음
            await redis_client.delete(cache_key)
            for _ in range(20):  # 다수 호출해도 경계 유지
                await self.dm._update_emotion_vector(test_user_id, "기쁨")

            clamped = await self.dm.get_emotion_vector(test_user_id)
            in_bounds = -1.0 <= clamped["v"] <= 1.0 and -1.0 <= clamped["a"] <= 1.0

            self._log("B2-5-4", f"경계값 준수 (-1.0~1.0): {in_bounds}", in_bounds)

        except Exception as e:
            self._log("B2-5-1", f"부드러운 전환 테스트 실패: {e}", False)

        # 정리
        await redis_client.delete(cache_key)

    async def test_b2_6_vector_to_prompt(self):
        """B2-6: 벡터 → 프롬프트 설명 변환 테스트"""
        print("\n" + "="*70)
        print("B2-6: 벡터 → 프롬프트 설명 변환 테스트")
        print("="*70)

        try:
            # 매우 지치고 가라앉은 상태 (v ≤ -0.6, a ≤ -0.4)
            depressed_prompt = _vector_to_prompt_description({"v": -0.8, "a": -0.6, "i": 0.3})
            has_depression_desc = "지치고 가라않은" in depressed_prompt or "차분하고 느린" in depressed_prompt
            self._log("B2-6-1", f"우울 상태 설명: {has_depression_desc}", has_depression_desc)

            # 활기차고 긍정적인 상태 (v ≥ 0.6, a ≥ 0.5)
            energetic_prompt = _vector_to_prompt_description({"v": 0.8, "a": 0.7, "i": 0.5})
            has_energy_desc = "활기차고 긍정적" in energetic_prompt or "신나게" in energetic_prompt
            self._log("B2-6-2", f"활기찬 상태 설명: {has_energy_desc}", has_energy_desc)

            # 매우 친밀한 상태 (i ≥ 0.8)
            intimate_prompt = _vector_to_prompt_description({"v": 0.5, "a": 0.2, "i": 0.9})
            has_intimacy_desc = "친밀한" in intimate_prompt or "솔직하고 가까운" in intimate_prompt
            self._log("B2-6-3", f"친밀한 상태 설명: {has_intimacy_desc}", has_intimacy_desc)

            # 중립 상태 (빈 문자열 또는 기본 설명)
            neutral_prompt = _vector_to_prompt_description({"v": 0.0, "a": 0.0, "i": 0.5})
            is_empty_or_neutral = neutral_prompt == "" or len(neutral_prompt) < 100
            self._log("B2-6-4", f"중립 상태는 간결한 설명: {is_empty_or_neutral}", is_empty_or_neutral)

        except Exception as e:
            self._log("B2-6-1", f"벡터→프롬프트 변환 테스트 실패: {e}", False)

    async def test_b2_integration_prompt_builder(self):
        """B2 통합: PromptBuilder에서 emotion_vector 파라미터 검증"""
        print("\n" + "="*70)
        print("B2 통합: PromptBuilder emotion_vector 파라미터 테스트")
        print("="*70)

        try:
            # 긍정적 높은 에너지 벡터
            positive_vector = {"v": 0.8, "a": 0.7, "i": 0.6}
            prompt_positive = self.pb.build_system_prompt(emotion_vector=positive_vector)

            has_emotion_block = "현재 감정 상태 벡터" in prompt_positive or "감정 상태" in prompt_positive
            self._log("B2-I1-1", f"감정 벡터 블록 추가: {has_emotion_block}", has_emotion_block)

            # 부정적 낮은 에너지 벡터
            negative_vector = {"v": -0.7, "a": -0.5, "i": 0.3}
            prompt_negative = self.pb.build_system_prompt(emotion_vector=negative_vector)

            has_negative_desc = "지치" in prompt_negative or "가라앉" in prompt_negative or "무겁" in prompt_negative
            self._log("B2-I1-2", f"부정적 감정 설명 포함: {has_negative_desc}", has_negative_desc)

            # 기존 프롬프트 구조 유지 확인
            has_base = "정원사" in prompt_positive
            self._log("B2-I1-3", f"기본 프롬프트 유지: {has_base}", has_base)

        except Exception as e:
            self._log("B2-I1-1", f"PromptBuilder 통합 테스트 실패: {e}", False)

    async def test_b2_integration_response_generator(self):
        """B2 통합: ResponseGenerator에서 emotion_vector 전달 검증"""
        print("\n" + "="*70)
        print("B2 통합: ResponseGenerator emotion_vector 전달 테스트")
        print("="*70)

        try:
            test_user_id = "test_b2_user_rg"

            # ResponseGenerator.generate() 호출 시 emotion_vector 전달
            # (실제 LLM 호출은 mock 없이는 어려우므로 파라미터 전달만 확인)

            # generate_empathetic_response() 메서드 확인
            import inspect
            sig = inspect.signature(self.rg.generate_empathetic_response)
            has_emotion_vector_param = "emotion_vector" in sig.parameters

            self._log("B2-I2-1", f"generate_empathetic_response에 emotion_vector 파라미터: {has_emotion_vector_param}", has_emotion_vector_param)

            # _build_system_prompt_with_emotion() 시그니처 확인
            sig2 = inspect.signature(self.rg._build_system_prompt_with_emotion)
            has_ev_in_builder = "emotion_vector" in sig2.parameters

            self._log("B2-I2-2", f"_build_system_prompt_with_emotion에 emotion_vector 파라미터: {has_ev_in_builder}", has_ev_in_builder)

        except Exception as e:
            self._log("B2-I2-1", f"ResponseGenerator 통합 테스트 실패: {e}", False)

    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*70)
        print("B2 통합 테스트 결과 요약")
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
            print("🎉 모든 테스트 통과! B2 구현 완료.")
        else:
            print(f"⚠️ {total_failed}개 테스트 실패 - 확인 필요.")
        print("="*70)


async def main():
    tester = B2IntegrationTester()

    print("Phase B2 통합 테스트 시작...\n")

    await tester.test_b2_1_emotion_vector_map()
    await tester.test_b2_4_vector_update()
    await tester.test_b2_5_smooth_transition()
    await tester.test_b2_6_vector_to_prompt()
    await tester.test_b2_integration_prompt_builder()
    await tester.test_b2_integration_response_generator()

    tester.print_summary()


# ========== B2-7: 감정 벡터 실제 갱신 테스트 추가 ==========
import pytest


@pytest.mark.asyncio
class TestEmotionVectorUpdate:
    """B2-7: 감정 벡터 실제 갱신 테스트"""

    async def test_joy_increases_valence(self):
        """기쁨 → valence 증가"""
        manager = DialogueManager()
        user_id = "test_b2_joy"

        # 초기화
        await redis_client.delete(f"emotion_vector:{user_id}")

        # 기쁜 메시지
        await manager.generate_response(
            user_id=user_id,
            user_message="딸이 방문해서 정말 기뻐요 ㅋㅋ"
        )

        # 벡터 확인
        vector = await redis_client.get_json(f"emotion_vector:{user_id}")

        assert vector is not None
        assert vector["v"] > 0.5, f"valence should be > 0.5, got {vector['v']}"
        assert vector["a"] > 0.5, f"arousal should be > 0.5, got {vector['a']}"

    async def test_sadness_decreases_valence(self):
        """슬픔 → valence 감소"""
        manager = DialogueManager()
        user_id = "test_b2_sadness"

        # 초기화
        await redis_client.delete(f"emotion_vector:{user_id}")

        # 슬픈 메시지
        await manager.generate_response(
            user_id=user_id,
            user_message="며칠 전 지나가신 친구분 생각하니까 너무 슬퍼요 ㅠㅠ"
        )

        # 벡터 확인
        vector = await redis_client.get_json(f"emotion_vector:{user_id}")

        assert vector is not None
        assert vector["v"] < 0.4, f"valence should be < 0.4, got {vector['v']}"

    async def test_anger_increases_arousal(self):
        """분노 → arousal 증가"""
        manager = DialogueManager()
        user_id = "test_b2_anger"

        # 초기화
        await redis_client.delete(f"emotion_vector:{user_id}")

        # 화난 메시지
        await manager.generate_response(
            user_id=user_id,
            user_message="정말 화가 나요 너무 속상해서..."
        )

        # 벡터 확인
        vector = await redis_client.get_json(f"emotion_vector:{user_id}")

        assert vector is not None
        assert vector["a"] > 0.6, f"arousal should be > 0.6 for anger, got {vector['a']}"
        assert vector["v"] < 0.4, f"valence should be < 0.4 for anger"

    async def test_emotion_delta_clamping(self):
        """한 턴 최대 변화량 제한 (MAX_DELTA_PER_TURN = 0.25)"""
        manager = DialogueManager()
        user_id = "test_b2_clamp"

        # 초기화
        await redis_client.delete(f"emotion_vector:{user_id}")

        # 극단적으로 기쁜 메시지
        await manager.generate_response(
            user_id=user_id,
            user_message="대박 최고의 행복입니다!!! ㅋㅋㅋㅋ"
        )

        # 벡터 확인
        vector = await redis_client.get_json(f"emotion_vector:{user_id}")

        # 초기값이 {"v": 0.0, "a": 0.0, "i": 0.5}이므로 최대 0.25까지만 증가 가능
        assert vector["v"] <= 0.25, f"valence should be clamped to 0.25, got {vector['v']}"
# ================================================================


if __name__ == "__main__":
    asyncio.run(main())
