import asyncio
import os
import sys

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.dialogue.dialogue_manager import DialogueManager

async def test_turn_limit():
    user_id = 'test-turn-limit-user-123'
    dialogue_manager = DialogueManager()
    
    # 1. Start a fresh session
    await dialogue_manager.start_session(user_id)
    
    print("=== TEST 3: Conversation Turn Limiting ===")
    
    # 2. Simulate 6 turns of conversation
    for turn in range(1, 7):
        print(f"\n[Turn {turn}]")
        user_message = "네, 알겠습니다." if turn > 1 else "안녕하세요"
        print(f"User: {user_message}")
        
        response = await dialogue_manager.generate_response(
            user_id=user_id,
            user_message=user_message,
        )
        print(f"AI: {response}")
        
        await dialogue_manager.add_turn(
            user_id=user_id,
            user_message=user_message,
            assistant_message=response
        )
        
        # Manually verify if it has a question mark
        if turn >= 5:
            if "?" in response or "까?" in response:
                print("❌ FAIL: AI asked a question after turn 5!")
            else:
                print("✅ PASS: AI gracefully answered without asking a question.")

if __name__ == "__main__":
    asyncio.run(test_turn_limit())
