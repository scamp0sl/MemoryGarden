#!/usr/bin/env python3
"""LLM 모델 비교 테스트

GPT-4o-mini vs Claude Sonnet 대화 및 분석 품질 비교
"""

import asyncio
import sys
sys.path.append('/home/admin/docker/MemoryGardenAI')

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from config.settings import settings

# 테스트 프롬프트
TEST_CONVERSATION = [
    "봄이 되니까 엄마가 산에서 쑥을 뜯으러 가셨던 기억이 나",
    "오늘 아침에 약 먹는 걸 깜빡했어",
    "옛날에는 이 집 마당에 감나무가 있었는데, 벌써 20년이 지났네",
]

TEST_MCDI_PROMPT = """
다음 사용자의 발언을 분석하여 인지 기능 지표를 평가하세요.

발언: "봄이 되니까 엄마가 산에서 쑥을 뜯으러 가셨던 기억이 나. 그때가 벌써 10년 전인가?"

다음 항목을 0-100점으로 평가하고 JSON으로 반환하세요:
{
    "lexical_richness": "어휘 다양성",
    "episodic_recall": "일화 기억 상세度",
    "temporal_orientation": "시간적 지남력",
    "narrative_coherence": "서사 일관성"
}
"""

async def test_gpt():
    """GPT-4o-mini 테스트"""
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    print("=" * 60)
    print("🤖 GPT-4o-mini")
    print("=" * 60)

    # 대화 테스트
    print("\n【대화 테스트】")
    for msg in TEST_CONVERSATION:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 '기억의 정원'이라는 치매 조기 감지 서비스의 상담원입니다. 60-70대 노인에게 따뜻하고 공감적으로 대화하세요."},
                {"role": "user", "content": msg}
            ],
            max_tokens=200
        )
        print(f"\n사용자: {msg}")
        print(f"GPT: {response.choices[0].message.content}")

    # MCDI 분석 테스트
    print("\n" + "=" * 60)
    print("【MCDI 분석 테스트】")
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": TEST_MCDI_PROMPT}
        ],
        response_format={"type": "json_object"},
        max_tokens=500
    )
    print(response.choices[0].message.content)

async def test_claude():
    """Claude Sonnet 테스트"""
    client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)

    print("\n\n" + "=" * 60)
    print("🧠 Claude Sonnet 4.6")
    print("=" * 60)

    # 대화 테스트
    print("\n【대화 테스트】")
    for msg in TEST_CONVERSATION:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            system="당신은 '기억의 정원'이라는 치매 조기 감지 서비스의 상담원입니다. 60-70대 노인에게 따뜻하고 공감적으로 대화하세요.",
            messages=[
                {"role": "user", "content": msg}
            ]
        )
        print(f"\n사용자: {msg}")
        print(f"Claude: {response.content[0].text}")

    # MCDI 분석 테스트
    print("\n" + "=" * 60)
    print("【MCDI 분석 테스트】")
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[
            {"role": "user", "content": TEST_MCDI_PROMPT}
        ]
    )
    print(response.content[0].text)

async def main():
    """메인 실행"""
    print("🌱 기억의 정원 - LLM 모델 비교 테스트\n")

    try:
        await test_gpt()
    except Exception as e:
        print(f"\n❌ GPT 테스트 실패: {e}")

    try:
        await test_claude()
    except Exception as e:
        print(f"\n❌ Claude 테스트 실패: {e}")

    print("\n\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
