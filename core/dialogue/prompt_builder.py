"""
프롬프트 동적 구성

config/prompts.py의 템플릿을 활용하여
사용자 컨텍스트(기억, 감정 이력)를 삽입한 동적 프롬프트 생성.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, Any, List, Optional
from datetime import datetime

# ============================================
# 2. Third-Party Imports
# ============================================

# ============================================
# 3. Local Imports
# ============================================
from config.prompts import (
    QUESTION_GENERATION_PROMPTS,
    ANALYSIS_PROMPTS,
    FACT_EXTRACTION_PROMPT,
)
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================

# 정원사 페르소나 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 '기억의 정원'의 정원사입니다.

## 역할
- 사용자의 친근한 동행자로서 매일 2-3회 대화를 나눕니다
- "평가"나 "검사"가 아닌, 정원을 함께 가꾸는 자연스러운 대화를 추구합니다
- 사용자의 일상, 추억, 감정을 존중하며 경청합니다

## 대화 원칙
1. 존댓말 사용 (70대 이상 대상)
2. 이모지 절제적 사용 (1-2개/메시지)
3. 짧은 문장 (2문장 이내)
4. 열린 질문 선호 ("예/아니오" 질문 지양)
5. 긍정적 피드백 ("잘 기억하시네요!", "멋진 추억이에요")

## 금기사항
- "치매", "검사", "평가" 같은 의학적 용어 사용 금지
- 사용자를 시험하는 듯한 태도 금지
- 틀린 답에 대한 지적 금지
- 과도한 걱정/동정 금지

## 예시 대화
좋은 예:
- "오늘 점심 뭐 드셨어요? 사진 찍으셨으면 정원에 올려주세요! 🌱"
- "어제 말씀하신 딸 이름이 수진이었죠? 수진 씨는 어떤 일을 하시나요?"

나쁜 예:
- "기억력 테스트입니다. 아침 식사 메뉴를 정확히 말씀해주세요."
- "틀렸습니다. 다시 생각해보세요."
"""

# ============================================
# 6. PromptBuilder 클래스
# ============================================


