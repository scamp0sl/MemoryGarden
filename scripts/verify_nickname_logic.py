import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.dialogue.dialogue_manager import DialogueManager
from core.dialogue.response_generator import ResponseGenerator
from database.redis_client import redis_client

TARGET_USER_ID = "1f729443-7b80-4d82-a227-c4751b3bf35f"

async def verify_logic():
    print(f"--- Verifying Nickname Logic for User: {TARGET_USER_ID} ---")
    
    # Mock ResponseGenerator to capture prompt
    mock_resp_gen = MagicMock(spec=ResponseGenerator)
    mock_resp_gen.generate = AsyncMock(return_value="Mocked response")
    
    # Initialize DialogueManager with mock
    manager = DialogueManager(response_generator=mock_resp_gen)
    
    # 1. First interaction: Should have apology AND nickname prompt
    print("\n[Test 1] First interaction (Expected: Apology + Nickname Prompt)")
    # Ensure flag is set in Redis (it was set by cleanup script)
    await redis_client.set(f"nickname_cleaned:{TARGET_USER_ID}", "1")
    
    await manager.generate_response(
        user_id=TARGET_USER_ID,
        user_message="안녕하세요"
    )
    
    # Inspect calls to mock_resp_gen.generate
    # args: user_message, conversation_history, user_context, next_question
    args, kwargs = mock_resp_gen.generate.call_args
    user_context = kwargs.get('user_context')
    
    print(f"  Flag apologize_for_nickname: {user_context.get('apologize_for_nickname')}")
    print(f"  Flag prompt_for_nickname: {user_context.get('prompt_for_nickname')}")
    
    # Now check the ACTUAL prompt built by PromptBuilder
    from core.dialogue.prompt_builder import PromptBuilder
    builder = PromptBuilder()
    
    def call_build_system_prompt(builder, context):
        return builder.build_system_prompt(
            user_name=context.get("user_name"),
            recent_emotion=context.get("recent_emotion"),
            biographical_facts=context.get("biographical_facts"),
            garden_name=context.get("garden_name"),
            recent_mentions=context.get("recent_mentions"),
            story_topic=context.get("story_topic"),
            role_reversal_mode=context.get("role_reversal_mode", False),
            to_assessment_needed=context.get("to_assessment_needed", False),
            evening_reflection_needed=context.get("evening_reflection_needed", False),
            suppress_questions=context.get("suppress_questions", False),
            apologize_for_nickname=context.get("apologize_for_nickname", False),
            prompt_for_nickname=context.get("prompt_for_nickname", False)
        )

    prompt = call_build_system_prompt(builder, user_context)
    
    print("\n--- Generated System Prompt Snippet ---")
    if "## 호칭 사과 지침" in prompt:
        print("[MATCH] Found '## 호칭 사과 지침' in prompt")
    else:
        print("[FAIL] '## 호칭 사과 지침' NOT found in prompt")
        
    if "## 새 호칭 설정 지침" in prompt:
        print("[MATCH] Found '## 새 호칭 설정 지침' in prompt")
    else:
        print("[FAIL] '## 새 호칭 설정 지침' NOT found in prompt")

    # 2. Second interaction: Should have ONLY nickname prompt (apology is consumed)
    print("\n[Test 2] Second interaction (Expected: Nickname Prompt ONLY)")
    mock_resp_gen.generate.reset_mock()
    
    await manager.generate_response(
        user_id=TARGET_USER_ID,
        user_message="그냥 궁금해서요"
    )
    
    args, kwargs = mock_resp_gen.generate.call_args
    user_context = kwargs.get('user_context')
    
    print(f"  Flag apologize_for_nickname: {user_context.get('apologize_for_nickname')}")
    print(f"  Flag prompt_for_nickname: {user_context.get('prompt_for_nickname')}")
    
    prompt = call_build_system_prompt(builder, user_context)
    
    if "## 호칭 사과 지침" not in prompt:
        print("[MATCH] '## 호칭 사과 지침' correctly removed")
    if "## 새 호칭 설정 지침" in prompt:
        print("[MATCH] '## 새 호칭 설정 지침' still present")

    print("\nVerification complete.")

if __name__ == "__main__":
    asyncio.run(verify_logic())
