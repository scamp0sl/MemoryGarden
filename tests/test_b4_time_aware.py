"""
Phase B4 통합 테스트 스크립트

시간 인식형 대화 (Time-Aware Dialogue) 기능 검증
시간대별 인사, 경과 시간 기반 Gap 메시지 생성 확인
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.dialogue.dialogue_manager import DialogueManager
from core.dialogue.time_aware import (
    TimeAwareDialogue,
    TIME_GREETING_TEMPLATES,
    GAP_MESSAGE_TEMPLATES,
    TIME_OF_DAY
)
from database.redis_client import redis_client


class B4IntegrationTester:
    """B4 통합 테스터"""

    def __init__(self):
        self.dm = DialogueManager()
        self.tad = TimeAwareDialogue(seed=42)  # 시드 고정 for reproducibility
        self.results = {
            "B4-1": {"passed": 0, "failed": 0, "details": []},
            "B4-2": {"passed": 0, "failed": 0, "details": []},
            "B4-3": {"passed": 0, "failed": 0, "details": []},
            "B4-I": {"passed": 0, "failed": 0, "details": []},
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

    async def test_b4_1_time_of_day_detection(self):
        """B4-1: 시간대 감지 테스트"""
        print("\n" + "="*70)
        print("B4-1: 시간대 감지 테스트")
        print("="*70)

        try:
            # 아침 (6-10시)
            morning = datetime(2026, 3, 26, 7, 30)
            time_morning = self.tad.get_time_of_day(morning)
            self._log("B4-1-1", f"07:30 → 'morning': {time_morning == 'morning'}", time_morning == 'morning')

            # 점심 (11-13시)
            noon = datetime(2026, 3, 26, 12, 0)
            time_noon = self.tad.get_time_of_day(noon)
            self._log("B4-1-2", f"12:00 → 'noon': {time_noon == 'noon'}", time_noon == 'noon')

            # 오후 (14-17시)
            afternoon = datetime(2026, 3, 26, 15, 30)
            time_afternoon = self.tad.get_time_of_day(afternoon)
            self._log("B4-1-3", f"15:30 → 'afternoon': {time_afternoon == 'afternoon'}", time_afternoon == 'afternoon')

            # 저녁 (18-21시)
            evening = datetime(2026, 3, 26, 19, 45)
            time_evening = self.tad.get_time_of_day(evening)
            self._log("B4-1-4", f"19:45 → 'evening': {time_evening == 'evening'}", time_evening == 'evening')

            # 밤 (22-5시)
            night = datetime(2026, 3, 26, 23, 0)
            time_night = self.tad.get_time_of_day(night)
            self._log("B4-1-5", f"23:00 → 'night': {time_night == 'night'}", time_night == 'night')

            # 새벽 (22-5시, 다음날)
            dawn = datetime(2026, 3, 27, 3, 0)
            time_dawn = self.tad.get_time_of_day(dawn)
            self._log("B4-1-6", f"03:00 (다음날) → 'night': {time_dawn == 'night'}", time_dawn == 'night')

        except Exception as e:
            self._log("B4-1-1", f"시간대 감지 테스트 실패: {e}", False)

    async def test_b4_1_last_interaction_tracking(self):
        """B4-1: 마지막 상호작용 시간 추적 테스트"""
        print("\n" + "="*70)
        print("B4-1: 마지막 상호작용 시간 추적 테스트")
        print("="*70)

        test_user_id = "test_b4_user_1"

        try:
            # 기존 데이터 삭제
            await redis_client.delete(f"last_interaction:{test_user_id}")

            # 초기 조회 (None)
            last1 = await self.dm.get_last_interaction(test_user_id)
            self._log("B4-1-L1", f"초기 상태: None 반환 = {last1 is None}", last1 is None)

            # 업데이트
            await self.dm.update_last_interaction(test_user_id)
            last2 = await self.dm.get_last_interaction(test_user_id)
            self._log("B4-1-L2", f"업데이트 후 시간 저장: {last2 is not None}", last2 is not None)

            # 경과 시간 계산 (0시간 미만)
            hours = await self.dm.get_hours_since_last_interaction(test_user_id)
            within_1min = hours is not None and hours < 1/60  # 1분 미만
            self._log("B4-1-L3", f"경과 시간 < 1분: {within_1min} ({hours:.4f}시간)", within_1min)

            # 과거 시간 설정 테스트
            past_time = (datetime.now() - timedelta(hours=5)).isoformat()
            await redis_client.set(f"last_interaction:{test_user_id}", past_time)
            hours2 = await self.dm.get_hours_since_last_interaction(test_user_id)
            approx_5h = 4.9 <= hours2 <= 5.1  # 약간의 오차 허용
            self._log("B4-1-L4", f"5시간 전 설정: 경과 시간 ~5시간 = {approx_5h} ({hours2:.2f}시간)", approx_5h)

        except Exception as e:
            self._log("B4-1-L1", f"마지막 상호작용 추적 테스트 실패: {e}", False)

        # 정리
        await redis_client.delete(f"last_interaction:{test_user_id}")

    async def test_b4_2_gap_hours_categorization(self):
        """B4-2: 경과 시간 범주화 테스트"""
        print("\n" + "="*70)
        print("B4-2: 경과 시간 범주화 테스트")
        print("="*70)

        try:
            # short (<3시간)
            cat1 = self.tad.categorize_gap_hours(1.5)
            self._log("B4-2-1", f"1.5시간 → 'short': {cat1 == 'short'}", cat1 == 'short')

            # medium (3-12시간)
            cat2 = self.tad.categorize_gap_hours(6.5)
            self._log("B4-2-2", f"6.5시간 → 'medium': {cat2 == 'medium'}", cat2 == 'medium')

            # long (12-24시간)
            cat3 = self.tad.categorize_gap_hours(18.5)
            self._log("B4-2-3", f"18.5시간 → 'long': {cat3 == 'long'}", cat3 == 'long')

            # extended (>24시간)
            cat4 = self.tad.categorize_gap_hours(48.0)
            self._log("B4-2-4", f"48시간 → 'extended': {cat4 == 'extended'}", cat4 == 'extended')

            # 경계값 테스트
            cat5 = self.tad.categorize_gap_hours(3.0)
            self._log("B4-2-5", f"3.0시간 (경계) → 'medium': {cat5 == 'medium'}", cat5 == 'medium')

        except Exception as e:
            self._log("B4-2-1", f"경과 시간 범주화 테스트 실패: {e}", False)

    async def test_b4_3_time_greeting_generation(self):
        """B4-3: 시간대별 인사 생성 테스트"""
        print("\n" + "="*70)
        print("B4-3: 시간대별 인사 생성 테스트")
        print("="*70)

        try:
            # 아침 인사
            tad_morning = TimeAwareDialogue(seed=1)
            msg_morning = tad_morning.generate_time_greeting("morning")
            has_morning_keyword = any(kw in msg_morning for kw in ["아침", "상쾌", "일어나"])
            self._log("B4-3-1", f"아침 인사: '{msg_morning[:30]}...' 키워드 포함: {has_morning_keyword}", has_morning_keyword)

            # 점심 인사
            tad_noon = TimeAwareDialogue(seed=2)
            msg_noon = tad_noon.generate_time_greeting("noon")
            has_noon_keyword = any(kw in msg_noon for kw in ["점심", "식사", "하루의 중간"])
            self._log("B4-3-2", f"점심 인사: '{msg_noon[:30]}...' 키워드 포함: {has_noon_keyword}", has_noon_keyword)

            # 저녁 인사
            tad_evening = TimeAwareDialogue(seed=3)
            msg_evening = tad_evening.generate_time_greeting("evening")
            has_evening_keyword = any(kw in msg_evening for kw in ["저녁", "하루의 마무리", "노을"])
            self._log("B4-3-3", f"저녁 인사: '{msg_evening[:30]}...' 키워드 포함: {has_evening_keyword}", has_evening_keyword)

            # 밤 인사
            tad_night = TimeAwareDialogue(seed=4)
            msg_night = tad_night.generate_time_greeting("night")
            has_night_keyword = any(kw in msg_night for kw in ["밤", "푹 쉬", "별"])
            self._log("B4-3-4", f"밤 인사: '{msg_night[:30]}...' 키워드 포함: {has_night_keyword}", has_night_keyword)

            # 한글 이모지 포함 확인 (ㅎㅎ, ㅠㅠ 등 허용)
            has_korean_emoticon = any(c in msg_morning for c in ["ㅎㅎ", "ㅠㅠ", "ㅋㅋ"])
            self._log("B4-3-5", f"아침 인사 한글 이모지 포함: {has_korean_emoticon}", has_korean_emoticon)

        except Exception as e:
            self._log("B4-3-1", f"시간대별 인사 생성 테스트 실패: {e}", False)

    async def test_b4_3_gap_message_generation(self):
        """B4-3: Gap 메시지 생성 테스트"""
        print("\n" + "="*70)
        print("B4-3: Gap 메시지 생성 테스트")
        print("="*70)

        try:
            # short gap (<3시간)
            tad1 = TimeAwareDialogue(seed=10)
            msg1 = tad1.generate_gap_message(1.5)
            has_short_keyword = any(kw in msg1 for kw in ["바로", "금방", "이어서"])
            self._log("B4-3-G1", f"Short Gap(1.5h) 키워드: {has_short_keyword}", has_short_keyword)

            # medium gap (3-12시간)
            tad2 = TimeAwareDialogue(seed=11)
            msg2 = tad2.generate_gap_message(6.5)
            has_medium_keyword = any(kw in msg2 for kw in ["반갑", "오랜만", "기뻐"])
            self._log("B4-3-G2", f"Medium Gap(6.5h) 키워드: {has_medium_keyword}", has_medium_keyword)

            # long gap (12-24시간)
            tad3 = TimeAwareDialogue(seed=12)
            msg3 = tad3.generate_gap_message(18.5)
            has_long_keyword = any(kw in msg3 for kw in ["어제", "하루", "24시간"])
            self._log("B4-3-G3", f"Long Gap(18.5h) 키워드: {has_long_keyword}", has_long_keyword)

            # extended gap (>24시간)
            tad4 = TimeAwareDialogue(seed=13)
            msg4 = tad4.generate_gap_message(48.0)
            has_extended_keyword = any(kw in msg4 for kw in ["오랫동안", "정말 오랜만", "쓸쓸"])
            self._log("B4-3-G4", f"Extended Gap(48h) 키워드: {has_extended_keyword}", has_extended_keyword)

            # 정원 메타포 포함 확인 (이모지 제거됨)
            has_garden_mention = "정원" in msg2
            self._log("B4-3-G5", f"정원 메타포 포함: {has_garden_mention}", has_garden_mention)

        except Exception as e:
            self._log("B4-3-G1", f"Gap 메시지 생성 테스트 실패: {e}", False)

    async def test_b4_integration_combined_message(self):
        """B4 통합: 종합 메시지 생성 테스트"""
        print("\n" + "="*70)
        print("B4 통합: 종합 메시지 생성 테스트")
        print("="*70)

        test_user_id = "test_b4_user_integration"

        try:
            # 초기 상태에서 Gap 메시지 생성 (None 반환)
            gap1 = await self.dm.generate_gap_message(test_user_id)
            is_none = gap1 is None
            self._log("B4-I-1", f"첫 상호작용 시 Gap 메시지 = None: {is_none}", is_none)

            # 마지막 상호작용 업데이트
            await self.dm.update_last_interaction(test_user_id)

            # 즉시 재조회 (short gap)
            gap2 = await self.dm.generate_gap_message(test_user_id)
            has_short = gap2 is not None and ("바로" in gap2 or "금방" in gap2 or "이어서" in gap2 or "좋아요" in gap2)
            self._log("B4-I-2", f"즉시 Gap 메시지 생성(short): {has_short}", has_short)

            # 5시간 전으로 설정
            past = (datetime.now() - timedelta(hours=5)).isoformat()
            await redis_client.set(f"last_interaction:{test_user_id}", past)

            gap3 = await self.dm.generate_gap_message(test_user_id)
            has_medium = gap3 is not None and ("반갑" in gap3 or "오랜만" in gap3 or "기다리고" in gap3 or "시간" in gap3)
            self._log("B4-I-3", f"5시간 Gap 메시지(medium): {has_medium}", has_medium)

            # 종합 메시지 직접 생성 (시드 고정)
            tad_combined = TimeAwareDialogue(seed=100)
            combined = tad_combined.generate_combined_message(
                hours_since_last=28.5,
                now=datetime(2026, 3, 26, 19, 30),  # 저녁
                include_garden_mention=True
            )
            # 더 유연한 키워드 검증: 시간대 관련 키워드 + Gap 관련 키워드
            has_time_keyword = any(kw in combined for kw in ["저녁", "하루", "밤", "노을"])
            has_gap_keyword = any(kw in combined for kw in ["오랫", "오랜만", "다시", "돌아오", "활기", "비어있"])
            has_both = has_time_keyword and has_gap_keyword
            self._log("B4-I-4", f"종합 메시지(저녁+28h): 시간+Gap 포함 = {has_both}", has_both)

            # 정원 메타포 포함 (이모지 제거됨)
            has_garden = "정원" in combined
            self._log("B4-I-5", f"종합 메시지 정원 메타포: {has_garden}", has_garden)

        except Exception as e:
            self._log("B4-I-1", f"종합 메시지 테스트 실패: {e}", False)

        # 정리
        await redis_client.delete(f"last_interaction:{test_user_id}")

    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*70)
        print("B4 통합 테스트 결과 요약")
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
            print("🎉 모든 테스트 통과! B4 구현 완료.")
        else:
            print(f"⚠️ {total_failed}개 테스트 실패 - 확인 필요.")
        print("="*70)


async def main():
    tester = B4IntegrationTester()

    print("Phase B4 통합 테스트 시작...\n")

    await tester.test_b4_1_time_of_day_detection()
    await tester.test_b4_1_last_interaction_tracking()
    await tester.test_b4_2_gap_hours_categorization()
    await tester.test_b4_3_time_greeting_generation()
    await tester.test_b4_3_gap_message_generation()
    await tester.test_b4_integration_combined_message()

    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
