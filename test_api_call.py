#!/usr/bin/env python3
"""API 직접 호출 테스트"""

import asyncio
import httpx


async def test():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/kakao/oauth/send-friend-talk/test_user",
            json={
                "user_key": "AkBzAKRCUoEn",
                "message": "안녕하세요! Memory Garden 테스트 메시지입니다."
            },
            timeout=30.0
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

        return response.json()


if __name__ == "__main__":
    result = asyncio.run(test())
    print(f"\nResult: {result}")
