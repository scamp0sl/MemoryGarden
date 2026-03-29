import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import patch

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.dialogue.category_selector import CategorySelector
from core.dialogue.dialogue_manager import DialogueManager
from database.redis_client import redis_client

async def run_tests():
    user_id = 'aa96e75d-70e2-4546-9001-043cc5db047d'  # "주인님" user
    
    print("\n=== TEST 2: Evening Reflection Prompt Injection ===")
    dialogue_manager = DialogueManager()
    
    # 1. Clear existing key
    mock_now = datetime(2026, 3, 13, 20, 0, 0)
    date_str = mock_now.strftime("%Y-%m-%d")
    r_key = f"evening_reflection_done:{user_id}:{date_str}"
    
    try:
        conn = await redis_client.get_client()
        await conn.delete(r_key)
        print(f"Cleared Redis Key: {r_key}")
    except Exception as e:
        print("Failed to clear redis:", e)
        
    
    with patch('core.dialogue.dialogue_manager.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now
        
        # We will mock the generator responses by patching the instance methods directly
        async def mock_generate(*args, **kwargs):
            return "Mock Response"
            
        dialogue_manager.response_generator.generate = mock_generate
        dialogue_manager.response_generator.generate_empathetic_response = mock_generate
        
        # Overwrite update_context to prevent redis errors
        async def mock_update_context(*args, **kwargs):
            pass
        dialogue_manager.update_context = mock_update_context
        
        # Need to capture kwargs
        captured_kwargs = []
        async def mock_generate_capture(*args, **kwargs):
            captured_kwargs.append(kwargs)
            return "Mock Response 1"
            
        dialogue_manager.response_generator.generate = mock_generate_capture
        
        await dialogue_manager.generate_response(
            user_id=user_id,
            user_message="안녕하세요",
            emotion=None,
            emotion_intensity=None
        )
        
        print("Call 1 user_context:", captured_kwargs[0].get('user_context', {}).get('evening_reflection_needed'))
        
        # Second call
        async def mock_generate_capture2(*args, **kwargs):
            captured_kwargs.append(kwargs)
            return "Mock Response 2"
            
        dialogue_manager.response_generator.generate = mock_generate_capture2
        
        await dialogue_manager.generate_response(
            user_id=user_id,
            user_message="두번째 대화",
            emotion=None,
            emotion_intensity=None
        )
        
        print("Call 2 user_context:", captured_kwargs[1].get('user_context', {}).get('evening_reflection_needed'))

if __name__ == "__main__":
    asyncio.run(run_tests())
