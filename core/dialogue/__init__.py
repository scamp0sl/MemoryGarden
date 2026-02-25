"""
Dialogue (대화) 모듈

대화 흐름 관리, AI 응답 생성, 프롬프트 구성.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# Dialogue Manager
# ============================================
from core.dialogue.dialogue_manager import DialogueManager

# ============================================
# Response Generator
# ============================================
from core.dialogue.response_generator import ResponseGenerator

# ============================================
# Prompt Builder
# ============================================
from core.dialogue.prompt_builder import (
    PromptBuilder,
    SYSTEM_PROMPT,
)


# ============================================
# Export All
# ============================================
__all__ = [
    # Dialogue Manager
    "DialogueManager",

    # Response Generator
    "ResponseGenerator",

    # Prompt Builder
    "PromptBuilder",
    "SYSTEM_PROMPT",
]