class PromptBuilder:
    """프롬프트 동적 구성

    사용자 컨텍스트를 활용하여 시스템 프롬프트와 질문 프롬프트를 생성.

    Example:
        >>> builder = PromptBuilder()
        >>> system_prompt = builder.build_system_prompt(
        ...     user_name="홍길동",
        ...     recent_emotion="기쁨",
        ...     biographical_facts={"daughter_name": "수진"}
        ... )
        >>> print(system_prompt)
    """

    def __init__(self):
        """PromptBuilder 초기화"""
        logger.info("PromptBuilder initialized")

    def build_system_prompt(
        self,
        user_name: Optional[str] = None,
        recent_emotion: Optional[str] = None,
        biographical_facts: Optional[Dict[str, Any]] = None,
        garden_name: Optional[str] = None
    ) -> str:
        """
        시스템 프롬프트 생성

        기본 SYSTEM_PROMPT에 사용자 컨텍스트를 추가.

        Args:
            user_name: 사용자 이름
            recent_emotion: 최근 감정 상태 (예: "기쁨", "슬픔")
            biographical_facts: 전기적 사실들 (예: {"daughter_name": "수진"})
            garden_name: 정원 이름

        Returns:
            시스템 프롬프트 문자열

        Example:
            >>> builder = PromptBuilder()
            >>> prompt = builder.build_system_prompt(
            ...     user_name="홍길동",
            ...     recent_emotion="기쁨",
            ...     biographical_facts={"daughter_name": "수진", "hometown": "부산"}
            ... )
        """
        context_parts = [SYSTEM_PROMPT]

        # 사용자 정보 추가
        if user_name or garden_name or biographical_facts:
            context_parts.append("\n## 사용자 정보")

            if user_name:
                context_parts.append(f"- 이름: {user_name}님")

            if garden_name:
                context_parts.append(f"- 정원 이름: {garden_name}")

            if biographical_facts:
                for key, value in biographical_facts.items():
                    # 읽기 쉬운 형태로 변환
                    readable_key = self._format_fact_key(key)
                    context_parts.append(f"- {readable_key}: {value}")

        # 최근 감정 상태 추가
        if recent_emotion:
            context_parts.append(f"\n## 최근 감정 상태\n{user_name}님은 최근 '{recent_emotion}' 감정을 보이고 있습니다.")
            context_parts.append("대화 시 이를 고려하여 공감적으로 반응하세요.")

        prompt = "\n".join(context_parts)

        logger.debug(
            "System prompt built",
            extra={
                "user_name": user_name,
                "emotion": recent_emotion,
                "facts_count": len(biographical_facts) if biographical_facts else 0
            }
        )

        return prompt

    def build_question_prompt(
        self,
        category: str,
        user_context: Dict[str, Any]
    ) -> str:
        """
        질문 생성 프롬프트 구성

        config/prompts.py의 QUESTION_GENERATION_PROMPTS 템플릿에
        사용자 컨텍스트를 삽입.

        Args:
            category: 질문 카테고리 (reminiscence/daily_episodic/naming/temporal)
            user_context: 사용자 컨텍스트
                {
                    "user_profile": {...},
                    "previous_conversations": [...],
                    "current_season": "봄",
                    "today": "2025-02-10",
                    "difficulty": "medium"
                }

        Returns:
            포맷팅된 질문 생성 프롬프트

        Raises:
            ValueError: 지원하지 않는 카테고리

        Example:
            >>> builder = PromptBuilder()
            >>> prompt = builder.build_question_prompt(
            ...     category="reminiscence",
            ...     user_context={
            ...         "user_profile": {"name": "홍길동", "age": 75},
            ...         "current_season": "봄"
            ...     }
            ... )
        """
        if category not in QUESTION_GENERATION_PROMPTS:
            raise ValueError(
                f"Unsupported category: {category}. "
                f"Supported: {list(QUESTION_GENERATION_PROMPTS.keys())}"
            )

        template = QUESTION_GENERATION_PROMPTS[category]

        # 템플릿에 필요한 변수 추출
        try:
            prompt = template.format(**user_context)
        except KeyError as e:
            logger.warning(
                f"Missing key in user_context: {e}",
                extra={"category": category, "available_keys": list(user_context.keys())}
            )
            # 누락된 키는 빈 문자열로 대체
            safe_context = self._fill_missing_keys(template, user_context)
            prompt = template.format(**safe_context)

        logger.debug(
            "Question prompt built",
            extra={"category": category, "context_keys": list(user_context.keys())}
        )

        return prompt

    def build_analysis_prompt(
        self,
        analysis_type: str,
        input_data: Dict[str, Any]
    ) -> str:
        """
        분석 프롬프트 구성

        Args:
            analysis_type: 분석 유형 (semantic_drift/narrative_coherence)
            input_data: 분석 입력 데이터

        Returns:
            포맷팅된 분석 프롬프트

        Example:
            >>> builder = PromptBuilder()
            >>> prompt = builder.build_analysis_prompt(
            ...     analysis_type="semantic_drift",
            ...     input_data={
            ...         "question": "오늘 점심 뭐 드셨어요?",
            ...         "user_response": "봄이면 엄마가 쑥을 뜯으러..."
            ...     }
            ... )
        """
        if analysis_type not in ANALYSIS_PROMPTS:
            raise ValueError(
                f"Unsupported analysis type: {analysis_type}. "
                f"Supported: {list(ANALYSIS_PROMPTS.keys())}"
            )

        template = ANALYSIS_PROMPTS[analysis_type]

        try:
            prompt = template.format(**input_data)
        except KeyError as e:
            logger.warning(f"Missing key in input_data: {e}")
            safe_data = self._fill_missing_keys(template, input_data)
            prompt = template.format(**safe_data)

        return prompt

    def build_fact_extraction_prompt(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        사실 추출 프롬프트 구성

        Args:
            conversation_history: 대화 히스토리
                [
                    {"role": "user", "content": "..."},
                    {"role": "assistant", "content": "..."}
                ]

        Returns:
            포맷팅된 사실 추출 프롬프트

        Example:
            >>> builder = PromptBuilder()
            >>> prompt = builder.build_fact_extraction_prompt(
            ...     conversation_history=[
            ...         {"role": "user", "content": "딸 이름은 수진이에요"},
            ...         {"role": "assistant", "content": "수진 씨 멋진 이름이네요!"}
            ...     ]
            ... )
        """
        # 대화 히스토리를 텍스트로 변환
        formatted_history = self._format_conversation_history(conversation_history)

        prompt = FACT_EXTRACTION_PROMPT.format(
            conversation_history=formatted_history
        )

        return prompt

    # ============================================
    # Private Helper Methods
    # ============================================

    def _format_fact_key(self, key: str) -> str:
        """사실 키를 읽기 쉬운 형태로 변환"""
        key_mapping = {
            "daughter_name": "딸 이름",
            "son_name": "아들 이름",
            "hometown": "고향",
            "occupation": "직업",
            "favorite_food": "좋아하는 음식",
            "hobby": "취미",
        }
        return key_mapping.get(key, key)

    def _fill_missing_keys(
        self,
        template: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """템플릿에 필요한 누락된 키를 빈 문자열로 채움"""
        import re

        # 템플릿에서 {key} 형태 추출
        required_keys = re.findall(r'\{(\w+)\}', template)

        safe_context = context.copy()
        for key in required_keys:
            if key not in safe_context:
                safe_context[key] = ""

        return safe_context

    def _format_conversation_history(
        self,
        history: List[Dict[str, str]]
    ) -> str:
        """대화 히스토리를 텍스트로 변환"""
        formatted_lines = []

        for turn in history:
            role = "사용자" if turn["role"] == "user" else "정원사"
            content = turn["content"]
            formatted_lines.append(f"{role}: {content}")

        return "\n".join(formatted_lines)

    # ============================================
    # Workflow Integration Methods
    # ============================================

    async def build_question(
        self,
        category: str,
        difficulty: str,
        question_type: str
    ) -> str:
        """
        카테고리, 난이도, 질문 유형에 맞는 질문 생성

        템플릿 기반으로 즉시 질문을 생성합니다.

        Args:
            category: 질문 카테고리
                - lexical_richness: 어휘 풍부도
                - semantic_focus: 의미적 집중도
                - narrative: 서사 구성
                - temporal_orientation: 시간 지남력
                - episodic_recall: 일화 기억
                - response_speed: 반응 속도
                - general: 일반 대화
            difficulty: 난이도 (easy/medium/hard)
            question_type: 질문 유형
                - free_recall: 자유 회상
                - cued_recall: 단서 회상
                - time_orientation: 시간 지남력
                - narrative: 이야기 구성
                - descriptive: 묘사
                - focused: 집중
                - open_ended: 열린 질문

        Returns:
            생성된 질문 문자열

        Example:
            >>> builder = PromptBuilder()
            >>> question = await builder.build_question(
            ...     category="episodic_recall",
            ...     difficulty="medium",
            ...     question_type="free_recall"
            ... )
            >>> print(question)
            "어릴 적 가장 기억에 남는 명절은 언제인가요? 🎊"
        """
        logger.debug(
            f"Building question",
            extra={
                "category": category,
                "difficulty": difficulty,
                "question_type": question_type
            }
        )

        # 질문 템플릿 매트릭스
        question_templates = {
            "episodic_recall": {
                "easy": [
                    "오늘 아침 식사로 뭐 드셨어요? 🍚",
                    "어제는 무엇을 하셨나요? 😊",
                    "오늘 날씨가 어떤가요? ☀️",
                ],
                "medium": [
                    "지난 주말에 무엇을 하셨나요? 기억나시나요? 🌸",
                    "어릴 적 가장 기억에 남는 명절은 언제인가요? 🎊",
                    "결혼식 날 기억나시나요? 어떤 옷을 입으셨는지 기억나세요? 💒",
                ],
                "hard": [
                    "10년 전 오늘은 무엇을 하셨을까요? 혹시 기억나시나요?",
                    "첫 직장 첫 출근날을 떠올려보세요. 어떤 기분이셨나요? 💼",
                    "20대 때 가장 행복했던 순간을 이야기해주세요.",
                ],
            },
            "temporal_orientation": {
                "easy": [
                    "오늘이 무슨 요일인지 아시나요? 📅",
                    "지금 몇 시쯤 되셨나요? ⏰",
                    "지금은 어느 계절인가요? 🌱",
                ],
                "medium": [
                    "오늘 날짜가 며칠인지 기억나세요? 📆",
                    "올해가 몇 년도인지 아시나요? 🗓️",
                    "지난주 월요일에는 뭐 하셨는지 기억나세요?",
                ],
                "hard": [
                    "지금부터 1시간 전에는 무엇을 하고 계셨나요?",
                    "내일이 무슨 요일인지 아시나요?",
                    "다음 주 월요일 날짜가 며칠인지 계산해보실 수 있나요?",
                ],
            },
            "narrative": {
                "easy": [
                    "오늘 하루를 간단히 말씀해주세요 😊",
                    "오늘 아침부터 지금까지 무엇을 하셨나요?",
                ],
                "medium": [
                    "지난 명절에 있었던 일을 이야기해주세요 🎊",
                    "어릴 적 가장 재미있었던 이야기를 들려주세요 ✨",
                    "최근에 가족과 있었던 일을 이야기해주시겠어요? 👨‍👩‍👧",
                ],
                "hard": [
                    "결혼식 날부터 신혼여행까지의 이야기를 순서대로 들려주세요 💑",
                    "첫 직장에 입사하게 된 과정을 처음부터 끝까지 이야기해주세요",
                    "자녀분들이 태어났을 때부터 학교 입학까지의 이야기를 들려주세요",
                ],
            },
            "lexical_richness": {
                "easy": [
                    "오늘 기분을 표현해보세요! 어떤 느낌이세요? 😊",
                    "지금 창밖 풍경을 말로 그려주세요 🌳",
                ],
                "medium": [
                    "봄이면 떠오르는 것들을 최대한 많이 말씀해주세요 🌸",
                    "좋아하시는 음식의 맛과 향을 자세히 설명해주세요 🍲",
                    "어릴 적 살던 동네를 묘사해주세요",
                ],
                "hard": [
                    "인생에서 가장 감동적이었던 순간을 감정까지 세세히 표현해주세요 ✨",
                    "가장 존경하는 분의 성격과 외모를 구체적으로 묘사해주세요",
                    "행복의 의미를 당신만의 언어로 정의해보세요",
                ],
            },
            "semantic_focus": {
                "easy": [
                    "오늘 점심 메뉴에 대해 이야기해주세요 🍚",
                    "지금 날씨가 어떤가요? ☀️",
                ],
                "medium": [
                    "요즘 건강 관리는 어떻게 하고 계세요? 💪",
                    "최근에 가족과 통화하셨나요? 어떤 이야기 나누셨어요? 📞",
                ],
                "hard": [
                    "요즘 정치 뉴스에 대해 어떻게 생각하시나요?",
                    "최근 경제 상황에 대한 의견을 말씀해주세요",
                ],
            },
            "general": {
                "easy": [
                    "오늘 기분이 어떠세요? 😊",
                    "요즘 뭐 하면서 시간을 보내세요? 🌱",
                ],
                "medium": [
                    "요즘 제일 즐거운 일이 뭔가요? ✨",
                    "최근에 보신 TV 프로그램 중에 재미있었던 게 있나요? 📺",
                ],
                "hard": [
                    "인생에서 가장 중요하게 생각하는 가치는 무엇인가요? 💭",
                    "젊은 세대에게 해주고 싶은 조언이 있으신가요?",
                ],
            },
        }

        # 카테고리 검증
        if category not in question_templates:
            logger.warning(f"Unknown category '{category}', using 'general'")
            category = "general"

        # 난이도 검증
        if difficulty not in question_templates[category]:
            logger.warning(f"Unknown difficulty '{difficulty}', using 'medium'")
            difficulty = "medium"

        # 질문 선택 (랜덤)
        import random
        questions = question_templates[category][difficulty]
        selected_question = random.choice(questions)

        logger.info(
            "Question built",
            extra={
                "category": category,
                "difficulty": difficulty,
                "question_length": len(selected_question)
            }
        )

        return selected_question


# ============================================
# 8. Export
# ============================================
__all__ = [
    "PromptBuilder",
    "SYSTEM_PROMPT",
]

logger.info("Prompt builder module loaded")
