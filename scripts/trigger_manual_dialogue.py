import asyncio
import os
import sys
import argparse

# Add project root to sys.path
sys.path.append(os.getcwd())

from tasks.dialogue import send_scheduled_dialogue

async def trigger_manual(user_id: str):
    print(f"Manually triggering dialogue for user: {user_id}")
    result = await send_scheduled_dialogue(user_id)
    if result.get("success"):
        print(f"Success! Method: {result.get('method')}")
        print(f"Message sent: {result.get('message_sent')}")
    else:
        print(f"Failed: {result.get('error')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger manual dialogue message.")
    parser.add_argument("user_id", help="User UUID or kakao_id")
    args = parser.parse_args()
    
    asyncio.run(trigger_manual(args.user_id))
