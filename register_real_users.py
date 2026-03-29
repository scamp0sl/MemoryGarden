#!/usr/bin/env python3
"""
실제 사용자 등록 및 스케줄 설정

사용법:
    python register_real_users.py
"""

import asyncio
import httpx
from datetime import datetime

API_BASE_URL = "http://localhost:8001"

# ========================================
# 👥 실제 참여자 정보 입력
# ========================================
REAL_USERS = [
    {
        "user_id": "user_001",  # 고유 ID (예: kakao_12345678)
        "name": "이정훈",  # 실제 이름 입력
        "age": 65,  # 실제 나이 입력
        "phone": "010-6557-5795",  # 카카오톡 가입 번호
        "schedule_times": ["10:00", "15:00", "18:00"]  # 원하는 시간대
    },
    {
        "user_id": "user_002",
        "name": "홍석일",
        "age": 62,
        "phone": "010-7762-5837",
        "schedule_times": ["09:00", "14:00", "18:00"]
    }
]


async def register_user(user_data: dict):
    """사용자 스케줄 등록"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        user_id = user_data["user_id"]
        name = user_data["name"]
        
        print(f"\n{'='*60}")
        print(f"📝 등록: {name} ({user_id})")
        print(f"{'='*60}")
        
        try:
            # 스케줄 생성
            schedule_url = f"{API_BASE_URL}/api/v1/sessions/users/{user_id}/schedule"
            payload = {"schedule_times": user_data["schedule_times"]}
            
            response = await client.post(schedule_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            print(f"✅ 스케줄 생성 완료:")
            print(f"   - 시간: {', '.join(result['schedule_times'])}")
            print(f"   - 작업 수: {len(result['job_ids'])}개")
            print(f"   - 생성 시각: {result['created_at']}")
            
            # 다음 실행 시간 확인
            schedule_info_url = f"{API_BASE_URL}/api/v1/sessions/users/{user_id}/schedule"
            info_response = await client.get(schedule_info_url)
            info_response.raise_for_status()
            
            schedule_info = info_response.json()
            next_time = schedule_info.get("next_run_time", "N/A")
            
            print(f"   - 다음 실행: {next_time}")
            
            return result
            
        except httpx.HTTPError as e:
            print(f"❌ 등록 실패: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   상세: {e.response.text}")
            return None


async def test_message(user_id: str, name: str):
    """테스트 메시지 전송"""
    print(f"\n📨 {name}에게 테스트 메시지 전송 중...")
    
    try:
        from tasks.dialogue import send_scheduled_dialogue
        result = await send_scheduled_dialogue(user_id)
        
        if result.get("success"):
            print(f"✅ 전송 성공!")
            print(f"   메시지: {result.get('message_sent', 'N/A')[:50]}...")
            print(f"   카카오 Message ID: {result.get('kakao_message_id')}")
        else:
            print(f"❌ 전송 실패: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ 전송 중 오류: {e}")


async def main():
    print("\n" + "="*60)
    print("🌸 Memory Garden - 실제 사용자 등록")
    print("="*60)
    print()
    
    # 서버 헬스 체크
    print("🔍 서버 상태 확인 중...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{API_BASE_URL}/health")
            response.raise_for_status()
            print("✅ 서버 정상 작동")
        except httpx.HTTPError as e:
            print(f"❌ 서버 접속 실패: {e}")
            print("서버를 먼저 시작하세요:")
            print("  .venv/bin/uvicorn api.main:app --reload --host 127.0.0.1 --port 8001")
            return
    
    print()
    print("📋 등록할 사용자:")
    for i, user in enumerate(REAL_USERS, 1):
        print(f"{i}. {user['name']} ({user['age']}세)")
        print(f"   - 전화: {user['phone']}")
        print(f"   - 시간: {', '.join(user['schedule_times'])}")
    print()
    
    answer = input("계속하시겠습니까? (y/n): ")
    if answer.lower() != 'y':
        print("취소되었습니다.")
        return
    
    # 사용자 등록
    for user_data in REAL_USERS:
        await register_user(user_data)
        await asyncio.sleep(1)
    
    print()
    print("="*60)
    print("✅ 등록 완료!")
    print("="*60)
    print()
    
    # 테스트 메시지 전송 여부
    answer = input("테스트 메시지를 전송하시겠습니까? (y/n): ")
    if answer.lower() == 'y':
        for user in REAL_USERS:
            await test_message(user['user_id'], user['name'])
            await asyncio.sleep(2)
    
    print()
    print("="*60)
    print("🎉 완료!")
    print("="*60)
    print()
    print("📋 다음 단계:")
    print("1. 카카오톡 앱에서 메시지 확인")
    print("2. 스케줄 확인:")
    print(f"   curl {API_BASE_URL}/api/v1/sessions/schedules | jq .")
    print("3. 모니터링:")
    print("   /tmp/monitor_schedule.sh")
    print()


if __name__ == "__main__":
    asyncio.run(main())
