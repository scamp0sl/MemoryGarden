"""
스케줄러 테스트 스크립트

DialogueScheduler의 기본 기능을 테스트합니다.
"""

import asyncio
from datetime import time
from core.dialogue.scheduler import DialogueScheduler

async def test_scheduler():
    print("=" * 60)
    print("📅 Testing DialogueScheduler")
    print("=" * 60)

    # 1. 스케줄러 생성
    print("\n1. Creating scheduler...")
    scheduler = DialogueScheduler()
    print("✅ Scheduler created")

    # 2. 스케줄러 시작
    print("\n2. Starting scheduler...")
    await scheduler.start()
    print("✅ Scheduler started")

    # 3. 사용자 스케줄 추가
    print("\n3. Adding user schedule...")
    user_id = "test_user_001"
    result = await scheduler.add_user_schedule(
        user_id=user_id,
        schedule_times=[time(10, 0), time(15, 0), time(20, 0)]
    )
    print(f"✅ Schedule added: {result}")

    # 4. 스케줄 조회
    print("\n4. Getting user schedule...")
    schedule = await scheduler.get_user_schedule(user_id)
    print(f"✅ Schedule retrieved: {schedule}")

    # 5. 다음 실행 시간 확인
    print("\n5. Getting next run time...")
    next_time = scheduler.get_next_run_time(user_id)
    if next_time:
        print(f"✅ Next dialogue at: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("⚠️ No next run time")

    # 6. 모든 스케줄 목록
    print("\n6. Listing all schedules...")
    all_schedules = await scheduler.list_all_schedules()
    print(f"✅ Total schedules: {len(all_schedules)}")

    # 7. 스케줄 제거
    print("\n7. Removing user schedule...")
    removed = await scheduler.remove_user_schedule(user_id)
    print(f"✅ Schedule removed: {removed}")

    # 8. 스케줄러 종료
    print("\n8. Stopping scheduler...")
    await scheduler.stop()
    print("✅ Scheduler stopped")

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_scheduler())
