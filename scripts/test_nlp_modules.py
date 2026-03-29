#!/usr/bin/env python3
"""
NLP 모듈 테스트 스크립트

감정 분석기와 키워드 추출기 테스트.

Usage:
    python scripts/test_nlp_modules.py
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.nlp import (
    EmotionDetector,
    EmotionCategory,
    KeywordExtractor,
    KeywordCategory,
)
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_emotion_detection():
    """감정 분석 테스트"""
    print("=" * 60)
    print("🔍 Emotion Detection Test")
    print("=" * 60)

    detector = EmotionDetector()

    # 테스트 케이스
    test_cases = [
        ("오늘 딸이 전화해서 정말 기분 좋았어요! 😊", EmotionCategory.JOY),
        ("요즘 혼자 있으니 외롭고 슬퍼요...", EmotionCategory.SADNESS),
        ("자꾸 잊어버려서 화가 나요", EmotionCategory.ANGER),
        ("내일 병원 가는 게 걱정돼요", EmotionCategory.FEAR),
        ("손녀가 갑자기 집에 왔어요!", EmotionCategory.SURPRISE),
        ("오늘은 날씨가 맑습니다", EmotionCategory.NEUTRAL),
    ]

    print("\n📝 Testing emotion detection on various texts...\n")

    success_count = 0
    for i, (text, expected) in enumerate(test_cases, 1):
        try:
            print(f"Test {i}: {text}")
            result = await detector.detect(text)

            emotion_kr = detector.get_emotion_label_kr(result.primary_emotion)
            expected_kr = detector.get_emotion_label_kr(expected)

            print(f"  ✅ Result: {emotion_kr} ({result.primary_emotion.value})")
            print(f"  📊 Intensity: {result.intensity:.2f}")
            if result.keywords:
                print(f"  🔑 Keywords: {', '.join(result.keywords[:3])}")
            print(f"  💭 Rationale: {result.rationale[:100]}...")

            # 검증
            if result.primary_emotion == expected:
                print(f"  ✓ Expected: {expected_kr} - MATCH!")
                success_count += 1
            else:
                print(f"  ✗ Expected: {expected_kr} - MISMATCH")

            print()

        except Exception as e:
            print(f"  ❌ Error: {e}\n")

    print(f"\n📈 Success Rate: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")
    print("=" * 60)

    return success_count == len(test_cases)


async def test_keyword_extraction():
    """키워드 추출 테스트"""
    print("\n" + "=" * 60)
    print("🔍 Keyword Extraction Test")
    print("=" * 60)

    extractor = KeywordExtractor(max_keywords=10)

    # 테스트 케이스
    test_cases = [
        "오늘 점심에 딸이 와서 된장찌개를 끓여줬어요. 정말 맛있었어요.",
        "어제 손녀 지우가 학교에서 상을 받았대요. 자랑스러워요!",
        "요즘 뒷산에 산책 나가면 단풍이 정말 아름다워요. 20년 전 남편과 자주 왔던 곳이에요.",
        "매일 아침 6시에 일어나서 운동하고, 7시에 아침 먹어요.",
    ]

    print("\n📝 Testing keyword extraction on various texts...\n")

    for i, text in enumerate(test_cases, 1):
        try:
            print(f"Test {i}: {text}")
            result = await extractor.extract(text)

            print(f"  🎯 Main Topic: {result.main_topic}")

            if result.sub_topics:
                print(f"  📌 Sub Topics: {', '.join(result.sub_topics)}")

            print(f"  🔑 Keywords ({len(result.keywords)}):")
            for kw in result.keywords[:5]:  # 상위 5개만 출력
                category_kr = extractor.get_category_label_kr(kw.category)
                print(f"     - {kw.word} ({category_kr}) [importance: {kw.importance:.2f}]")
                if kw.context:
                    print(f"       💬 {kw.context}")

            # 카테고리별 분류
            people = extractor.get_keywords_by_category(result, KeywordCategory.PERSON)
            places = extractor.get_keywords_by_category(result, KeywordCategory.PLACE)
            foods = extractor.get_keywords_by_category(result, KeywordCategory.FOOD)

            if people:
                print(f"  👤 People: {', '.join([kw.word for kw in people])}")
            if places:
                print(f"  📍 Places: {', '.join([kw.word for kw in places])}")
            if foods:
                print(f"  🍽️  Foods: {', '.join([kw.word for kw in foods])}")

            print()

        except Exception as e:
            print(f"  ❌ Error: {e}\n")

    print("=" * 60)
    return True


async def test_batch_processing():
    """배치 처리 테스트"""
    print("\n" + "=" * 60)
    print("🔍 Batch Processing Test")
    print("=" * 60)

    detector = EmotionDetector()
    extractor = KeywordExtractor()

    texts = [
        "오늘 기분이 좋아요!",
        "슬프고 외로워요",
        "화가 나네요"
    ]

    print(f"\n📝 Testing batch processing on {len(texts)} texts...\n")

    # 감정 배치 분석
    print("1️⃣ Emotion Detection (Batch)")
    emotion_results = await detector.detect_batch(texts)
    for text, result in zip(texts, emotion_results):
        emotion_kr = detector.get_emotion_label_kr(result.primary_emotion)
        print(f"  '{text}' → {emotion_kr} ({result.intensity:.2f})")

    print()

    # 키워드 배치 추출
    print("2️⃣ Keyword Extraction (Batch)")
    keyword_results = await extractor.extract_batch(texts)
    for text, result in zip(texts, keyword_results):
        keywords = [kw.word for kw in result.keywords[:3]]
        print(f"  '{text}' → {', '.join(keywords)}")

    print("\n" + "=" * 60)
    return True


async def test_integration():
    """통합 테스트 (감정 + 키워드)"""
    print("\n" + "=" * 60)
    print("🔍 Integration Test (Emotion + Keywords)")
    print("=" * 60)

    detector = EmotionDetector()
    extractor = KeywordExtractor()

    text = """
    오늘 딸 수진이가 손녀 지우를 데리고 집에 왔어요.
    지우가 학교에서 그림 그리기 대회에서 상을 받았대요.
    정말 자랑스럽고 기뻐요! 저녁에 같이 삼겹살도 구워 먹었어요.
    """

    print(f"\n📝 Text: {text.strip()}\n")

    # 감정 분석
    print("1️⃣ Emotion Analysis:")
    emotion_result = await detector.detect(text)
    emotion_kr = detector.get_emotion_label_kr(emotion_result.primary_emotion)
    print(f"  Primary: {emotion_kr} (intensity: {emotion_result.intensity:.2f})")
    print(f"  Keywords: {', '.join(emotion_result.keywords[:5])}")

    print()

    # 키워드 추출
    print("2️⃣ Keyword Extraction:")
    keyword_result = await extractor.extract(text)
    print(f"  Main Topic: {keyword_result.main_topic}")
    print(f"  Keywords:")
    for kw in keyword_result.keywords[:5]:
        category_kr = extractor.get_category_label_kr(kw.category)
        print(f"    - {kw.word} ({category_kr}) [{kw.importance:.2f}]")

    print("\n" + "=" * 60)
    return True


async def main():
    """메인 테스트 실행"""
    print("\n")
    print("=" * 60)
    print("🚀 NLP Modules Test Suite")
    print("=" * 60)

    try:
        # 1. 감정 분석 테스트
        emotion_success = await test_emotion_detection()

        # 2. 키워드 추출 테스트
        keyword_success = await test_keyword_extraction()

        # 3. 배치 처리 테스트
        batch_success = await test_batch_processing()

        # 4. 통합 테스트
        integration_success = await test_integration()

        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"  Emotion Detection: {'✅ PASS' if emotion_success else '❌ FAIL'}")
        print(f"  Keyword Extraction: {'✅ PASS' if keyword_success else '❌ FAIL'}")
        print(f"  Batch Processing: {'✅ PASS' if batch_success else '❌ FAIL'}")
        print(f"  Integration Test: {'✅ PASS' if integration_success else '❌ FAIL'}")
        print("=" * 60)

        all_success = all([emotion_success, keyword_success, batch_success, integration_success])

        if all_success:
            print("\n✅ All tests passed!")
            print("\n📌 Next steps:")
            print("   1. Integrate with message processor")
            print("   2. Store emotions in episodic memory")
            print("   3. Use keywords for fact extraction")
            print("=" * 60)
            return True
        else:
            print("\n⚠️  Some tests failed. Check logs for details.")
            return False

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
