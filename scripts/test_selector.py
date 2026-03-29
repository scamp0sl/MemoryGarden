import asyncio
import os
import sys

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.dialogue.category_selector import CategorySelector

async def test_selector():
    user_id = 'aa96e75d-70e2-4546-9001-043cc5db047d'
    selector = CategorySelector()
    
    # 1. Fetch current scores
    scores = await selector._fetch_indicator_averages(user_id)
    print("Scores:", scores)
    
    # 2. Fetch weekly usage
    usage = await selector._fetch_weekly_usage(user_id)
    print("Weekly Usage before:", usage)
    
    # 3. Simulate selection 5 times
    for i in range(5):
        cat = await selector.select(user_id)
        print(f"Selection {i+1}: {cat}")
        
    usage_after = await selector._fetch_weekly_usage(user_id)
    print("Weekly Usage after:", usage_after)

if __name__ == "__main__":
    asyncio.run(test_selector())
