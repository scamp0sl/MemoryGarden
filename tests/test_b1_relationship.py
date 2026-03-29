"""
Phase B1 통합 테스트 스크립트

관계 모델 (Relationship Stage) 기능 검증
5단계 Stage에 따른 사만다의 말투 조절 확인
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.dialogue.dialogue_manager import DialogueManager
from core.dialogue.prompt_builder import PromptBuilder
from database.redis_client import redis_client


class B1IntegrationTester:
    """B1 통합 테스터"""

    def __init__(self):
        self.dm = DialogueManager()
        self.pb = PromptBuilder()
        self.results = {
            "B1-1": {"passed": 0, "failed": 0, "details": []},
            "B1-2": {"passed": 0, "failed": 0, "details": []},
            "B1-3": {"passed": 0, "failed": 0, "details": []},
            "B1-4": {"passed": 0, "failed": 0, "details": []},
        }

    def _log(self, test_name: str, message: str, passed: bool = None):
        """테스트 결과 로그"""
        status = "✅" if passed else "❌" if passed is not None else "ℹ️"
        print(f"{status} [{test_name}] {message}")

        if passed is not None:
            # task_key 추출: "B1-1-1" → "B1-1"
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

    async def test_b1_1_relationship_init(self):
        """B1-1: 관계 데이터 초기화 테스트"""
        print("\n" + "="*70)
        print("B1-1: 관계 데이터 초기화 테스트")
        print("="*70)

        test_user_id = "test_b1_user_1"
        cache_key = f"relationship:{test_user_id}"

        # 기존 데이터 삭제
        try:
            await redis_client.delete(cache_key)
            self._log("B1-1-1", "기존 데이터 삭제 완료", True)
        except Exception as e:
            self._log("B1-1-1", f"삭제 실패: {e}", False)

        # 초기화
        try:
            rel = await self.dm._get_or_init_relationship(test_user_id)
            has_stage = "stage" in rel
            has_turns = "total_turns" in rel
            has_first = "first_interaction" in rel
            is_stage_0 = rel.get("stage") == 0

            self._log("B1-1-2", "관계 데이터 초기화 성공", has_stage and has_turns and has_first)
            self._log("B1-1-3", f"초기 Stage = 0 확인: {is_stage_0}", is_stage_0)
        except Exception as e:
            self._log("B1-1-2", f"초기화 실패: {e}", False)

        # 정리
        await redis_client.delete(cache_key)

    async def test_b1_2_stage_upgrade(self):
        """B1-2: Stage 진급 로직 테스트"""
        print("\n" + "="*70)
        print("B1-2: Stage 진급 로직 테스트")
        print("="*70)

        test_user_id = "test_b1_user_2"
        cache_key = f"relationship:{test_user_id}"

        # 초기화
        await redis_client.delete(cache_key)

        try:
            # Stage 0 → 1 (20턴)
            for i in range(20):
                await self.dm._update_relationship_stage(test_user_id, "기쁨")

            rel = await self.dm._get_or_init_relationship(test_user_id)
            stage_1 = rel.get("stage") == 1

            self._log("B1-2-1", f"20턴 후 Stage 1 진급: {stage_1} (현재: {rel.get('stage')})", stage_1)

            # Stage 1 → 2 (7일 + 긍정 3회)
            # 첫 번째 상호작용을 7일 전으로 설정하고 긍정 3회 추가
            from datetime import datetime, timedelta
            first_interaction = (datetime.now() - timedelta(days=8)).isoformat()
            rel["first_interaction"] = first_interaction
            rel["positive_events"] = 3
            await redis_client.set_json(cache_key, rel)

            await self.dm._update_relationship_stage(test_user_id, "기쁨")
            rel = await self.dm._get_or_init_relationship(test_user_id)
            stage_2 = rel.get("stage") == 2

            self._log("B1-2-2", f"7일+긍정3회 후 Stage 2 진급: {stage_2} (현재: {rel.get('stage')})", stage_2)

            # Stage 2 → 3 (14일 + 긍정 10회)
            rel["first_interaction"] = (datetime.now() - timedelta(days=15)).isoformat()
            rel["positive_events"] = 10
            await redis_client.set_json(cache_key, rel)

            await self.dm._update_relationship_stage(test_user_id, "기쁨")
            rel = await self.dm._get_or_init_relationship(test_user_id)
            stage_3 = rel.get("stage") == 3

            self._log("B1-2-3", f"14일+긍정10회 후 Stage 3 진급: {stage_3} (현재: {rel.get('stage')})", stage_3)

        except Exception as e:
            self._log("B1-2-1", f"Stage 진급 실패: {e}", False)

        # 정리
        await redis_client.delete(cache_key)

    async def test_b1_3_stage_prompts(self):
        """B1-3: Stage별 프롬프트 블록 테스트"""
        print("\n" + "="*70)
        print("B1-3: Stage별 프롬프트 블록 테스트")
        print("="*70)

        try:
            # Stage 0
            prompt_0 = await self.pb.build_system_prompt(user_id="test_b1", relationship_stage=0)
            has_stage_0 = "처음 알아가는 사이" in prompt_0
            self._log("B1-3-1", f"Stage 0 프롬프트 포함: {has_stage_0}", has_stage_0)

            # Stage 1
            prompt_1 = await self.pb.build_system_prompt(user_id="test_b1", relationship_stage=1)
            has_stage_1 = "조금씩 친해지는 중" in prompt_1
            self._log("B1-3-2", f"Stage 1 프롬프트 포함: {has_stage_1}", has_stage_1)

            # Stage 2
            prompt_2 = await self.pb.build_system_prompt(user_id="test_b1", relationship_stage=2)
            has_stage_2 = "좋은 친구 사이" in prompt_2
            self._log("B1-3-3", f"Stage 2 프롬프트 포함: {has_stage_2}", has_stage_2)

            # Stage 3
            prompt_3 = await self.pb.build_system_prompt(user_id="test_b1", relationship_stage=3)
            has_stage_3 = "매우 친한 친구" in prompt_3
            self._log("B1-3-4", f"Stage 3 프롬프트 포함: {has_stage_3}", has_stage_3)

            # Stage 4
            prompt_4 = await self.pb.build_system_prompt(user_id="test_b1", relationship_stage=4)
            has_stage_4 = "깊은 친구" in prompt_4
            self._log("B1-3-5", f"Stage 4 프롬프트 포함: {has_stage_4}", has_stage_4)

            # 기본 프롬프트 유지 확인
            has_base = "정원사" in prompt_0
            self._log("B1-3-6", f"기본 프롬프트 유지: {has_base}", has_base)

        except Exception as e:
            self._log("B1-3-1", f"Stage 프롬프트 테스트 실패: {e}", False)

    async def test_b1_4_get_stage(self):
        """B1-4: Stage 조회 메서드 테스트"""
        print("\n" + "="*70)
        print("B1-4: Stage 조회 메서드 테스트")
        print("="*70)

        test_user_id = "test_b1_user_4"

        try:
            # 신규 사용자 Stage 조회
            stage_new = await self.dm.get_relationship_stage(test_user_id)
            is_zero = stage_new == 0
            self._log("B1-4-1", f"신규 사용자 Stage 0 확인: {is_zero}", is_zero)

            # 20턴 후 Stage 조회
            cache_key = f"relationship:{test_user_id}"
            for i in range(20):
                await self.dm._update_relationship_stage(test_user_id, "기쁨")

            stage_updated = await self.dm.get_relationship_stage(test_user_id)
            is_one = stage_updated == 1
            self._log("B1-4-2", f"20턴 후 Stage 1 확인: {is_one}", is_one)

        except Exception as e:
            self._log("B1-4-1", f"Stage 조회 실패: {e}", False)

        # 정리
        await redis_client.delete(cache_key)

    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*70)
        print("B1 통합 테스트 결과 요약")
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
            print("🎉 모든 테스트 통과! B1 구현 완료.")
        else:
            print(f"⚠️ {total_failed}개 테스트 실패 - 확인 필요.")
        print("="*70)


"""B1: Relationship Stage 테스트 (recovery_events 검증)"""

import pytest
from core.dialogue.dialogue_manager import DialogueManager
from database.redis_client import redis_client


@pytest.mark.asyncio
async def test_b1_recovery_events_increment():
    """B1 수정: 갈등 후 긍정 전환 시 recovery_events 증가"""
    manager = DialogueManager()
    user_id = "test_b1_recovery"

    # 초기화
    await redis_client.delete(f"relationship:{user_id}")

    # 1. 갈등 상황 (부정 감정)
    await manager.generate_response(
        user_id=user_id,
        user_message="속상해서 마음이 너무 힘들어요"
    )

    # 2. 긍정 전환
    await manager.generate_response(
        user_id=user_id,
        user_message="그래도 친구가 위로해줘서 기분이 나아졌어요"
    )

    # 3. recovery_events 확인
    rel = await manager._get_or_init_relationship(user_id)
    assert rel["recovery_events"] >= 1, f"recovery_events should be >= 1, got {rel['recovery_events']}"

    # 정리
    await redis_client.delete(f"relationship:{user_id}")


@pytest.mark.asyncio
async def test_b1_stage_4_progression():
    """Stage 3 → 4 진급: recovery_events 조건 충족"""
    manager = DialogueManager()
    user_id = "test_b1_stage4"

    # 초기화
    await redis_client.delete(f"relationship:{user_id}")

    # Redis에 Stage 3 조건 데이터 직접 주입
    # Stage 3 → 4 조건: total_days >= 30 AND recovery_events >= 1
    from datetime import datetime, timedelta
    await redis_client.set_json(f"relationship:{user_id}", {
        "stage": 3,
        "total_turns": 200,
        "total_days": 35,
        "positive_events": 50,
        "conflict_events": 3,
        "recovery_events": 0,
        "_was_negative": False,
        "first_interaction": (datetime.now() - timedelta(days=35)).isoformat(),
        "last_interaction": datetime.now().isoformat(),
    })

    # 갈등 상태 설정 (_was_negative = True)
    rel_before = await redis_client.get_json(f"relationship:{user_id}")
    rel_before["_was_negative"] = True
    await redis_client.set_json(f"relationship:{user_id}", rel_before)

    # 긍정 전환 → recovery_events 증가 → Stage 4 진급
    await manager.generate_response(user_id=user_id, user_message="위로해줘서 고마워요 ㅎㅎ")

    # Stage 4 진급 확인
    rel = await manager._get_or_init_relationship(user_id)
    assert rel["stage"] == 4, f"Expected stage 4, got {rel['stage']}"
    assert rel["recovery_events"] >= 1, f"Expected recovery_events >= 1, got {rel['recovery_events']}"

    # 정리
    await redis_client.delete(f"relationship:{user_id}")


async def main():
    tester = B1IntegrationTester()

    print("Phase B1 통합 테스트 시작...\n")

    await tester.test_b1_1_relationship_init()
    await tester.test_b1_2_stage_upgrade()
    await tester.test_b1_3_stage_prompts()
    await tester.test_b1_4_get_stage()

    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
