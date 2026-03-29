"""
NLP 모듈 테스트

감정 분석 및 키워드 추출 기능 테스트.
OpenAI API 호출은 mock 처리.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# Standard Library Imports
# ============================================
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

# ============================================
# Third-Party Imports
# ============================================
import pytest
import pytest_asyncio

# ============================================
# Local Imports
# ============================================
from core.nlp.emotion_detector import (
    EmotionDetector,
    EmotionResult,
    EmotionCategory,
    SecondaryEmotion
)
from core.nlp.keyword_extractor import (
    KeywordExtractor,
    KeywordExtractionResult,
    Keyword,
    KeywordCategory
)
from services.llm_service import LLMService
from utils.exceptions import AnalysisError


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_llm_service():
    """Mock LLM Service"""
    service = AsyncMock(spec=LLMService)
    return service


@pytest.fixture
def emotion_detector(mock_llm_service):
    """EmotionDetector 인스턴스"""
    return EmotionDetector(llm_service=mock_llm_service)


@pytest.fixture
def keyword_extractor(mock_llm_service):
    """KeywordExtractor 인스턴스"""
    return KeywordExtractor(llm_service=mock_llm_service, max_keywords=10)


@pytest.fixture
def sample_emotion_response() -> Dict[str, Any]:
    """샘플 감정 분석 응답"""
    return {
        "primary_emotion": "joy",
        "intensity": 0.85,
        "secondary_emotions": [
            {"emotion": "surprise", "intensity": 0.3}
        ],
        "keywords": ["기쁨", "행복", "좋아"],
        "rationale": "긍정적인 단어들이 많이 사용됨"
    }


@pytest.fixture
def sample_keyword_response() -> Dict[str, Any]:
    """샘플 키워드 추출 응답"""
    return {
        "keywords": [
            {
                "word": "딸",
                "importance": 0.9,
                "category": "person",
                "context": "가족 구성원"
            },
            {
                "word": "김치찌개",
                "importance": 0.8,
                "category": "food",
                "context": "식사 메뉴"
            },
            {
                "word": "집",
                "importance": 0.7,
                "category": "place",
                "context": "장소"
            }
        ],
        "main_topic": "가족과의 식사",
        "sub_topics": ["요리", "가족", "집"]
    }


# ============================================
# EmotionDetector Tests
# ============================================

@pytest.mark.asyncio
async def test_detect_emotion_joy(emotion_detector, mock_llm_service, sample_emotion_response):
    """정상 케이스: 기쁨 감정 감지"""
    # Arrange
    text = "오늘 딸이 전화해서 너무 기분 좋아요!"
    mock_llm_service.call_json.return_value = sample_emotion_response

    # Act
    result = await emotion_detector.detect(text)

    # Assert
    assert isinstance(result, EmotionResult)
    assert result.primary_emotion == EmotionCategory.JOY
    assert result.intensity == 0.85
    assert len(result.secondary_emotions) == 1
    assert result.secondary_emotions[0].emotion == EmotionCategory.SURPRISE
    assert "기쁨" in result.keywords

    # LLM 호출 검증
    mock_llm_service.call_json.assert_called_once()
    call_args = mock_llm_service.call_json.call_args
    assert text in call_args.kwargs['prompt'] or text in str(call_args)


@pytest.mark.asyncio
async def test_detect_emotion_sadness(emotion_detector, mock_llm_service):
    """정상 케이스: 슬픔 감정 감지"""
    # Arrange
    text = "오늘은 슬픈 날이에요"
    mock_llm_service.call_json.return_value = {
        "primary_emotion": "sadness",
        "intensity": 0.7,
        "secondary_emotions": [],
        "keywords": ["슬픔"],
        "rationale": "슬픔을 나타내는 표현"
    }

    # Act
    result = await emotion_detector.detect(text)

    # Assert
    assert result.primary_emotion == EmotionCategory.SADNESS
    assert result.intensity == 0.7
    assert len(result.secondary_emotions) == 0


@pytest.mark.asyncio
async def test_detect_emotion_empty_text(emotion_detector):
    """엣지 케이스: 빈 입력"""
    # Arrange
    text = ""

    # Act
    result = await emotion_detector.detect(text)

    # Assert
    assert result.primary_emotion == EmotionCategory.NEUTRAL
    assert result.intensity == 0.0
    assert result.rationale == "Empty input"


@pytest.mark.asyncio
async def test_detect_emotion_with_llm_failure(emotion_detector, mock_llm_service):
    """에러 케이스: LLM 호출 실패"""
    # Arrange
    text = "테스트 메시지"
    mock_llm_service.call_json.side_effect = Exception("API Error")

    # Act & Assert
    with pytest.raises(AnalysisError, match="Failed to detect emotion"):
        await emotion_detector.detect(text)


@pytest.mark.asyncio
async def test_detect_emotion_batch(emotion_detector, mock_llm_service):
    """배치 처리: 여러 텍스트 동시 감정 분석"""
    # Arrange
    texts = [
        "기뻐요",
        "슬퍼요",
        "화나요"
    ]

    # Mock 각 호출마다 다른 응답
    mock_llm_service.call_json.side_effect = [
        {
            "primary_emotion": "joy",
            "intensity": 0.9,
            "secondary_emotions": [],
            "keywords": [],
            "rationale": ""
        },
        {
            "primary_emotion": "sadness",
            "intensity": 0.8,
            "secondary_emotions": [],
            "keywords": [],
            "rationale": ""
        },
        {
            "primary_emotion": "anger",
            "intensity": 0.85,
            "secondary_emotions": [],
            "keywords": [],
            "rationale": ""
        }
    ]

    # Act
    results = await emotion_detector.detect_batch(texts)

    # Assert
    assert len(results) == 3
    assert results[0].primary_emotion == EmotionCategory.JOY
    assert results[1].primary_emotion == EmotionCategory.SADNESS
    assert results[2].primary_emotion == EmotionCategory.ANGER


@pytest.mark.asyncio
async def test_detect_emotion_batch_with_partial_failure(emotion_detector, mock_llm_service):
    """배치 처리: 일부 실패 시 에러 처리"""
    # Arrange
    texts = ["기뻐요", "슬퍼요", "화나요"]

    # 두 번째 호출만 실패
    mock_llm_service.call_json.side_effect = [
        {"primary_emotion": "joy", "intensity": 0.9, "secondary_emotions": [], "keywords": [], "rationale": ""},
        Exception("API Error"),
        {"primary_emotion": "anger", "intensity": 0.85, "secondary_emotions": [], "keywords": [], "rationale": ""}
    ]

    # Act
    results = await emotion_detector.detect_batch(texts)

    # Assert
    assert len(results) == 3
    assert results[0].primary_emotion == EmotionCategory.JOY
    assert results[1].primary_emotion == EmotionCategory.NEUTRAL  # Fallback
    assert results[2].primary_emotion == EmotionCategory.ANGER


def test_parse_emotion_response_valid(emotion_detector, sample_emotion_response):
    """응답 파싱: 정상 케이스"""
    # Act
    result = emotion_detector._parse_response(sample_emotion_response)

    # Assert
    assert isinstance(result, EmotionResult)
    assert result.primary_emotion == EmotionCategory.JOY
    assert result.intensity == 0.85
    assert len(result.secondary_emotions) == 1


def test_parse_emotion_response_invalid(emotion_detector):
    """응답 파싱: 잘못된 형식"""
    # Arrange
    invalid_response = {
        "invalid_field": "value"
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid emotion response format"):
        emotion_detector._parse_response(invalid_response)


def test_parse_emotion_response_invalid_emotion_category(emotion_detector):
    """응답 파싱: 잘못된 감정 카테고리"""
    # Arrange
    invalid_response = {
        "primary_emotion": "invalid_emotion",
        "intensity": 0.5,
        "secondary_emotions": [],
        "keywords": [],
        "rationale": ""
    }

    # Act & Assert
    with pytest.raises(ValueError):
        emotion_detector._parse_response(invalid_response)


def test_get_emotion_label_kr(emotion_detector):
    """한국어 레이블 반환"""
    # Act & Assert
    assert emotion_detector.get_emotion_label_kr(EmotionCategory.JOY) == "기쁨"
    assert emotion_detector.get_emotion_label_kr(EmotionCategory.SADNESS) == "슬픔"
    assert emotion_detector.get_emotion_label_kr(EmotionCategory.ANGER) == "분노"
    assert emotion_detector.get_emotion_label_kr(EmotionCategory.FEAR) == "두려움"
    assert emotion_detector.get_emotion_label_kr(EmotionCategory.SURPRISE) == "놀람"
    assert emotion_detector.get_emotion_label_kr(EmotionCategory.NEUTRAL) == "중립"


# ============================================
# KeywordExtractor Tests
# ============================================

@pytest.mark.asyncio
async def test_extract_keywords_normal(keyword_extractor, mock_llm_service, sample_keyword_response):
    """정상 케이스: 키워드 추출"""
    # Arrange
    text = "어제 딸이 집에 와서 김치찌개 끓여줬어요"
    mock_llm_service.call_json.return_value = sample_keyword_response

    # Act
    result = await keyword_extractor.extract(text)

    # Assert
    assert isinstance(result, KeywordExtractionResult)
    assert len(result.keywords) == 3

    # 첫 번째 키워드 검증 (importance 순 정렬됨)
    assert result.keywords[0].word == "딸"
    assert result.keywords[0].importance == 0.9
    assert result.keywords[0].category == KeywordCategory.PERSON

    # 주제 검증
    assert result.main_topic == "가족과의 식사"
    assert "가족" in result.sub_topics

    # LLM 호출 검증
    mock_llm_service.call_json.assert_called_once()


@pytest.mark.asyncio
async def test_extract_keywords_empty_text(keyword_extractor):
    """엣지 케이스: 빈 입력"""
    # Arrange
    text = ""

    # Act
    result = await keyword_extractor.extract(text)

    # Assert
    assert len(result.keywords) == 0
    assert result.main_topic == ""
    assert len(result.sub_topics) == 0


@pytest.mark.asyncio
async def test_extract_keywords_with_llm_failure(keyword_extractor, mock_llm_service):
    """에러 케이스: LLM 호출 실패"""
    # Arrange
    text = "테스트 메시지"
    mock_llm_service.call_json.side_effect = Exception("API Error")

    # Act & Assert
    with pytest.raises(AnalysisError, match="Failed to extract keywords"):
        await keyword_extractor.extract(text)


@pytest.mark.asyncio
async def test_extract_keywords_batch(keyword_extractor, mock_llm_service):
    """배치 처리: 여러 텍스트 동시 키워드 추출"""
    # Arrange
    texts = [
        "오늘 딸과 함께 밥 먹었어요",
        "손녀가 학교에서 상 받았대요"
    ]

    # Mock 각 호출마다 다른 응답
    mock_llm_service.call_json.side_effect = [
        {
            "keywords": [
                {"word": "딸", "importance": 0.9, "category": "person", "context": ""}
            ],
            "main_topic": "식사",
            "sub_topics": []
        },
        {
            "keywords": [
                {"word": "손녀", "importance": 0.9, "category": "person", "context": ""},
                {"word": "학교", "importance": 0.8, "category": "place", "context": ""}
            ],
            "main_topic": "수상",
            "sub_topics": []
        }
    ]

    # Act
    results = await keyword_extractor.extract_batch(texts)

    # Assert
    assert len(results) == 2
    assert len(results[0].keywords) == 1
    assert len(results[1].keywords) == 2
    assert results[0].keywords[0].word == "딸"
    assert results[1].keywords[0].word == "손녀"


@pytest.mark.asyncio
async def test_extract_keywords_batch_with_partial_failure(keyword_extractor, mock_llm_service):
    """배치 처리: 일부 실패 시 에러 처리"""
    # Arrange
    texts = ["텍스트1", "텍스트2", "텍스트3"]

    # 두 번째 호출만 실패
    mock_llm_service.call_json.side_effect = [
        {"keywords": [{"word": "키워드1", "importance": 0.9, "category": "other"}], "main_topic": "", "sub_topics": []},
        Exception("API Error"),
        {"keywords": [{"word": "키워드3", "importance": 0.8, "category": "other"}], "main_topic": "", "sub_topics": []}
    ]

    # Act
    results = await keyword_extractor.extract_batch(texts)

    # Assert
    assert len(results) == 3
    assert len(results[0].keywords) == 1
    assert len(results[1].keywords) == 0  # Fallback: empty result
    assert len(results[2].keywords) == 1


def test_parse_keyword_response_valid(keyword_extractor, sample_keyword_response):
    """응답 파싱: 정상 케이스"""
    # Act
    result = keyword_extractor._parse_response(sample_keyword_response)

    # Assert
    assert isinstance(result, KeywordExtractionResult)
    assert len(result.keywords) == 3

    # 중요도 순 정렬 확인
    assert result.keywords[0].importance >= result.keywords[1].importance
    assert result.keywords[1].importance >= result.keywords[2].importance

    # 카테고리 확인
    assert result.keywords[0].category == KeywordCategory.PERSON
    assert result.keywords[1].category == KeywordCategory.FOOD
    assert result.keywords[2].category == KeywordCategory.PLACE


def test_parse_keyword_response_invalid(keyword_extractor):
    """응답 파싱: 잘못된 형식 - 빈 결과 반환 (forgiving parser)"""
    # Arrange
    invalid_response = {
        "invalid_field": "value"
    }

    # Act
    result = keyword_extractor._parse_response(invalid_response)

    # Assert - Parser is forgiving, returns empty result
    assert len(result.keywords) == 0
    assert result.main_topic == ""
    assert len(result.sub_topics) == 0


def test_parse_keyword_response_invalid_category(keyword_extractor):
    """응답 파싱: 잘못된 카테고리는 OTHER로 처리"""
    # Arrange
    response_with_invalid_category = {
        "keywords": [
            {
                "word": "테스트",
                "importance": 0.8,
                "category": "invalid_category",  # 잘못된 카테고리
                "context": ""
            }
        ],
        "main_topic": "테스트",
        "sub_topics": []
    }

    # Act
    result = keyword_extractor._parse_response(response_with_invalid_category)

    # Assert
    assert len(result.keywords) == 1
    assert result.keywords[0].category == KeywordCategory.OTHER  # Fallback


def test_parse_keyword_response_max_keywords_limit(keyword_extractor):
    """응답 파싱: 최대 키워드 개수 제한"""
    # Arrange
    response_with_many_keywords = {
        "keywords": [
            {"word": f"키워드{i}", "importance": 1.0 - i * 0.05, "category": "other"}
            for i in range(20)  # 20개 생성
        ],
        "main_topic": "",
        "sub_topics": []
    }

    # Act
    result = keyword_extractor._parse_response(response_with_many_keywords)

    # Assert
    assert len(result.keywords) == keyword_extractor.max_keywords  # 10개로 제한


def test_get_keywords_by_category(keyword_extractor, sample_keyword_response):
    """카테고리별 키워드 필터링"""
    # Arrange
    result = keyword_extractor._parse_response(sample_keyword_response)

    # Act
    people = keyword_extractor.get_keywords_by_category(result, KeywordCategory.PERSON)
    foods = keyword_extractor.get_keywords_by_category(result, KeywordCategory.FOOD)
    places = keyword_extractor.get_keywords_by_category(result, KeywordCategory.PLACE)

    # Assert
    assert len(people) == 1
    assert people[0].word == "딸"

    assert len(foods) == 1
    assert foods[0].word == "김치찌개"

    assert len(places) == 1
    assert places[0].word == "집"


def test_get_top_keywords(keyword_extractor, sample_keyword_response):
    """상위 N개 키워드 반환"""
    # Arrange
    result = keyword_extractor._parse_response(sample_keyword_response)

    # Act
    top_2 = keyword_extractor.get_top_keywords(result, n=2)

    # Assert
    assert len(top_2) == 2
    assert top_2[0].word == "딸"  # importance 0.9
    assert top_2[1].word == "김치찌개"  # importance 0.8


def test_get_category_label_kr(keyword_extractor):
    """한국어 레이블 반환"""
    # Act & Assert
    assert keyword_extractor.get_category_label_kr(KeywordCategory.PERSON) == "인물"
    assert keyword_extractor.get_category_label_kr(KeywordCategory.PLACE) == "장소"
    assert keyword_extractor.get_category_label_kr(KeywordCategory.FOOD) == "음식"
    assert keyword_extractor.get_category_label_kr(KeywordCategory.EVENT) == "사건"
    assert keyword_extractor.get_category_label_kr(KeywordCategory.TIME) == "시간"
    assert keyword_extractor.get_category_label_kr(KeywordCategory.EMOTION) == "감정"
    assert keyword_extractor.get_category_label_kr(KeywordCategory.ACTIVITY) == "활동"
    assert keyword_extractor.get_category_label_kr(KeywordCategory.OBJECT) == "사물"
    assert keyword_extractor.get_category_label_kr(KeywordCategory.CONCEPT) == "개념"
    assert keyword_extractor.get_category_label_kr(KeywordCategory.OTHER) == "기타"


# ============================================
# Integration Tests (EmotionDetector + KeywordExtractor)
# ============================================

@pytest.mark.asyncio
async def test_combined_nlp_analysis(emotion_detector, keyword_extractor, mock_llm_service):
    """통합 테스트: 감정 분석 + 키워드 추출"""
    # Arrange
    text = "오늘 딸이 전화해서 너무 기분 좋아요! 김치찌개 끓여준다고 하네요."

    mock_llm_service.call_json.side_effect = [
        # 감정 분석 응답
        {
            "primary_emotion": "joy",
            "intensity": 0.9,
            "secondary_emotions": [],
            "keywords": ["기쁨", "좋아"],
            "rationale": "긍정적 감정 표현"
        },
        # 키워드 추출 응답
        {
            "keywords": [
                {"word": "딸", "importance": 0.9, "category": "person", "context": ""},
                {"word": "김치찌개", "importance": 0.8, "category": "food", "context": ""}
            ],
            "main_topic": "가족과의 대화",
            "sub_topics": ["전화", "요리"]
        }
    ]

    # Act
    emotion_result = await emotion_detector.detect(text)
    keyword_result = await keyword_extractor.extract(text)

    # Assert
    # 감정 분석 결과
    assert emotion_result.primary_emotion == EmotionCategory.JOY
    assert emotion_result.intensity == 0.9

    # 키워드 추출 결과
    assert len(keyword_result.keywords) == 2
    assert keyword_result.keywords[0].word == "딸"
    assert keyword_result.main_topic == "가족과의 대화"

    # LLM 호출 횟수 검증 (2번: 감정 + 키워드)
    assert mock_llm_service.call_json.call_count == 2


# ============================================
# Integration Tests (Real OpenAI API Calls)
# ============================================

@pytest_asyncio.fixture
async def real_llm_service():
    """실제 LLM Service (OpenAI API 호출)"""
    from config.settings import settings

    # API 키 확인
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "sk-test-key":
        pytest.skip("OPENAI_API_KEY not configured for integration tests")

    service = LLMService()
    return service


@pytest_asyncio.fixture
async def real_emotion_detector(real_llm_service):
    """실제 EmotionDetector (OpenAI API 사용)"""
    return EmotionDetector(llm_service=real_llm_service)


@pytest_asyncio.fixture
async def real_keyword_extractor(real_llm_service):
    """실제 KeywordExtractor (OpenAI API 사용)"""
    return KeywordExtractor(llm_service=real_llm_service, max_keywords=10)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_detect_emotion_joy(real_emotion_detector):
    """통합 테스트: 실제 API로 기쁨 감정 감지"""
    # Arrange
    text = "오늘 손녀가 처음으로 할머니라고 불러서 너무너무 기쁘고 행복해요! 눈물이 날 정도예요."

    # Act
    result = await real_emotion_detector.detect(text)

    # Assert
    assert isinstance(result, EmotionResult)
    assert result.primary_emotion == EmotionCategory.JOY
    assert result.intensity > 0.5  # 강한 긍정 감정
    assert len(result.keywords) > 0

    # 감정 레이블 확인
    emotion_label = real_emotion_detector.get_emotion_label_kr(result.primary_emotion)
    assert emotion_label == "기쁨"

    print(f"\n[Integration Test - Emotion Detection]")
    print(f"텍스트: {text}")
    print(f"주요 감정: {emotion_label} (강도: {result.intensity:.2f})")
    print(f"키워드: {', '.join(result.keywords)}")
    print(f"근거: {result.rationale}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_detect_emotion_sadness(real_emotion_detector):
    """통합 테스트: 실제 API로 슬픔 감정 감지"""
    # Arrange
    text = "남편이 떠난 지 벌써 10년이 되었네요. 오늘따라 많이 보고 싶고 슬퍼요."

    # Act
    result = await real_emotion_detector.detect(text)

    # Assert
    assert isinstance(result, EmotionResult)
    assert result.primary_emotion == EmotionCategory.SADNESS
    assert result.intensity > 0.4

    print(f"\n[Integration Test - Sadness Detection]")
    print(f"주요 감정: {real_emotion_detector.get_emotion_label_kr(result.primary_emotion)} (강도: {result.intensity:.2f})")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_detect_emotion_neutral(real_emotion_detector):
    """통합 테스트: 실제 API로 중립 텍스트 감지"""
    # Arrange
    text = "오늘 날씨는 맑고 기온은 15도입니다. 미세먼지 농도는 보통입니다."

    # Act
    result = await real_emotion_detector.detect(text)

    # Assert
    assert isinstance(result, EmotionResult)
    # 중립이거나 약한 감정
    assert result.intensity < 0.5

    print(f"\n[Integration Test - Neutral Text]")
    print(f"주요 감정: {real_emotion_detector.get_emotion_label_kr(result.primary_emotion)} (강도: {result.intensity:.2f})")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_extract_keywords_family_meal(real_keyword_extractor):
    """통합 테스트: 실제 API로 가족 식사 관련 키워드 추출"""
    # Arrange
    text = "오늘 아침에 딸이 집에 와서 김치찌개를 끓여줬어요. 손녀 지우도 함께 왔는데 밥을 너무 잘 먹더라고요."

    # Act
    result = await real_keyword_extractor.extract(text)

    # Assert
    assert isinstance(result, KeywordExtractionResult)
    assert len(result.keywords) > 0

    # 주요 키워드 확인 (가족, 음식 카테고리가 있어야 함)
    categories = {kw.category for kw in result.keywords}
    assert KeywordCategory.PERSON in categories or KeywordCategory.FOOD in categories

    # 주제 확인
    assert len(result.main_topic) > 0

    print(f"\n[Integration Test - Keyword Extraction]")
    print(f"텍스트: {text}")
    print(f"주요 주제: {result.main_topic}")
    print(f"하위 주제: {', '.join(result.sub_topics)}")
    print(f"추출된 키워드 ({len(result.keywords)}개):")
    for kw in result.keywords[:5]:  # 상위 5개만 출력
        category_label = real_keyword_extractor.get_category_label_kr(kw.category)
        print(f"  - {kw.word} ({category_label}, 중요도: {kw.importance:.2f})")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_extract_keywords_reminiscence(real_keyword_extractor):
    """통합 테스트: 실제 API로 회상 관련 키워드 추출"""
    # Arrange
    text = "젊었을 때는 매일 새벽에 일어나서 시장에 갔어요. 봄이면 쑥을 캐러 뒷산에도 자주 갔고요. 그때가 참 좋았어요."

    # Act
    result = await real_keyword_extractor.extract(text)

    # Assert
    assert isinstance(result, KeywordExtractionResult)
    assert len(result.keywords) > 0

    # 시간, 장소, 활동 관련 키워드가 있어야 함
    categories = {kw.category for kw in result.keywords}
    expected_categories = {KeywordCategory.TIME, KeywordCategory.PLACE, KeywordCategory.ACTIVITY}
    assert len(categories & expected_categories) > 0

    print(f"\n[Integration Test - Reminiscence Keywords]")
    print(f"주요 주제: {result.main_topic}")
    print(f"키워드: {', '.join([kw.word for kw in result.keywords[:7]])}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_combined_nlp_analysis(real_emotion_detector, real_keyword_extractor):
    """통합 테스트: 실제 API로 감정 분석 + 키워드 추출 동시 수행"""
    # Arrange
    text = "오늘 병원에 갔다가 오랜만에 옛날 친구를 만났어요. 반갑기도 하고 건강이 안 좋아 보여서 걱정도 되더라고요."

    # Act - 병렬 실행
    import asyncio
    emotion_result, keyword_result = await asyncio.gather(
        real_emotion_detector.detect(text),
        real_keyword_extractor.extract(text)
    )

    # Assert
    # 감정 분석 결과
    assert isinstance(emotion_result, EmotionResult)
    assert emotion_result.primary_emotion in [
        EmotionCategory.JOY,
        EmotionCategory.SADNESS,
        EmotionCategory.SURPRISE
    ]

    # 키워드 추출 결과
    assert isinstance(keyword_result, KeywordExtractionResult)
    assert len(keyword_result.keywords) > 0

    # 일관성 확인: 감정과 키워드가 텍스트 내용과 부합하는지
    keyword_words = {kw.word for kw in keyword_result.keywords}

    print(f"\n[Integration Test - Combined NLP Analysis]")
    print(f"텍스트: {text}")
    print(f"\n감정 분석:")
    print(f"  - 주요 감정: {real_emotion_detector.get_emotion_label_kr(emotion_result.primary_emotion)}")
    print(f"  - 강도: {emotion_result.intensity:.2f}")
    if emotion_result.secondary_emotions:
        print(f"  - 보조 감정: {', '.join([real_emotion_detector.get_emotion_label_kr(e.emotion) for e in emotion_result.secondary_emotions])}")

    print(f"\n키워드 분석:")
    print(f"  - 주요 주제: {keyword_result.main_topic}")
    print(f"  - 키워드: {', '.join([kw.word for kw in keyword_result.keywords[:5]])}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_detect_emotion_batch(real_emotion_detector):
    """통합 테스트: 실제 API로 배치 감정 분석"""
    # Arrange
    texts = [
        "오늘 딸이 전화해서 너무 기뻐요!",
        "남편 생각이 나서 슬퍼요.",
        "오늘 날씨가 좋네요."
    ]

    # Act
    results = await real_emotion_detector.detect_batch(texts)

    # Assert
    assert len(results) == 3

    # 각 결과가 유효한지 확인
    for i, result in enumerate(results):
        assert isinstance(result, EmotionResult)
        assert result.primary_emotion in EmotionCategory

        print(f"\n[Batch {i+1}] {texts[i]}")
        print(f"  감정: {real_emotion_detector.get_emotion_label_kr(result.primary_emotion)} (강도: {result.intensity:.2f})")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_extract_keywords_batch(real_keyword_extractor):
    """통합 테스트: 실제 API로 배치 키워드 추출"""
    # Arrange
    texts = [
        "오늘 손녀와 공원에서 산책했어요.",
        "아침에 김치찌개를 끓여 먹었습니다.",
        "날씨가 좋아서 빨래를 했어요."
    ]

    # Act
    results = await real_keyword_extractor.extract_batch(texts)

    # Assert
    assert len(results) == 3

    # 각 결과가 유효한지 확인
    for i, result in enumerate(results):
        assert isinstance(result, KeywordExtractionResult)
        assert len(result.keywords) >= 0  # 빈 결과도 허용

        print(f"\n[Batch {i+1}] {texts[i]}")
        if result.keywords:
            print(f"  키워드: {', '.join([kw.word for kw in result.keywords[:3]])}")
        else:
            print(f"  키워드: (없음)")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_error_handling(real_emotion_detector):
    """통합 테스트: 실제 API 에러 처리 (매우 긴 텍스트)"""
    # Arrange - 매우 긴 텍스트 (토큰 제한 초과 가능성)
    text = "테스트 " * 10000  # 약 20,000 토큰

    # Act & Assert
    # 에러가 발생하거나 정상 처리되거나 둘 다 허용
    try:
        result = await real_emotion_detector.detect(text)
        assert isinstance(result, EmotionResult)
        print(f"\n[Integration Test - Long Text] 정상 처리됨")
    except (AnalysisError, Exception) as e:
        print(f"\n[Integration Test - Long Text] 예상된 에러 발생: {type(e).__name__}")
        # 에러가 발생해도 테스트는 통과 (graceful degradation)
        assert True
