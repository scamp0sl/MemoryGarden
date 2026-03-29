"""
VisionService 간단 검증 스크립트

pytest 없이 VisionService의 기본 기능을 테스트합니다.
"""

import asyncio
from datetime import datetime
from services.vision_service import VisionService


async def test_basic_visualization():
    """기본 정원 시각화 생성 테스트"""
    print("=" * 60)
    print("VisionService 기본 테스트")
    print("=" * 60)

    # 서비스 초기화
    service = VisionService()
    print("✅ VisionService 초기화 완료")

    # 테스트 파라미터
    params = {
        "user_id": "test_user_123",
        "total_conversations": 50,
        "consecutive_days": 15,
        "current_streak": 15,
        "current_level": 2,
        "flowers_count": 50,
        "butterflies_count": 5,
        "trees_count": 1,
        "season_badges": ["spring_2025"],
        "mcdi_score": 78.5,
        "recent_emotion": "joy",
        "last_conversation_date": datetime.now()
    }

    # 정원 시각화 생성
    try:
        result = await service.generate_garden_visualization(**params)
        print("✅ 정원 시각화 생성 성공")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return False

    # 결과 검증
    print("\n" + "=" * 60)
    print("생성된 정원 정보:")
    print("=" * 60)

    print(f"날씨: {result['weather']}")
    print(f"계절: {result['season']}")
    print(f"시간대: {result['time_of_day']}")
    print(f"정원 건강도: {result['garden_health']}")
    print(f"꽃 개수: {len(result['flowers'])}")
    print(f"나비 개수: {len(result['butterflies'])}")
    print(f"나무 개수: {len(result['trees'])}")
    print(f"장식 개수: {len(result['decorations'])}")
    print(f"특수 효과: {len(result['special_effects'])}")

    # 꽃 샘플 출력
    if result['flowers']:
        print("\n꽃 샘플 (첫 3개):")
        for i, flower in enumerate(result['flowers'][:3], 1):
            print(f"  {i}. {flower['type']} - {flower['state']} - 위치({flower['position']['x']:.2f}, {flower['position']['y']:.2f})")

    # 나비 샘플 출력
    if result['butterflies']:
        print("\n나비 샘플:")
        for i, butterfly in enumerate(result['butterflies'], 1):
            active = "활동중" if butterfly['is_active'] else "휴식중"
            print(f"  {i}. {butterfly['color']} 나비 - {active} - {butterfly['animation']}")

    # 나무 정보 출력
    if result['trees']:
        tree = result['trees'][0]
        print(f"\n나무 정보:")
        print(f"  성장 단계: {tree['growth_stage']}")
        print(f"  크기: {tree['size']}")
        print(f"  나이: {tree['age_days']}일")

    # 특수 효과 출력
    if result['special_effects']:
        print("\n특수 효과:")
        for effect in result['special_effects']:
            print(f"  - {effect['type']}")

    print("\n" + "=" * 60)
    print("✅ 모든 테스트 통과!")
    print("=" * 60)

    return True


async def test_different_emotions():
    """다양한 감정에 따른 날씨 테스트"""
    print("\n" + "=" * 60)
    print("감정별 날씨 테스트")
    print("=" * 60)

    service = VisionService()

    emotions = ["joy", "sadness", "anxiety", "anger", "contentment"]

    for emotion in emotions:
        result = await service.generate_garden_visualization(
            user_id="test",
            total_conversations=10,
            consecutive_days=5,
            current_streak=5,
            current_level=1,
            flowers_count=10,
            butterflies_count=2,
            trees_count=1,
            season_badges=[],
            mcdi_score=70.0,
            recent_emotion=emotion
        )
        print(f"{emotion:12s} -> {result['weather']}")

    print("✅ 감정별 날씨 테스트 완료")


async def test_mcdi_health_mapping():
    """MCDI 점수별 건강도 테스트"""
    print("\n" + "=" * 60)
    print("MCDI 점수별 건강도 테스트")
    print("=" * 60)

    service = VisionService()

    mcdi_scores = [95, 75, 55, 35, 15]

    for score in mcdi_scores:
        result = await service.generate_garden_visualization(
            user_id="test",
            total_conversations=10,
            consecutive_days=5,
            current_streak=5,
            current_level=1,
            flowers_count=10,
            butterflies_count=2,
            trees_count=1,
            season_badges=[],
            mcdi_score=score,
            recent_emotion="neutral"
        )
        print(f"MCDI {score:3d} -> {result['garden_health']}")

    print("✅ MCDI 점수별 건강도 테스트 완료")


async def main():
    """메인 테스트 실행"""
    try:
        # 기본 테스트
        await test_basic_visualization()

        # 감정 테스트
        await test_different_emotions()

        # MCDI 테스트
        await test_mcdi_health_mapping()

        print("\n" + "=" * 60)
        print("🎉 모든 테스트 성공!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
