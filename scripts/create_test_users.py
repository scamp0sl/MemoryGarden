"""
테스트 사용자 생성 스크립트

3명의 테스트 사용자를 생성하고 스케줄을 설정합니다.

Usage:
    python scripts/create_test_users.py
"""

import asyncio
import httpx
from datetime import datetime

# FastAPI 서버 URL
API_BASE_URL = "http://localhost:8001"

# 테스트 사용자 3명
TEST_USERS = [
    {
        "user_id": "test_user_001",
        "name": "김영희",
        "age": 75,
        "schedule_times": ["10:00", "15:00", "20:00"]
    },
    {
        "user_id": "test_user_002",
        "name": "이철수",
        "age": 72,
        "schedule_times": ["09:00", "14:00", "19:00"]
    },
    {
        "user_id": "test_user_003",
        "name": "박민수",
        "age": 78,
        "schedule_times": ["11:00", "16:00", "21:00"]
    }
]


async def create_user_and_schedule(user_data: dict):
    """
    사용자 생성 및 스케줄 설정

    Args:
        user_data: 사용자 정보
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        user_id = user_data["user_id"]
        name = user_data["name"]
        schedule_times = user_data["schedule_times"]

        print(f"\n{'='*60}")
        print(f"📝 Creating user: {name} ({user_id})")
        print(f"{'='*60}")

        # 1. 사용자 등록 (향후 구현 예정)
        # TODO: POST /api/v1/users
        print(f"✅ User would be created: {user_id}")

        # 2. 스케줄 생성
        try:
            schedule_url = f"{API_BASE_URL}/api/v1/sessions/users/{user_id}/schedule"

            # 커스텀 시간대 사용
            payload = {"schedule_times": schedule_times}

            response = await client.post(schedule_url, json=payload)
            response.raise_for_status()

            result = response.json()

            print(f"✅ Schedule created:")
            print(f"   - Times: {', '.join(result['schedule_times'])}")
            print(f"   - Job IDs: {len(result['job_ids'])} jobs")
            print(f"   - Created at: {result['created_at']}")

            return result

        except httpx.HTTPError as e:
            print(f"❌ Failed to create schedule: {e}")
            return None


async def verify_schedules():
    """
    생성된 스케줄 확인
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n{'='*60}")
        print(f"🔍 Verifying all schedules")
        print(f"{'='*60}")

        try:
            url = f"{API_BASE_URL}/api/v1/sessions/schedules"
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            total = data["total"]
            schedules = data["schedules"]

            print(f"✅ Total schedules: {total}")
            print()

            for schedule in schedules:
                print(f"📅 User: {schedule['user_id']}")
                print(f"   Times: {', '.join(schedule['schedule_times'])}")
                print(f"   Jobs: {len(schedule['job_ids'])}")
                print()

            return schedules

        except httpx.HTTPError as e:
            print(f"❌ Failed to verify schedules: {e}")
            return []


async def get_next_dialogue_times():
    """
    각 사용자의 다음 대화 시간 확인
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n{'='*60}")
        print(f"⏰ Next dialogue times")
        print(f"{'='*60}")

        for user in TEST_USERS:
            user_id = user["user_id"]
            name = user["name"]

            try:
                url = f"{API_BASE_URL}/api/v1/sessions/users/{user_id}/schedule"
                response = await client.get(url)
                response.raise_for_status()

                schedule = response.json()
                next_time = schedule.get("next_run_time", "N/A")

                if next_time != "N/A":
                    # ISO format to readable
                    dt = datetime.fromisoformat(next_time.replace('Z', '+00:00'))
                    next_time = dt.strftime("%Y-%m-%d %H:%M:%S")

                print(f"👤 {name} ({user_id})")
                print(f"   Next dialogue: {next_time}")
                print()

            except httpx.HTTPError as e:
                print(f"❌ {name}: Failed to get schedule - {e}")
                print()


async def main():
    """
    메인 실행 함수
    """
    print("\n" + "="*60)
    print("🌸 Memory Garden - Test User Setup")
    print("="*60)
    print(f"Server: {API_BASE_URL}")
    print(f"Users to create: {len(TEST_USERS)}")
    print()

    # 서버 헬스 체크
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{API_BASE_URL}/health")
            response.raise_for_status()
            print("✅ Server is healthy")
        except httpx.HTTPError as e:
            print(f"❌ Server is not available: {e}")
            print("Please start the server first:")
            print("  uvicorn api.main:app --reload")
            return

    # 사용자 생성 및 스케줄 설정
    for user_data in TEST_USERS:
        await create_user_and_schedule(user_data)
        await asyncio.sleep(1)  # 서버 부하 방지

    # 스케줄 확인
    await verify_schedules()

    # 다음 대화 시간 확인
    await get_next_dialogue_times()

    print("\n" + "="*60)
    print("✅ Test user setup completed!")
    print("="*60)
    print()
    print("📋 Next steps:")
    print("1. Wait for scheduled dialogue times")
    print("2. Check logs: tail -f logs/app.log")
    print("3. Monitor MCDI scores via API")
    print("4. Review risk levels after 7 days")
    print()


if __name__ == "__main__":
    asyncio.run(main())
