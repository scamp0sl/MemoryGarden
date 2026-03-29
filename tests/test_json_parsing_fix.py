"""
JSON 파싱 에러 수정 테스트

call_json 메서드가 빈 JSON 응답과 malformed JSON을
제대로 처리하는지 검증.

Author: Memory Garden Team
Created: 2026-03-29
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# sys.path 추가 (상위 경로에서 임포트 가능하도록)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.llm_service import LLMService


# ============================================
# Test Cases
# ============================================


class TestJSONParsingFix:
    """JSON 파싱 에러 수정 테스트"""

    @pytest.fixture
    def llm_service(self):
        """LLMService 인스턴스"""
        return LLMService()

    @pytest.mark.asyncio
    async def test_empty_json_response_with_retry(self, llm_service):
        """빈 JSON 응답 후 재시도 성공"""
        # 첫 번째는 빈 응답, 두 번째는 정상 응답
        mock_responses = [
            "```json\n```",  # 빈 JSON
            '{"emotion": "joy", "intensity": 0.8}'  # 정상
        ]

        with patch.object(llm_service, 'call', new=AsyncMock(side_effect=mock_responses)):
            result = await llm_service.call_json(
                prompt="감정 분석",
                max_retries=2
            )

        assert result["emotion"] == "joy"
        assert result["intensity"] == 0.8

    @pytest.mark.asyncio
    async def test_empty_json_response_final_failure(self, llm_service):
        """빈 JSON 응답이 계속되면 에러 발생"""
        # 항상 빈 응답만 반환
        mock_response = "```json\n```"

        with patch.object(llm_service, 'call', new=AsyncMock(return_value=mock_response)):
            with pytest.raises(Exception) as exc_info:
                await llm_service.call_json(
                    prompt="감정 분석",
                    max_retries=1
                )

            # JSONDecodeError 또는 관련 에러여야 함
            assert "JSON" in str(exc_info.value) or "Empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_malformed_json_with_retry(self, llm_service):
        """잘못된 JSON 후 재시도 성공"""
        mock_responses = [
            '{"emotion": "joy", "intensity":',  # 불완전한 JSON
            '{"emotion": "joy", "intensity": 0.8}'  # 정상
        ]

        with patch.object(llm_service, 'call', new=AsyncMock(side_effect=mock_responses)):
            result = await llm_service.call_json(
                prompt="감정 분석",
                max_retries=2
            )

        assert result["emotion"] == "joy"

    @pytest.mark.asyncio
    async def test_json_with_markdown_blocks(self, llm_service):
        """```json``` 블록이 있는 응답 처리"""
        mock_response = '```json\n{"emotion": "joy", "intensity": 0.8}\n```'

        with patch.object(llm_service, 'call', new=AsyncMock(return_value=mock_response)):
            result = await llm_service.call_json(
                prompt="감정 분석"
            )

        assert result["emotion"] == "joy"

    @pytest.mark.asyncio
    async def test_json_with_extra_text_before_fails_gracefully(self, llm_service):
        """JSON 앞에 텍스트가 있는 경우 - json_mode=True면 발생하지 않아야 함"""
        # 이런 응답은 json_mode=True에서 나오면 안 되지만,
        # 나왔을 때를 대비해 적절히 실패하는지 확인
        mock_response = '분석 결과:\n```json\n{"emotion": "joy"}\n```'

        with patch.object(llm_service, 'call', new=AsyncMock(return_value=mock_response)):
            # 파싱 실패가 예상됨
            with pytest.raises(Exception):
                result = await llm_service.call_json(
                    prompt="감정 분석"
                )

    @pytest.mark.asyncio
    async def test_valid_json_no_markdown(self, llm_service):
        """마크다운 없는 순수 JSON 응답"""
        mock_response = '{"emotion": "sadness", "intensity": 0.3}'

        with patch.object(llm_service, 'call', new=AsyncMock(return_value=mock_response)):
            result = await llm_service.call_json(
                prompt="감정 분석"
            )

        assert result["emotion"] == "sadness"

    @pytest.mark.asyncio
    async def test_empty_object_json(self, llm_service):
        """빈 객체 JSON도 정상 파싱"""
        mock_response = '{}'

        with patch.object(llm_service, 'call', new=AsyncMock(return_value=mock_response)):
            result = await llm_service.call_json(
                prompt="감정 분석"
            )

        assert result == {}


# ============================================
# Run Tests
# ============================================

if __name__ == "__main__":
    import sys

    async def run_quick_test():
        service = LLMService()

        print("=" * 60)
        print("JSON 파싱 에러 수정 테스트")
        print("=" * 60)

        # 테스트 1: ```json``` 블록 처리
        print("\n[Test 1] 마크다운 JSON 블록 처리")
        with patch.object(service, 'call', new=AsyncMock(return_value='```json\n{"test": "value"}\n```')):
            try:
                result = await service.call_json(prompt="test")
                print(f"  결과: {result}")
                print("  성공!")
            except Exception as e:
                print(f"  실패: {e}")

        # 테스트 2: 빈 JSON 블록 (재시도)
        print("\n[Test 2] 빈 JSON 후 재시도")
        call_count = 0
        async def mock_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "```json\n```"
            return '{"retry": "success"}'

        with patch.object(service, 'call', new=AsyncMock(side_effect=mock_with_retry)):
            try:
                result = await service.call_json(prompt="test", max_retries=2)
                print(f"  결과: {result}")
                print(f"  호출 횟수: {call_count}")
                print("  성공!")
            except Exception as e:
                print(f"  실패: {e}")

        # 테스트 3: 잘못된 JSON 후 재시도
        print("\n[Test 3] 잘못된 JSON 후 재시도")
        call_count = 0
        async def mock_malformed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return '{"incomplete":'
            return '{"fixed": true}'

        with patch.object(service, 'call', new=AsyncMock(side_effect=mock_malformed)):
            try:
                result = await service.call_json(prompt="test", max_retries=2)
                print(f"  결과: {result}")
                print(f"  호출 횟수: {call_count}")
                print("  성공!")
            except Exception as e:
                print(f"  실패: {e}")

        print("\n" + "=" * 60)
        print("테스트 완료!")
        print("=" * 60)

    # 실행
    asyncio.run(run_quick_test())
