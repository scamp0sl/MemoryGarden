"""
LLM 서비스

Anthropic Claude API를 사용한 텍스트 생성 및 분석.

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2026-03-29 (Claude Sonnet로 변경)
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import json
from typing import Optional, Dict, Any, List

# ============================================
# 2. Third-Party Imports
# ============================================
from anthropic import AsyncAnthropic
from anthropic import APIError as AnthropicError, RateLimitError as AnthropicRateLimitError

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
# Claude 모델 매핑 (최신 4.6 시리즈)
CLAUDE_MODELS = {
    # Sonnet 4.6 (기본, 균형형)
    "sonnet": "claude-sonnet-4-20250514",      # Claude Sonnet 4.6
    "sonnet-4-6": "claude-sonnet-4-20250514",   # 별칭
    # Opus 4.6 (최고 성능)
    "opus": "claude-opus-4-20250514",           # Claude Opus 4.6
    "opus-4-6": "claude-opus-4-20250514",       # 별칭
    # Haiku 4.6 (고속 저비용)
    "haiku": "claude-haiku-4-20250514",         # Claude Haiku 4.6
    "haiku-4-6": "claude-haiku-4-20250514",     # 별칭
}

DEFAULT_MODEL = "sonnet-4-6"  # 기본 모델: Sonnet 4.6 (최신)
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000


# ============================================
# 6. LLM 서비스 클래스
# ============================================

class LLMService:
    """
    Anthropic Claude API 래퍼 클래스

    비동기 텍스트 생성 및 JSON 응답 파싱 지원.

    Attributes:
        client: AsyncAnthropic 클라이언트
        model: 사용할 모델 이름
        temperature: 샘플링 온도 (0.0~1.0)
        max_tokens: 최대 토큰 수

    Example:
        >>> llm = LLMService()
        >>> response = await llm.call("안녕하세요!")
        >>> print(response)
        "반가워요!"
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS
    ):
        """
        LLMService 초기화

        Args:
            model: Claude 모델 이름 (sonnet/opus/haiku)
            temperature: 샘플링 온도 (0.0~1.0)
            max_tokens: 최대 생성 토큰 수
        """
        # API 키 확인
        api_key = settings.CLAUDE_API_KEY or settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("CLAUDE_API_KEY or ANTHROPIC_API_KEY must be set in settings")

        self.client = AsyncAnthropic(api_key=api_key)

        # 모델 매핑
        self.model = CLAUDE_MODELS.get(model, model)
        self.model_name = model  # 원본 모델 이름 저장

        self.temperature = temperature
        self.max_tokens = max_tokens

        logger.info(
            f"LLMService initialized with Claude",
            extra={
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
        )

    async def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> str:
        """
        Claude API 호출

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택)
            temperature: 샘플링 온도 (None이면 기본값)
            max_tokens: 최대 토큰 수 (None이면 기본값)
            json_mode: JSON 응답 강제 여부

        Returns:
            str: LLM 응답 텍스트

        Raises:
            AnthropicError: API 호출 실패 시

        Example:
            >>> llm = LLMService()
            >>> response = await llm.call(
            ...     "감정을 분석해줘: 오늘 기분이 좋아요!",
            ...     system_prompt="당신은 감정 분석 전문가입니다.",
            ...     json_mode=True
            ... )
            >>> print(response)
            '{"emotion": "joy", "intensity": 0.8}'
        """
        try:
            # API 호출 파라미터
            params = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            # 시스템 프롬프트
            if system_prompt:
                params["system"] = system_prompt

            # JSON 모드 - 프롬프트에 지시사항 추가
            if json_mode:
                if system_prompt:
                    params["system"] += "\n\n반드시 JSON 형식으로만 응답하세요."
                else:
                    params["system"] = "반드시 JSON 형식으로만 응답하세요."

            # API 호출
            logger.debug(f"Calling Claude API: model={self.model}")
            response = await self.client.messages.create(**params)

            # 응답 추출
            content = response.content[0].text

            logger.debug(
                f"Claude API response received",
                extra={
                    "model": self.model,
                    "tokens": response.usage.input_tokens + response.usage.output_tokens,
                    "content_length": len(content)
                }
            )

            return content

        except AnthropicRateLimitError as e:
            logger.error(f"Claude rate limit exceeded: {e}", exc_info=True)
            raise
        except AnthropicError as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LLM call: {e}", exc_info=True)
            raise

    async def call_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        JSON 응답 요청

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택)
            temperature: 샘플링 온도
            max_tokens: 최대 토큰 수

        Returns:
            Dict: 파싱된 JSON 객체

        Raises:
            json.JSONDecodeError: JSON 파싱 실패 시
            AnthropicError: API 호출 실패 시

        Example:
            >>> llm = LLMService()
            >>> result = await llm.call_json(
            ...     "감정을 JSON으로 반환해줘: 오늘 기분이 좋아요!"
            ... )
            >>> print(result["emotion"])
            "joy"
        """
        try:
            # JSON 모드로 호출
            response = await self.call(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=True
            )

            # JSON 파싱 (```json 제거)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            result = json.loads(response)

            logger.debug(f"JSON response parsed successfully")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}", exc_info=True)
            logger.error(f"Raw response: {response}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in call_json: {e}", exc_info=True)
            raise

    async def batch_call(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> List[str]:
        """
        여러 프롬프트를 동시에 처리

        Args:
            prompts: 프롬프트 리스트
            system_prompt: 시스템 프롬프트
            temperature: 샘플링 온도
            max_tokens: 최대 토큰 수

        Returns:
            List[str]: 응답 리스트

        Example:
            >>> llm = LLMService()
            >>> prompts = ["안녕", "감사합니다", "좋은 하루"]
            >>> responses = await llm.batch_call(prompts)
            >>> print(len(responses))
            3
        """
        import asyncio

        tasks = [
            self.call(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            for prompt in prompts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 에러 처리
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch call failed for prompt {i}: {result}")
                responses.append("")
            else:
                responses.append(result)

        return responses


# ============================================
# 7. 전역 인스턴스
# ============================================

# 기본 LLM 서비스 인스턴스 (Sonnet)
default_llm_service = LLMService()


# ============================================
# 8. Export
# ============================================
__all__ = [
    "LLMService",
    "default_llm_service",
    "CLAUDE_MODELS",
]


logger.info("LLM service module loaded (Claude Sonnet)")
