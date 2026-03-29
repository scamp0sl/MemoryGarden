#!/usr/bin/env python3
"""나에게 보내기 API 테스트"""

import asyncio
import httpx
import json


async def test():
    access_token = "gE2H9fsupT7g17OEP62Ue4wt0r-Vy6HvAAAAAQoNDSEAAAGciFCcyv8D-j8FVvr5"

    # 나에게 보내기
    template_object = {
        "object_type": "text",
        "text": "Memory Garden 테스트 메시지입니다!",
        "link": {
            "web_url": "https://n8n.softline.co.kr"
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            data={
                "template_object": json.dumps(template_object, ensure_ascii=False)
            },
            timeout=30.0
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")


if __name__ == "__main__":
    asyncio.run(test())
