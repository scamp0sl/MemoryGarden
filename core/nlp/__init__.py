"""
NLP (자연어 처리) 모듈

텍스트 분석, 감정 감지, 키워드 추출 등.

Author: Memory Garden Team
Created: 2025-01-15
"""

# ============================================
# Emotion Detection
# ============================================
from core.nlp.emotion_detector import (
    EmotionDetector,
    EmotionResult,
    EmotionCategory,
    SecondaryEmotion,
)

# ============================================
# Keyword Extraction
# ============================================
from core.nlp.keyword_extractor import (
    KeywordExtractor,
    KeywordExtractionResult,
    Keyword,
    KeywordCategory,
)


# ============================================
# Export All
# ============================================
__all__ = [
    # Emotion Detection
    "EmotionDetector",
    "EmotionResult",
    "EmotionCategory",
    "SecondaryEmotion",

    # Keyword Extraction
    "KeywordExtractor",
    "KeywordExtractionResult",
    "Keyword",
    "KeywordCategory",
]
