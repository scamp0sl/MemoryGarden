#!/usr/bin/env python3
"""카카오 API 직접 호출 테스트"""

import asyncio
import httpx
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.routes.kakao_oauth import get_access_token


async def test():
    # API를 통해 액세스 토큰 가져오기
    async with httpx.AsyncClient() as client:
        token_response = await client.get(
            "http://localhost:8000/kakao/oauth/token/test_user"
        )

        if token_response.status_code != 200:
            print("❌ 액세스 토큰 없음!")
            print(f"Response: {token_response.text}")
            return

        # 전체 토큰을 직접 가져오기 위해 내부 API 사용
        import sys
        sys.path.insert(0, "/home/admin/docker/MemoryGardenAI")

        # FastAPI 앱 import하여 직접 토큰 스토리지 접근
        from api.routes import kakao_oauth
        access_token = kakao_oauth._token_storage.get("test_user", {}).get("access_token")

        if not access_token:
            print("❌ 토큰 스토리지에 토큰 없음!")
            return

    print(f"✅ 액세스 토큰: {access_token[:30]}...")

    # 카카오 API 직접 호출
    payload = {
        "receiver_uuids": ["AkBzAKRCUoEn"],
        "template_object": {
            "object_type": "text",
            "text": "안녕하세요! Memory Garden 테스트 메시지입니다.",
            "link": {
                "web_url": "https://n8n.softline.co.kr",
                "mobile_web_url": "https://n8n.softline.co.kr"
            }
        }
    }

    print(f"\n📤 요청 데이터:")
    print(f"{payload}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://kapi.kakao.com/v1/api/talk/friends/message/default/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30.0
        )

        print(f"\n📥 응답:")
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Body: {response.text}")


if __name__ == "__main__":
    asyncio.run(test())
