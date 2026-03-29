import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.dialogue.category_selector import CategorySelector
from core.dialogue.dialogue_manager import DialogueManager

async def run_tests():
    user_id = 'aa96e75d-70e2-4546-9001-043cc5db047d'  # "주인님" user
    
    print("=== TEST 1: Routing Distribution ===")
    selector = CategorySelector()
    
    # 1. Fetch current scores
    scores = await selector._fetch_indicator_averages(user_id)
    print("Scores:", scores)
    
    # 2. Fetch usage
    weekly_usage = await selector._fetch_weekly_usage(user_id)
    daily_usage = await selector._fetch_daily_usage(user_id)
    print("Weekly Usage before:", weekly_usage)
    print("Daily Usage before:", daily_usage)
    
    # 3. Simulate selection 10 times to check if it distributes evenly.
    for i in range(10):
        cat = await selector.select(user_id)
        print(f"Selection {i+1}: {cat}")
    
    weekly_usage_after = await selector._fetch_weekly_usage(user_id)
    daily_usage_after = await selector._fetch_daily_usage(user_id)
    print("Weekly Usage after:", weekly_usage_after)
    print("Daily Usage after:", daily_usage_after)

    print("\n=== TEST 2: Evening Reflection Prompt Injection ===")
    dialogue_manager = DialogueManager()
    
    # Mock datetime to simulate evening (20:00)
    mock_now = datetime(2026, 3, 13, 20, 0, 0)
    
    with patch('core.dialogue.dialogue_manager.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now
        
        # Call generate_response with a test message
        # We will mock response_generator.generate to see what user_context it receives
        dialogue_manager.response_generator.generate = AsyncMock()
        dialogue_manager.response_generator.generate_empathetic_response = AsyncMock()
        
        await dialogue_manager.generate_response(
            user_id=user_id,
            user_message="안녕하세요",
            emotion=None,
            emotion_intensity=None
        )
        
        # Check if the flag was passed to the response generator
        call_args = dialogue_manager.response_generator.generate.call_args
        if call_args:
            user_context = call_args.kwargs.get('user_context', {})
            print("Evening Reflection Needed Flag:", user_context.get('evening_reflection_needed'))
        else:
            print("Response generator not called.")
            
        # Call it again and the flag should be False because it's already done
        await dialogue_manager.generate_response(
            user_id=user_id,
            user_message="두번째 대화",
            emotion=None,
            emotion_intensity=None
        )
        
        call_args2 = dialogue_manager.response_generator.generate.call_args
        if call_args2:
            user_context2 = call_args2.kwargs.get('user_context', {})
            print("Evening Reflection Needed Flag (2nd turn):", user_context2.get('evening_reflection_needed', False))
        else:
            print("Response generator not called.")

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

if __name__ == "__main__":
    asyncio.run(run_tests())
