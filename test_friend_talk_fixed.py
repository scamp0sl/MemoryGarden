#!/usr/bin/env python3
"""
친구톡 API 테스트 (수정된 버전)

카카오 공식 문서 기준:
- Content-Type: application/x-www-form-urlencoded
- receiver_uuids: JSON 문자열
- template_object: JSON 문자열
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def test_friend_talk_official():
    """카카오 공식 문서 예제대로 테스트"""

    # 1. 액세스 토큰 가져오기
    print("1️⃣ 액세스 토큰 가져오는 중...")
    async with httpx.AsyncClient() as client:
        token_response = await client.get(
            "http://localhost:8000/kakao/oauth/token/test_user?full=true"
        )

        if token_response.status_code != 200:
            print("❌ 액세스 토큰 없음!")
            print(f"Response: {token_response.text}")
            print("\n먼저 로그인하세요:")
            print("https://n8n.softline.co.kr/kakao/oauth/login?user_id=test_user")
            return

        token_data = token_response.json()
        access_token = token_data["access_token"]

    print(f"✅ 액세스 토큰: {access_token[:30]}...")

    # 2. 친구톡 전송 (카카오 공식 문서 방식)
    print("\n2️⃣ 친구톡 전송 중...")

    user_key = "AkBzAKRCUoEn"

    # 템플릿 객체 (딕셔너리)
    template_object = {
        "object_type": "text",
        "text": "안녕하세요! Memory Garden 테스트 메시지입니다.\n\n카카오 공식 문서 기준으로 수정했습니다.",
        "link": {
            "web_url": "https://n8n.softline.co.kr",
            "mobile_web_url": "https://n8n.softline.co.kr"
        }
    }

    print(f"\n📤 요청 정보:")
    print(f"  - 엔드포인트: /v1/api/talk/friends/message/default/send")
    print(f"  - Content-Type: application/x-www-form-urlencoded;charset=utf-8")
    print(f"  - User Key: {user_key}")
    print(f"  - Message: {template_object['text'][:50]}...")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://kapi.kakao.com/v1/api/talk/friends/message/default/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
            },
            data={
                # JSON 문자열로 변환 (카카오 공식 문서 요구사항)
                "receiver_uuids": json.dumps([user_key], ensure_ascii=False),
                "template_object": json.dumps(template_object, ensure_ascii=False)
            },
            timeout=30.0
        )

        print(f"\n📥 응답:")
        print(f"  - Status: {response.status_code}")
        print(f"  - Headers: {dict(response.headers)}")
        print(f"  - Body: {response.text}")

        if response.status_code == 200:
            result = response.json()
            if "successful_receiver_uuids" in result:
                print(f"\n✅ 성공! 전송된 사용자: {result['successful_receiver_uuids']}")
            else:
                print(f"\n⚠️  응답 확인 필요: {result}")
        else:
            print(f"\n❌ 실패!")


async def test_via_our_api():
    """우리 API 엔드포인트로 테스트"""
    print("\n" + "="*60)
    print("3️⃣ 우리 API로 테스트")
    print("="*60)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/kakao/oauth/send-friend-talk/test_user",
            json={
                "user_key": "AkBzAKRCUoEn",
                "message": "안녕하세요! Memory Garden 테스트 메시지입니다.\n\nAPI를 통한 전송 테스트."
            },
            timeout=30.0
        )

        print(f"\n📥 응답:")
        print(f"  - Status: {response.status_code}")
        print(f"  - Body: {response.text}")

        if response.status_code == 200:
            print("\n✅ 성공!")
        else:
            print("\n❌ 실패!")


if __name__ == "__main__":
    print("="*60)
    print("친구톡 API 테스트 (카카오 공식 문서 기준)")
    print("="*60)

    asyncio.run(test_friend_talk_official())

    # 우리 API도 테스트
    print("\n")
    asyncio.run(test_via_our_api())
