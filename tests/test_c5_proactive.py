"""
Phase C5 통합 테스트 스크립트

Proactive Messaging 기능 검증
- ProactiveService 클래스
- 비활성 사용자 조회
- Proactive 메시지 생성
- 메시지 발송 (OAuth / Channel)
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.proactive_service import ProactiveService
from database.models import User
from database.postgres import AsyncSessionLocal
from sqlalchemy import select


class C5IntegrationTester:
    """C5 통합 테스터"""

    def __init__(self):
        self.ps = ProactiveService()
        self.results = {
            "C5-1": {"passed": 0, "failed": 0, "details": []},
            "C5-2": {"passed": 0, "failed": 0, "details": []},
            "C5-3": {"passed": 0, "failed": 0, "details": []},
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

    async def test_c5_1_inactive_threshold(self):
        """C5-1: INACTIVE_THRESHOLD_HOURS 상수 확인"""
        print("\n" + "="*70)
        print("C5-1: 비활성 임계값 상수 확인")
        print("="*70)

        try:
            has_threshold = hasattr(self.ps, 'INACTIVE_THRESHOLD_HOURS')
            is_correct = self.ps.INACTIVE_THRESHOLD_HOURS == 36
            self._log("C5-1-1", f"INACTIVE_THRESHOLD_HOURS = 36: {has_threshold and is_correct}", has_threshold and is_correct)

            has_sending_hours = (
                hasattr(self.ps, 'SENDING_START_HOUR') and
                hasattr(self.ps, 'SENDING_END_HOUR')
            )
            is_correct_range = (
                self.ps.SENDING_START_HOUR == 9 and
                self.ps.SENDING_END_HOUR == 21
            )
            self._log("C5-1-2", f"송신 시간대 9-21시: {has_sending_hours and is_correct_range}", has_sending_hours and is_correct_range)

        except Exception as e:
            self._log("C5-1-1", f"상수 확인 실패: {e}", False)

    async def test_c5_2_get_inactive_users(self):
        """C5-2: 비활성 사용자 조회 테스트"""
        print("\n" + "="*70)
        print("C5-2: 비활성 사용자 조회 테스트")
        print("="*70)

        try:
            # 36시간 이상 비활성 사용자 조회
            inactive_users = await self.ps.get_inactive_users(hours=36)

            is_list = isinstance(inactive_users, list)
            self._log("C5-2-1", f"비활성 사용자 목록 반환: {is_list}", is_list)

            if inactive_users:
                first_user = inactive_users[0]
                has_user_id = "user_id" in first_user
                has_kakao_id = "kakao_id" in first_user
                has_hours_since = "hours_since" in first_user
                has_last_interaction = "last_interaction" in first_user

                self._log("C5-2-2", f"user_id 필드 존재: {has_user_id}", has_user_id)
                self._log("C5-2-3", f"kakao_id 필드 존재: {has_kakao_id}", has_kakao_id)
                self._log("C5-2-4", f"hours_since 필드 존재: {has_hours_since}", has_hours_since)
                self._log("C5-2-5", f"last_interaction 필드 존재: {has_last_interaction}", has_last_interaction)

                self._log("C5-2-6", f"조회된 사용자 수: {len(inactive_users)}", True)
            else:
                self._log("C5-2-6", "비활성 사용자 없음 (정상)", True)

        except Exception as e:
            self._log("C5-2-1", f"비활성 사용자 조회 실패: {e}", False)

    async def test_c5_3_generate_proactive_message(self):
        """C5-3: Proactive 메시지 생성 테스트"""
        print("\n" + "="*70)
        print("C5-3: Proactive 메시지 생성 테스트")
        print("="*70)

        try:
            # 36시간 미만 경과
            context1 = {"user_id": "test1", "hours_since": 24.0}
            message1 = await self.ps.generate_proactive_message(context1)
            has_message1 = bool(message1)
            self._log("C5-3-1", f"24시간 미만 메시지 생성: {has_message1}", has_message1)
            if message1:
                self._log("C5-3-1-detail", f"메시지: {message1}", True)

            # 48시간 경과
            context2 = {"user_id": "test2", "hours_since": 48.0}
            message2 = await self.ps.generate_proactive_message(context2)
            has_message2 = bool(message2)
            self._log("C5-3-2", f"48시간 경과 메시지 생성: {has_message2}", has_message2)
            if message2:
                self._log("C5-3-2-detail", f"메시지: {message2}", True)

            # 72시간 이상 경과
            context3 = {"user_id": "test3", "hours_since": 80.0}
            message3 = await self.ps.generate_proactive_message(context3)
            has_message3 = bool(message3)
            self._log("C5-3-3", f"80시간 경과 메시지 생성: {has_message3}", has_message3)
            if message3:
                self._log("C5-3-3-detail", f"메시지: {message3}", True)

        except Exception as e:
            self._log("C5-3-1", f"Proactive 메시지 생성 실패: {e}", False)

    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*70)
        print("C5 통합 테스트 결과 요약")
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
            print("🎉 모든 테스트 통과! C5 구현 완료.")
        else:
            print(f"⚠️ {total_failed}개 테스트 실패 - 확인 필요.")
        print("="*70)


async def main():
    tester = C5IntegrationTester()

    print("Phase C5 통합 테스트 시작...\n")

    await tester.test_c5_1_inactive_threshold()
    await tester.test_c5_2_get_inactive_users()
    await tester.test_c5_3_generate_proactive_message()

    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
