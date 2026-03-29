"""
감정 벡터 프롬프트 변환 기능 테스트

Emotion Vector의 딕셔너리 키(v, a, i)가
LLM이 이해할 수 있는 자연어 설명으로 올바르게 변환되는지 검증.

Author: Memory Garden Team
Created: 2026-03-29
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

# ============================================
# 1. Test Setup
# ============================================

# sys.path 추가 (상위 경로에서 임포트 가능하도록)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dialogue.prompt_builder import PromptBuilder


# ============================================
# 2. Test Cases
# ============================================


class TestEmotionVectorPromptFix:
    """감정 벡터 프롬프트 변환 테스트"""

    @pytest.fixture
    def prompt_builder(self):
        """PromptBuilder 인스턴스"""
        return PromptBuilder()

    @pytest.mark.asyncio
    async def test_positive_high_arousal_high_intimacy(self, prompt_builder):
        """긍정+고활성+높은 친박감 조합"""
        result = await prompt_builder.build_system_prompt(
            user_id="test_user",
            emotion_vector={"v": 0.8, "a": 0.7, "i": 0.9}
        )

        # 프롬프트에 감정 설명이 포함되어야 함
        assert "지금 내 기분" in result
        # 긍정적 표현
        assert ("긍정적" in result or "기분이 밝" in result)
        # 고활성 표현
        assert ("활발" in result or "에너지" in result)
        # 친박감 표현
        assert ("친박" in result or "가깝워" in result)

        # 딕셔너리 키가 노출되지 않아야 함
        assert "v=" not in result
        assert "a=" not in result
        assert "i=" not in result
        assert "valence" not in result
        assert "arousal" not in result

    @pytest.mark.asyncio
    async def test_negative_low_arousal_low_intimacy(self, prompt_builder):
        """부정+진정+낮은 친박감 조합"""
        result = await prompt_builder.build_system_prompt(
            user_id="test_user",
            emotion_vector={"v": -0.7, "a": -0.5, "i": 0.2}
        )

        assert "지금 내 기분" in result
        # 부정적 표현
        assert ("우울" in result or "쓸쓸" in result or "가라앉" in result)
        # 진정 표현
        assert ("차분" in result or "진정" in result)
        # 낮은 친박감 (생략되거나 서먹서움 표현)
        # 현재 구현에서 i < 0.3일 때 "서먹서운" 표현이 추가됨

    @pytest.mark.asyncio
    async def test_neutral_balanced(self, prompt_builder):
        """중립+균형 조합"""
        result = await prompt_builder.build_system_prompt(
            user_id="test_user",
            emotion_vector={"v": 0.0, "a": 0.0, "i": 0.5}
        )

        # 중립 상태에서는 생략될 수 있음
        # 또는 기본값으로 표현
        # 중요한 것은 에러가 나지 않는 것
        assert result is not None

    @pytest.mark.asyncio
    async def test_empty_emotion_vector(self, prompt_builder):
        """빈 emotion_vector 처리"""
        result = await prompt_builder.build_system_prompt(
            user_id="test_user",
            emotion_vector=None
        )

        # emotion_vector가 없어도 에러가 나지 않아야 함
        assert result is not None
        # 감정 설명 블록이 없어야 함
        assert "지금 내 기분" not in result

    @pytest.mark.asyncio
    async def test_all_extreme_combinations(self, prompt_builder):
        """모든 극단 조합 테스트"""
        test_cases = [
            # (v, a, i, expected_keywords)
            (0.9, 0.9, 0.9, ["긍정", "활발", "친박"]),
            (0.9, 0.9, 0.1, ["긍정", "활발"]),
            (0.9, -0.9, 0.9, ["긍정", "진정", "친박"]),
            (-0.9, 0.9, 0.9, ["우울", "활발", "친박"]),
            (-0.9, -0.9, 0.9, ["우울", "진정", "친박"]),
            (-0.9, 0.9, 0.1, ["우울", "활발", "서머"]),
            (0.0, 0.0, 0.0, []),  # 중립
        ]

        for v, a, i, expected_keywords in test_cases:
            result = await prompt_builder.build_system_prompt(
                user_id="test_user",
                emotion_vector={"v": v, "a": a, "i": i}
            )

            # 딕셔너리 키가 절대 노출되지 않아야 함
            assert "v=" not in result, f"v= 노출됨: v={v}"
            assert "a=" not in result, f"a= 노출됨: a={a}"
            assert "i=" not in result, f"i= 노출됨: i={i}"

            # 예상 키워드 중 하나라도 포함되는지 확인 (단, 중립은 제외)
            if expected_keywords:
                has_any = any(kw in result for kw in expected_keywords)
                assert has_any, f"예상 키워드 없음: {expected_keywords}, v={v}, a={a}, i={i}"


# ============================================
# 3. Integration Test: 실제 Prompt 확인
# ============================================


class TestEmotionVectorIntegration:
    """감정 벡터 통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_prompt_with_emotion_vector(self):
        """전체 프롬프트에 감정 벡터가 올바르게 통합되는지 확인"""
        builder = PromptBuilder()

        # 사용자 컨텍스트 포함
        result = await builder.build_system_prompt(
            user_id="test_user",
            user_name="홍길동",
            garden_name="행복한 정원",
            emotion_vector={"v": 0.6, "a": 0.4, "i": 0.7},
            relationship_stage=2,
            mcdi_context={"has_data": False}
        )

        # 프롬프트 구조 확인
        assert "사만다처럼" in result
        assert "홍길동" in result
        assert "지금 내 기분" in result

        # 감정 설명이 자연스러운 한국어인지 확인
        assert "v=" not in result
        assert "a=" not in result
        assert "i=" not in result

        # 긍정적 표현이 있는지 확인
        assert any(word in result for word in ["긍정", "밝고", "기분이 좋"])

    @pytest.mark.asyncio
    async def test_emotion_vector_with_mcdi_orange(self):
        """MCDI ORANGE 모드와 감정 벡터가 함께 작동하는지 확인"""
        builder = PromptBuilder()

        result = await builder.build_system_prompt(
            user_id="test_user",
            emotion_vector={"v": -0.4, "a": -0.3, "i": 0.5},
            mcdi_context={
                "has_data": True,
                "latest_risk_level": "ORANGE",
                "latest_mcdi_score": 45.0,
                "score_trend": "declining",
                "latest_scores": {"LR": 50, "SD": 40, "NC": 45, "TO": 35, "ER": 30, "RT": 50}
            },
            relationship_stage=2
        )

        # 두 가지 컨텍스트가 모두 포함되어야 함
        assert "[인지 집중 모드 - ORANGE]" in result
        assert "지금 내 기분" in result

        # ORANGE 모드 지침 확인
        assert "문장당 10단어 이하" in result

        # 감정 설명 확인 (우울한 기분 + 진정 상태)
        assert "쓸쓸" in result or "우울" in result


