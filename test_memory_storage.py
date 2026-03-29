"""메모리 저장 기능 테스트"""
import asyncio
from core.memory.memory_manager import MemoryManager
from core.nlp.embedder import Embedder

async def test_memory_storage():
    """메모리 저장 테스트"""
    user_id = "aa96e75d-70e2-4546-9001-043cc5db047d"
    message = "엄마가 봄에 쑥을 캐러 뒷산에 가셔서 쑥떡을 만들어주셨어요. 그 맛을 잊을 수가 없어요"
    response = "쑥을 캐서 쑥떡을 만드셨군요! 봄마다의 소중한 추억이네요."

    print(f"테스트 사용자 ID: {user_id}")
    print(f"메시지: {message}")
    print()

    # 가짜 MCDI 분석 결과
    fake_analysis = {
        "mcdi_score": 85.0,
        "mcdi_details": {"risk_category": "GREEN"},
        "scores": {"LR": 80, "SD": 85, "NC": 90, "TO": 85, "ER": 85, "RT": 80},
        "emotion_vector": {"v": 0.7, "a": 0.3, "i": 0.5},
        "samantha_emotion": "기쁨",
        "follow_up_notes": ["쑥 캐는 이야기", "어머니와의 추억"]
    }

    # 메모리 매니저로 저장
    print("4계층 메모리 저장 시작...")
    memory_manager = MemoryManager(embedder=Embedder())

    stored = await memory_manager.store_all(
        user_id=user_id,
        message=message,
        response=response,
        analysis=fake_analysis
    )

    print(f"   - 세션 저장: {stored.get('session_stored', False)}")
    print(f"   - 저장된 에피소드: {stored.get('episodic_stored', 0)}개")
    print(f"   - 저장된 전기적 사실: {stored.get('biographical_stored', 0)}개")
    print(f"   - 분석 저장: {stored.get('analytical_stored', False)}")
    print()

    # 저장된 메모리 검증
    print("저장된 메모리 검증...")
    retrieved = await memory_manager.retrieve_all(
        user_id=user_id,
        query="쑥 떡",
        limit=5
    )

    print(f"   - 검색된 에피소드: {len(retrieved.get('episodic', []))}개")
    for mem in retrieved.get('episodic', [])[:3]:
        print(f"     * {mem.get('content', '')[:80]}... (유사도: {mem.get('score', 0):.2f})")

    biog = retrieved.get('biographical', {})
    print(f"   - 검색된 전기적 사실: {len(biog) if isinstance(biog, dict) else 0}개")
    if isinstance(biog, dict):
        for key, value in list(biog.items())[:5]:
            print(f"     * {key}: {value}")

    print()
    print("테스트 완료!")

if __name__ == "__main__":
    asyncio.run(test_memory_storage())
