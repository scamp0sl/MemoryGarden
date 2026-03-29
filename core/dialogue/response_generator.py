"""
AI 응답 생성기

OpenAI ChatCompletion API를 사용하여
사용자 기억/감정 상태를 반영한 공감적 응답 생성.

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
from openai import AsyncOpenAI

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings
from core.dialogue.prompt_builder import PromptBuilder
from utils.logger import get_logger
from utils.exceptions import AnalysisError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 300  # 짧은 응답 권장


# ============================================
# 6. ResponseGenerator 클래스
# ============================================


class ResponseGenerator:
    """AI 응답 생성기

    OpenAI ChatCompletion을 사용하여 공감적이고 자연스러운 응답 생성.
    시스템 프롬프트에 사용자 기억/감정 상태를 주입.

    Attributes:
        client: OpenAI AsyncClient
        model: 사용할 모델 (기본: gpt-4o-mini)
        temperature: 생성 온도 (0.0~2.0)
        max_tokens: 최대 토큰 수
        prompt_builder: 프롬프트 빌더

    Example:
        >>> generator = ResponseGenerator()
        >>> response = await generator.generate(
        ...     user_message="오늘 점심은 된장찌개 먹었어요",
        ...     conversation_history=[...],
        ...     user_context={...}
        ... )
        >>> print(response)
        "된장찌개 드셨군요! 🌱 어떤 재료가 들어갔나요?"
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        prompt_builder: Optional[PromptBuilder] = None
    ):
        """
        ResponseGenerator 초기화

        Args:
            model: OpenAI 모델명
            temperature: 생성 온도 (높을수록 창의적, 낮을수록 일관적)
            max_tokens: 최대 토큰 수
            prompt_builder: 프롬프트 빌더 (None이면 생성)
        """
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.prompt_builder = prompt_builder or PromptBuilder()

        logger.info(
            "ResponseGenerator initialized",
            extra={
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )

    async def generate(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        user_context: Optional[Dict[str, Any]] = None,
        next_question: Optional[str] = None,
        user_id: Optional[str] = None,  # B3-4: 쿨다운 체크용 추가
        mcdi_context: Optional[Dict[str, Any]] = None,  # B3-3: 신규 추가
        relationship_stage: Optional[int] = None,  # B1-3: 신규 추가
        emotion_vector: Optional[Dict[str, float]] = None  # B2-6: 신규 추가
    ) -> str:
        """
        AI 응답 생성

        Args:
            user_message: 사용자 메시지
            conversation_history: 대화 히스토리 (최근 N턴)
                [
                    {"role": "user", "content": "..."},
                    {"role": "assistant", "content": "..."}
                ]
            user_context: 사용자 컨텍스트
                {
                    "user_name": "홍길동",
                    "recent_emotion": "기쁨",
                    "biographical_facts": {...},
                    "garden_name": "행복한 정원"
                }
            next_question: 다음 질문 (포함 시 응답 끝에 추가)
            mcdi_context: MCDI 분석 컨텍스트 (B3-3 어댑티브 대화용)
                {
                    "latest_risk_level": "GREEN",
                    "latest_mcdi_score": 78.5,
                    "score_trend": "stable",
                    "latest_scores": {"LR": 80.0, ...},
                    "has_data": True
                }
            relationship_stage: 관계 Stage 0~4 (B1-3 관계 모델용)

        Returns:
            생성된 응답 메시지

        Raises:
            AnalysisError: 응답 생성 실패 시

        Example:
            >>> generator = ResponseGenerator()
            >>> response = await generator.generate(
            ...     user_message="된장찌개 먹었어요",
            ...     conversation_history=[],
            ...     user_context={"user_name": "홍길동"},
            ...     next_question="어떤 반찬과 함께 드셨어요?"
            ... )
        """
        try:
            logger.debug(
                "Generating response",
                extra={
                    "user_message_length": len(user_message),
                    "history_length": len(conversation_history),
                    "has_mcdi_context": mcdi_context is not None,
                    "relationship_stage": relationship_stage
                }
            )

            # 시스템 프롬프트 구성 (B3-3: mcdi_context, B1-3: relationship_stage, B2-6: emotion_vector 추가)
            system_prompt = await self._build_system_prompt(
                user_id=user_id,  # B3-4: 쿨다운용 user_id 전달
                user_context=user_context or {},
                mcdi_context=mcdi_context,
                relationship_stage=relationship_stage,
                emotion_vector=emotion_vector
            )

            # 메시지 리스트 구성
            messages = self._build_messages(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message=user_message
            )

            # OpenAI API 호출
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=0.9,
                frequency_penalty=0.5,  # 반복 줄이기
                presence_penalty=0.3    # 다양성 증가
            )

            # 응답 추출
            generated_text = response.choices[0].message.content.strip()

            # 다음 질문 추가 (선택)
            if next_question:
                generated_text = f"{generated_text}\n\n{next_question}"

            logger.info(
                "Response generated successfully",
                extra={
                    "response_length": len(generated_text),
                    "tokens_used": response.usage.total_tokens if response.usage else None
                }
            )

            return generated_text

        except Exception as e:
            logger.error(f"Response generation failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to generate response: {e}") from e

    async def generate_empathetic_response(
        self,
        user_message: str,
        detected_emotion: str,
        emotion_intensity: float,
        conversation_history: List[Dict[str, str]],
        user_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,  # B3-4: 쿨다운 체크용 추가
        mcdi_context: Optional[Dict[str, Any]] = None,  # B3-3: 신규 추가
        relationship_stage: Optional[int] = None,  # B1-3: 신규 추가
        emotion_vector: Optional[Dict[str, float]] = None  # B2-6: 신규 추가
    ) -> str:
        """
        공감적 응답 생성

        감정 상태를 명시적으로 반영하여 응답 생성.

        Args:
            user_message: 사용자 메시지
            detected_emotion: 감지된 감정 (joy/sadness/anger/fear/surprise/neutral)
            emotion_intensity: 감정 강도 (0.0~1.0)
            conversation_history: 대화 히스토리
            user_context: 사용자 컨텍스트
            mcdi_context: MCDI 분석 컨텍스트 (B3-3 어댑티브 대화용)
            relationship_stage: 관계 Stage 0~4 (B1-3 관계 모델용)
            emotion_vector: 감정 벡터 (B2-6 감정 상태 추적용)

        Returns:
            공감적 응답 메시지

        Example:
            >>> generator = ResponseGenerator()
            >>> response = await generator.generate_empathetic_response(
            ...     user_message="딸이 전화해서 기분 좋아요",
            ...     detected_emotion="joy",
            ...     emotion_intensity=0.85,
            ...     conversation_history=[],
            ...     user_context={"user_name": "홍길동"}
            ... )
        """
        # 감정 정보를 컨텍스트에 추가
        enriched_context = (user_context or {}).copy()
        enriched_context["recent_emotion"] = self._translate_emotion(detected_emotion)
        enriched_context["emotion_intensity"] = emotion_intensity

        # 시스템 프롬프트에 감정 대응 가이드 추가 (B3-3: mcdi_context, B1-3: relationship_stage, B2-6: emotion_vector 추가)
        system_prompt = await self._build_system_prompt_with_emotion(
            user_id=user_id,  # B3-4: 쿨다운용 user_id 전달
            user_context=enriched_context,
            emotion=detected_emotion,
            intensity=emotion_intensity,
            mcdi_context=mcdi_context,
            relationship_stage=relationship_stage,
            emotion_vector=emotion_vector  # B2-6
        )

        # 메시지 구성
        messages = self._build_messages(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user_message=user_message
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,  # 감정 대응 시 약간 더 창의적으로
                max_tokens=self.max_tokens
            )

            generated_text = response.choices[0].message.content.strip()

            logger.info(
                "Empathetic response generated",
                extra={
                    "emotion": detected_emotion,
                    "intensity": emotion_intensity,
                    "response_length": len(generated_text),
                    "has_mcdi_context": mcdi_context is not None
                }
            )

            return generated_text

        except Exception as e:
            logger.error(f"Empathetic response generation failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to generate empathetic response: {e}") from e

    # ============================================
    # Private Helper Methods
    # ============================================

    async def _build_system_prompt(
        self,
        user_id: Optional[str] = None,  # B3-4: 쿨다운 체크용 추가
        user_context: Dict[str, Any] = None,
        mcdi_context: Optional[Dict[str, Any]] = None,  # B3-3: 신규 추가
        relationship_stage: Optional[int] = None,  # B1-3: 신규 추가
        emotion_vector: Optional[Dict[str, float]] = None  # B2-6: 신규 추가
    ) -> str:
        """시스템 프롬프트 구성 (B3-3: mcdi_context, B1-3: relationship_stage, B2-6: emotion_vector 지원)"""
        return await self.prompt_builder.build_system_prompt(
            user_id=user_id,  # B3-4: 쿨다운용 user_id 전달
            user_name=user_context.get("user_name") if user_context else None,
            recent_emotion=user_context.get("recent_emotion") if user_context else None,
            biographical_facts=user_context.get("biographical_facts") if user_context else None,
            garden_name=user_context.get("garden_name") if user_context else None,
            mcdi_context=mcdi_context,  # B3-3: MCDI 어댑티브 블록
            relationship_stage=relationship_stage,  # B1-3: 관계 Stage 블록
            emotion_vector=emotion_vector,  # B2-6: 감정 벡터 설명
            episodic_memories=user_context.get("episodic_memories") if user_context else None,  # 에피소드 기억
            recent_mentions=user_context.get("recent_mentions") if user_context else None,  # 대화 맥락 연속성
            suppress_questions=user_context.get("suppress_questions", False) if user_context else False  # 피로도 방지
        )

    async def _build_system_prompt_with_emotion(
        self,
        user_id: Optional[str] = None,  # B3-4: 쿨다운 체크용 추가
        user_context: Dict[str, Any] = None,
        emotion: str = None,
        intensity: float = None,
        mcdi_context: Optional[Dict[str, Any]] = None,  # B3-3: 신규 추가
        relationship_stage: Optional[int] = None,  # B1-3: 신규 추가
        emotion_vector: Optional[Dict[str, float]] = None  # B2-6: 신규 추가
    ) -> str:
        """감정 대응 가이드가 포함된 시스템 프롬프트 구성 (B3-3: mcdi_context, B1-3: relationship_stage, B2-6: emotion_vector 지원)"""
        base_prompt = await self._build_system_prompt(user_id, user_context, mcdi_context=mcdi_context, relationship_stage=relationship_stage, emotion_vector=emotion_vector)

        # 감정별 대응 가이드
        emotion_guides = {
            "joy": "사용자가 기쁜 상태입니다. 함께 기뻐하며 긍정적으로 반응하세요.",
            "sadness": "사용자가 슬픈 상태입니다. 공감하되 과도한 동정은 피하세요. 경청하는 태도를 보이세요.",
            "anger": "사용자가 화가 난 상태입니다. 감정을 인정하고 차분하게 대응하세요.",
            "fear": "사용자가 불안한 상태입니다. 안심시키되 걱정을 무시하지 마세요.",
            "surprise": "사용자가 놀란 상태입니다. 상황을 함께 확인하고 긍정적으로 전환하세요.",
            "neutral": "사용자가 중립적인 상태입니다. 자연스럽게 대화를 이어가세요."
        }

        guide = emotion_guides.get(emotion, emotion_guides["neutral"])
        intensity_level = "강하게" if intensity > 0.7 else "보통" if intensity > 0.3 else "약하게"

        emotion_context = f"\n\n## 현재 감정 상태\n{guide}\n강도: {intensity_level} ({intensity:.2f})"

        return base_prompt + emotion_context

    def _build_messages(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        user_message: str
    ) -> List[Dict[str, str]]:
        """ChatCompletion용 메시지 리스트 구성"""
        messages = [{"role": "system", "content": system_prompt}]

        # 대화 히스토리 추가
        messages.extend(conversation_history)

        # 현재 사용자 메시지 추가
        messages.append({"role": "user", "content": user_message})

        logger.debug(
            "Messages built",
            extra={
                "total_messages": len(messages),
                "history_turns": len(conversation_history)
            }
        )

        return messages

    def _translate_emotion(self, emotion_en: str) -> str:
        """영어 감정 레이블을 한국어로 변환"""
        emotion_map = {
            "joy": "기쁨",
            "sadness": "슬픔",
            "anger": "분노",
            "fear": "두려움",
            "surprise": "놀람",
            "neutral": "중립"
        }
        return emotion_map.get(emotion_en, "알 수 없음")


# ============================================
# 8. Export
# ============================================
__all__ = [
    "ResponseGenerator",
]

logger.info("Response generator module loaded")
