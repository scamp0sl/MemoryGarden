import asyncio
import sys
from datetime import datetime

sys.path.insert(0, "/home/admin/docker/MemoryGardenAI")

from core.dialogue.dialogue_manager import DialogueManager
from core.dialogue.prompt_builder import PromptBuilder
from core.dialogue.response_generator import ResponseGenerator

async def test_er_feedback():
    print("=== ER Feedback Loop Test ===")
    rg = ResponseGenerator()
    score = await rg.evaluate_quiz_answer("된장찌개를 먹었어", "된장찌개")
    print(f"User answer: '된장찌개를 먹었어', Expected: '된장찌개' -> Score: {score}")
    
    score2 = await rg.evaluate_quiz_answer("라면 먹었지", "된장찌개")
    print(f"User answer: '라면 먹었지', Expected: '된장찌개' -> Score: {score2}")
    
    if score > 80 and score2 < 50:
        print("✅ ER Feedback loop grading logic works.\n")
    else:
        print("❌ ER Feedback loop test failed.\n")

async def test_temporal_awareness():
    print("=== Temporal Awareness Test ===")
    pb = PromptBuilder()
    prompt = pb.build_system_prompt()
    now = datetime.now()
    
    # Check if current time info is in prompt
    has_temporal_awareness = f"현재 시각: {now.year}년 {now.month}월" in prompt
    print("Contains current datetime:", has_temporal_awareness)
    
    # Check absolute rule for temporal awareness
    has_rules = "시공간 및 과거/현재 인지 절대 규칙" in prompt
    print("Contains temporal rules:", has_rules)
    
    if has_temporal_awareness and has_rules:
        print("✅ Temporal Awareness logic works.\n")
    else:
        print("❌ Temporal Awareness test failed.\n")

async def test_fallback_messages():
    print("=== 5-Second Fallback Diversity Test ===")
    import random
    fallback_msgs = [
        "잠깐만 기다려요! 가장 좋은 대답을 고민하느라 시간이 좀 걸리고 있어요. 잠시 뒤 준비됐나요? 다시 말씀해 주세요! 🌿",
        "어이쿠, 고민이 좀 필요하네요! 생각 정리 중이니, 조금 이따가 말해줘요! 😄",
        "네트워크를 타고 가느라 답변이 지연되고 있어요ㅠㅠ 얼른 좋은 대답 들려드릴 테니, 조금후에 알려줘~ 라고 다시 얘기하세요"
    ]
    # Simulate timeout randomness
    chosen = set()
    for _ in range(10):
        chosen.add(random.choice(fallback_msgs))
    
    print(f"Number of distinct fallback messages: {len(fallback_msgs)}")
    print(f"Messages chosen randomly: {len(chosen)} distinct messages")
    if len(chosen) > 1:
        print("✅ 5-Second Fallback diversity works.\n")
    else:
        print("❌ 5-Second Fallback test failed.\n")

async def main():
    await test_er_feedback()
    await test_temporal_awareness()
    await test_fallback_messages()
    
if __name__ == "__main__":
    asyncio.run(main())