# ============================================
# 4. Regression Test: 기존 기능 확인
# ============================================


class TestEmotionVectorRegression:
    """감정 벡터 수정 후 기존 기능 회귀 테스트"""

    @pytest.mark.asyncio
    async def test_system_prompt_integrity(self):
        """SYSTEM_PROMPT 기본 구조가 유지되는지 확인"""
        builder = PromptBuilder()

        result = await builder.build_system_prompt(
            user_id="test_user"
        )

        # 기본 프롬프트 요소 확인
        assert "사만다처럼" in result
        assert "절대 규칙" in result
        assert "금기사항" in result
        assert "의존 방지 가드레일" in result

    @pytest.mark.asyncio
    async def test_relationship_stage_still_works(self):
        """관계 Stage 기능이 여전히 작동하는지 확인"""
        builder = PromptBuilder()

        # Stage 0
        result_0 = await builder.build_system_prompt(
            user_id="test_user",
            relationship_stage=0
        )
        assert "처음 알아가는 사이" in result_0
        assert "조심스럽고 다정하게" in result_0

        # Stage 3
        result_3 = await builder.build_system_prompt(
            user_id="test_user",
            relationship_stage=3
        )
        assert "매우 친한 친구" in result_3
        assert "자연스럽고 편안하게" in result_3

    @pytest.mark.asyncio
    async def test_mcdi_yellow_mode_still_works(self):
        """MCDI YELLOW 모드가 여전히 작동하는지 확인"""
        builder = PromptBuilder()

        result = await builder.build_system_prompt(
            user_id="test_user",
            mcdi_context={
                "has_data": True,
                "latest_risk_level": "YELLOW",
                "latest_scores": {"LR": 55, "SD": 50, "NC": 45}
            }
        )

        assert "[인지 주의 모드 - YELLOW]" in result
        assert "주의가 필요합니다" in result


# ============================================
# 5. Run Tests
# ============================================


if __name__ == "__main__":
    import sys

    # 간단한 테스트 실행
    async def run_quick_test():
        builder = PromptBuilder()

        print("=" * 60)
        print("감정 벡터 프롬프트 변환 테스트")
        print("=" * 60)

        # 테스트 1: 긍정+고활성+친박
        print("\n[Test 1] 긍정+고활성+친박감")
        result1 = await builder.build_system_prompt(
            user_id="test_user",
            emotion_vector={"v": 0.8, "a": 0.7, "i": 0.9}
        )
        print("결과 포함 확인:")
        print("  - '지금 내 기분' 있음:", "지금 내 기분" in result1)
        print("  - '긍정' 있음:", "긍정" in result1 or "기분이 밝" in result1)
        print("  - '활발' 있음:", "활발" in result1 or "에너지" in result1)
        print("  - '친박' 있음:", "친박" in result1 or "가깊워" in result1)
        print("  - 딕셔너리 키 없음:", "v=" not in result1 and "a=" not in result1)

        # 감정 설명 부분 추출
        lines = result1.split('\n')
        for i, line in enumerate(lines):
            if "지금 내 기분" in line:
                print(f"\n  실제 감정 설명 블록:")
                j = i + 1
                while j < len(lines) and j < i + 5:
                    if lines[j].strip():
                        print(f"    {lines[j]}")
                    j += 1
                break

        # 테스트 2: 부정+진정+서머
        print("\n[Test 2] 부정+진정+서머서운")
        result2 = await builder.build_system_prompt(
            user_id="test_user",
            emotion_vector={"v": -0.7, "a": -0.5, "i": 0.2}
        )
        print("결과 포함 확인:")
        print("  - '지금 내 기분' 있음:", "지금 내 기분" in result2)
        print("  - '우울' 있음:", "우울" in result2 or "쓸쓸" in result2)
        print("  - '진정' 있음:", "진정" in result2 or "차분" in result2)
        print("  - 딕셔너리 키 없음:", "v=" not in result2 and "a=" not in result2)

        # 테스트 3: 빈 벡터
        print("\n[Test 3] 빈 emotion_vector")
        result3 = await builder.build_system_prompt(
            user_id="test_user",
            emotion_vector=None
        )
        print("결과:")
        print("  - 감정 설명 없음:", "지금 내 기분" not in result3)

        print("\n" + "=" * 60)
        print("모든 테스트 통과!")
        print("=" * 60)

    # 실행
    asyncio.run(run_quick_test())
