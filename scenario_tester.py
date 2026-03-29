import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env vars to ensure we have OpenAI/Anthropic keys for real generation
load_dotenv()

from core.dialogue.response_generator import ResponseGenerator

async def run_scenario(
    scenario_name, 
    user_message, 
    biographical_facts=None, 
    emotion_history=None, 
    emotion_intensity=0.5,
    quiz_feedback_instruction=None
):
    print(f"\n{'='*70}")
    print(f"▶ {scenario_name}")
    print(f"{'='*70}")
    print(f"👤 사용자 입력: {user_message}")
    if biographical_facts:
        print(f"🧠 삽입된 메모리 컨텍스트: {biographical_facts}")
    if emotion_history:
        print(f"❤️ 감정 관성 버퍼: {emotion_history}")
    if quiz_feedback_instruction:
        print(f"📝 퀴즈 피드백 지시: {quiz_feedback_instruction}")
    
    rg = ResponseGenerator()
    user_context = {"user_name": "고객님"}
    if biographical_facts:
        user_context["biographical_facts"] = biographical_facts
    if emotion_history:
        user_context["emotion_history"] = emotion_history
    if quiz_feedback_instruction:
        user_context["quiz_feedback_instruction"] = quiz_feedback_instruction
        
    print("\n⏳ 사만다(AI) 응답 생성 중...\n")
    try:
        # 최근 감정은 emotion_history의 마지막 요소로 간주
        detected_emotion = emotion_history[-1] if emotion_history else "neutral"
        
        response = await rg.generate_empathetic_response(
            user_message=user_message,
            detected_emotion=detected_emotion,
            emotion_intensity=emotion_intensity,
            conversation_history=[],
            user_context=user_context
        )
        print(f"🤖 사만다(AI) 대답:\n{response}")
        print(f"\n[{scenario_name} 종료]\n")
        return response
    except Exception as e:
        print(f"Error during generation: {e}")
        return str(e)

async def main():
    # TC 1. 감정적 관성 (Emotional Inertia) 동작 테스트
    await run_scenario(
        "TC 1: Emotional Inertia (감정적 관성)",
        user_message="응, 그냥 밥이나 먹으려고 휴...",
        emotion_history=["sadness", "sadness", "neutral"],
        emotion_intensity=0.5
    )
    
    # TC 2. 입체적 융합 기억 + AI 자아 노출 (Synthesized Memory & Vulnerability)
    await run_scenario(
        "TC 2: Synthesized Memory & Vulnerability (입체 기억 + 호기심)",
        user_message="오늘 하루 종일 비 오네... 집에 갇혔어 ㅠㅠ",
        biographical_facts={"hobby": "수채화 그리기", "favorite_food": "파전"},
        emotion_history=["neutral", "neutral"],
        emotion_intensity=0.5
    )

    # TC 3. 친근한 장난기와 위트 (Playful Banter) 발동
    await run_scenario(
        "TC 3: Playful Banter (친근한 장난기/밀당)",
        user_message="아 큰일 났다 ㅋㅋ 늦잠 자서 지각이야 부장님한테 죽었다 ㅠㅠ",
        emotion_history=["neutral"],
        emotion_intensity=0.5
    )
    
    # TC 4. [회귀 방어] 깊은 위로 모드 오버라이딩 (Regression: Deep Comforting)
    await run_scenario(
        "TC 4: [Regression] Deep Comforting (위로 모드 하드 오버라이드)",
        user_message="진짜 세상에 내 편이 하나도 없는 것 같아... 너무 외로워.",
        emotion_history=["neutral", "sadness"],
        emotion_intensity=0.9
    )
    
    # TC 5. [회귀 방어] ER 퀴즈 피드백 훼손 검증 (Regression: ER Quiz Integrity)
    await run_scenario(
        "TC 5: [Regression] ER Quiz Integrity (퀴즈 피드백 문자열 유지 확인)",
        user_message="어제 라면 먹었지 ㅎㅎ 아 피곤하네 이제 자야지",
        emotion_history=["neutral", "neutral"],
        emotion_intensity=0.5,
        quiz_feedback_instruction="[정답 인정] 맞아요! 어제 점심으로 라면을 드셨죠."
    )

if __name__ == "__main__":
    asyncio.run(main())
