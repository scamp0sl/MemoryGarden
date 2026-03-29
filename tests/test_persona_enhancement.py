import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from core.dialogue.prompt_builder import PromptBuilder
from core.dialogue.response_generator import ResponseGenerator

@pytest.fixture
def prompt_builder():
    return PromptBuilder()

@pytest.fixture
def response_generator():
    rg = ResponseGenerator()
    rg._client = AsyncMock() # Mock the OpenAI Client
    return rg

@pytest.mark.asyncio
async def test_memory_utilization_prompt_generation(prompt_builder):
    """
    Test TC 1-1 & 1-2 (Prompt Check):
    Verify that biographical_facts triggers the special memory injection instruction.
    """
    facts = {"favorite_food": "김치찌개", "hobby": "수채화 그리기"}
    prompt = await prompt_builder.build_system_prompt(
        user_name="테스터",
        biographical_facts=facts
    )
    
    assert "[특명] 메모리 활용 규칙" in prompt
    assert "자연스럽게 아는 척하며 대화에 녹여내세요" in prompt
    assert "김치찌개" in prompt
    assert "수채화 그리기" in prompt

@pytest.mark.asyncio
async def test_deep_comforting_mode_prompt_generation(prompt_builder):
    """
    Test TC 2-1 & 2-2 (Prompt Check):
    Verify that negative emotions trigger the Deep Comforting Mode.
    """
    negative_emotion = "우울"
    prompt = await prompt_builder.build_system_prompt(
        user_name="테스터",
        recent_emotion=negative_emotion
    )
    
    # Check if Deep Comforting Mode block is inserted
    assert "[깊은 위로 모드 (Deep Comforting Mode) 발동]" in prompt
    assert "우울'입니다" in prompt
    assert "발랄함'과 '높은 텐션'을 즉각 끄세요." in prompt
    assert "도입부의 감탄사('헐!', '우와!')를 모두 제거하고" in prompt
    assert "해결책 금지" in prompt
    assert "질문형 어미" in prompt
    
    # Check regular emotion behavior
    normal_prompt = await prompt_builder.build_system_prompt(
        user_name="테스터",
        recent_emotion="기쁨"
    )
    assert "[깊은 위로 모드 (Deep Comforting Mode) 발동]" not in normal_prompt
    assert "기쁨' 감정을 보이고 있습니다." in normal_prompt

@pytest.mark.asyncio
async def test_deep_comforting_mode_end_to_end_mock(response_generator):
    """
    Test TC 2-1: Ensure the empathetic response logic correctly builds the context
    and handles the generation step without raising errors, assuming OpenAI returns a calm response.
    """
    # Mocking the OpenAI response
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "많이 속상하시겠어요... 오늘 혼자서 얼마나 힘드셨을까요."
    
    # Proper mocking pattern for recent OpenAI client
    response_generator._client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    user_context = {"user_name": "테스터"}
    response = await response_generator.generate_empathetic_response(
        user_message="오늘 진짜 너무 힘들고 우울해...",
        detected_emotion="sadness", # translates to '슬픔'
        emotion_intensity=0.9,
        conversation_history=[],
        user_context=user_context
    )
    
    # Asserting basic properties (the prompt is tested above, this ensures the chain works)
    assert response == "많이 속상하시겠어요... 오늘 혼자서 얼마나 힘드셨을까요."
    
    # Ensure client was called
    response_generator._client.chat.completions.create.assert_called_once()
    
    # Extract args to verify the prompt indeed had the comforting mode
    call_kwargs = response_generator._client.chat.completions.create.call_args.kwargs
    system_message = None
    for msg in call_kwargs['messages']:
        if msg['role'] == 'system':
            system_message = msg['content']
            
    assert "[깊은 위로 모드" in system_message
