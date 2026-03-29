"""Samantha MCDI Context 연결 테스트"""
import asyncio
import httpx

async def test_mcdi_context_flow():
    """MCDI 컨텍스트가 정상적으로 연결되어 어댑티브 대화가 생성되는지 테스트"""
    test_user_key = "test_sam_mcdi_20260326"

    async with httpx.AsyncClient() as client:
        # 1. 시뮬레이션 엔드포인트로 테스트
        response = await client.post(
            "http://127.0.0.1:8002/kakao/webhook/simulate",
            params={
                "user_key": test_user_key,
                "message": "오늘 점심에 김치찌개 먹었어요"
            },
            timeout=30.0
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")

        # 2. 응답 파싱
        try:
            data = response.json()
            if "template" in data:
                outputs = data["template"]["outputs"]
                if outputs and "simpleText" in outputs[0]:
                    ai_message = outputs[0]["simpleText"]["text"]
                    print(f"\nAI 응답: {ai_message}\n")

                    # MCDI 관련 키워드 체크
                    mcdi_keywords = ["인지", "기억", "대화", "점수", "분석", "표현", "어휘"]
                    found_keywords = [kw for kw in mcdi_keywords if kw in ai_message]

                    if found_keywords:
                        print(f"✅ MCDI 관련 키워드 감지: {found_keywords}")
                        print("✅ 어댑티브 대화 블록이 생성된 것으로 확인됨")
                    else:
                        print("⚠️ 일반 대화 (MCDI 컨텍스트 미반영 가능)")
        except:
            print(f"Raw response: {response.text[:200]}")

if __name__ == "__main__":
    asyncio.run(test_mcdi_context_flow())
