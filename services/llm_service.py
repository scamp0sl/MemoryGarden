"""
LLM 서비스

Anthropic Claude, OpenAI GPT, DeepSeek을 동일한 인터페이스로 추상화.
LLM_PROVIDER 환경변수로 provider를 선택하고, 각 모델명은 .env에서 제어.

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2026-05-06 (multi-provider 지원)
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import asyncio
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

# ============================================
# 2. Third-Party Imports
# ============================================
from anthropic import AsyncAnthropic
from anthropic import APIError as AnthropicError, RateLimitError as AnthropicRateLimitError
from openai import AsyncOpenAI
from openai import APIError as OpenAIError, RateLimitError as OpenAIRateLimitError

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

# Claude 단축 별칭 → 실제 모델 ID 매핑
# .env의 CLAUDE_MODEL에 단축명(sonnet) 또는 전체 ID 모두 사용 가능
CLAUDE_MODELS: Dict[str, str] = {
    "sonnet":           "claude-sonnet-4-6",
    "sonnet-4-6":       "claude-sonnet-4-6",
    "opus":             "claude-opus-4-7",
    "opus-4-7":         "claude-opus-4-7",
    "haiku":            "claude-haiku-4-5-20251001",
    "haiku-4-5":        "claude-haiku-4-5-20251001",
    # 구버전 호환
    "claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307":    "claude-3-haiku-20240307",
}

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000


# ============================================
# 6. 공통 인터페이스
# ============================================

class BaseLLMService(ABC):
    """LLM 서비스 공통 인터페이스"""

    @abstractmethod
    async def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str: ...

    @abstractmethod
    async def call_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]: ...

    @abstractmethod
    async def batch_call(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> List[str]: ...

    # ── JSON 보조 메서드 (하위 클래스 공유) ──────────────────────────
    @staticmethod
    def _strip_json_fence(text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    @staticmethod
    def _add_json_fallback_instruction(prompt: str) -> str:
        return (
            f"{prompt}\n\n"
            "중요: 반드시 유효한 JSON 형식으로만 응답하세요. 다른 텍스트를 추가하지 마세요.\n"
            '예시: {"key": "value"}'
        )

    @staticmethod
    def _add_json_system_instruction(system: Optional[str]) -> str:
        base = system or ""
        return (
            f"{base}\n\n"
            "## JSON 출력 강제 규칙\n"
            "1. 응답은 반드시 유효한 JSON 객체로만 작성하세요\n"
            "2. ```json ``` 마크다운 없이 JSON만 출력하세요\n"
            "3. JSON 앞뒤에 아무런 텍스트나 설명을 붙이지 마세요\n"
            "4. 빈 JSON {} 을 반환하더라도 유효한 형식이어야 합니다"
        )


# ============================================
# 7. Anthropic Claude 구현
# ============================================

class AnthropicLLMService(BaseLLMService):
    """
    Anthropic Claude API 서비스.
    사용 모델: .env CLAUDE_MODEL (단축명 또는 전체 ID)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        api_key = settings.CLAUDE_API_KEY or settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("CLAUDE_API_KEY 또는 ANTHROPIC_API_KEY가 설정되지 않았습니다")

        self.client = AsyncAnthropic(api_key=api_key)

        raw_model = model or settings.CLAUDE_MODEL
        self.model = CLAUDE_MODELS.get(raw_model, raw_model)
        self.temperature = temperature
        self.max_tokens = max_tokens

        logger.info(
            "AnthropicLLMService initialized",
            extra={"model": self.model, "temperature": temperature, "max_tokens": max_tokens},
        )

    async def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        try:
            params: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature if temperature is not None else self.temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            sys = system_prompt or ""
            if json_mode:
                sys += "\n\n반드시 JSON 형식으로만 응답하세요."
            if sys.strip():
                params["system"] = sys.strip()

            logger.debug(f"Claude API 호출: model={self.model}")
            response = await self.client.messages.create(**params)
            content = response.content[0].text

            logger.debug(
                "Claude API 응답 수신",
                extra={
                    "model": self.model,
                    "tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
            )
            return content

        except AnthropicRateLimitError:
            logger.error("Claude rate limit 초과", exc_info=True)
            raise
        except AnthropicError:
            logger.error("Claude API 오류", exc_info=True)
            raise
        except Exception:
            logger.error("LLM 호출 중 예외", exc_info=True)
            raise

    async def call_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        cur_prompt, cur_system = prompt, system_prompt
        for attempt in range(max_retries + 1):
            try:
                raw = await self.call(cur_prompt, cur_system, temperature, max_tokens, json_mode=True)
                text = self._strip_json_fence(raw)
                if not text:
                    raise json.JSONDecodeError("빈 응답", "", 0)
                return json.loads(text)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패 {attempt+1}/{max_retries+1}: {e}")
                if attempt < max_retries:
                    cur_prompt = self._add_json_fallback_instruction(cur_prompt)
                    cur_system = self._add_json_system_instruction(cur_system)
                    await asyncio.sleep(0.5)
                else:
                    raise

    async def batch_call(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> List[str]:
        tasks = [self.call(p, system_prompt, temperature, max_tokens) for p in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        responses = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(f"batch_call #{i} 실패: {r}")
                responses.append("")
            else:
                responses.append(r)
        return responses


# ============================================
# 8. OpenAI 호환 서비스 (OpenAI / DeepSeek)
# ============================================

class OpenAICompatibleLLMService(BaseLLMService):
    """
    OpenAI API 호환 서비스.
    OpenAI(gpt-4o 등)와 DeepSeek(OpenAI 호환 엔드포인트) 모두 지원.
    base_url을 바꾸면 다른 OpenAI-compatible provider도 추가 가능.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        min_max_tokens: int = 0,
    ):
        if not api_key:
            raise ValueError("api_key가 설정되지 않았습니다")

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = AsyncOpenAI(**client_kwargs)
        self.model = model or settings.GPT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        # 호출자가 낮은 max_tokens를 넘겨도 이 값 이상으로 강제 (reasoning 모델용)
        self._min_max_tokens = min_max_tokens
        self._base_url = base_url

        logger.info(
            "OpenAICompatibleLLMService initialized",
            extra={
                "model": self.model,
                "base_url": base_url or "default(api.openai.com)",
                "temperature": temperature,
            },
        )

    async def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        try:
            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.temperature,
                "max_tokens": max(max_tokens or self.max_tokens, self._min_max_tokens),
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            logger.debug(f"OpenAI 호환 API 호출: model={self.model}")
            response = await self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""

            logger.debug(
                "OpenAI 호환 API 응답 수신",
                extra={
                    "model": self.model,
                    "tokens": (response.usage.total_tokens if response.usage else 0),
                },
            )
            return content

        except OpenAIRateLimitError:
            logger.error("OpenAI 호환 rate limit 초과", exc_info=True)
            raise
        except OpenAIError:
            logger.error("OpenAI 호환 API 오류", exc_info=True)
            raise
        except Exception:
            logger.error("LLM 호출 중 예외", exc_info=True)
            raise

    async def call_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        cur_prompt, cur_system = prompt, system_prompt
        for attempt in range(max_retries + 1):
            try:
                raw = await self.call(cur_prompt, cur_system, temperature, max_tokens, json_mode=True)
                text = self._strip_json_fence(raw)
                if not text:
                    raise json.JSONDecodeError("빈 응답", "", 0)
                return json.loads(text)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패 {attempt+1}/{max_retries+1}: {e}")
                if attempt < max_retries:
                    cur_prompt = self._add_json_fallback_instruction(cur_prompt)
                    cur_system = self._add_json_system_instruction(cur_system)
                    await asyncio.sleep(0.5)
                else:
                    raise

    async def batch_call(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> List[str]:
        tasks = [self.call(p, system_prompt, temperature, max_tokens) for p in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        responses = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(f"batch_call #{i} 실패: {r}")
                responses.append("")
            else:
                responses.append(r)
        return responses


# ============================================
# 9. Provider 팩토리
# ============================================

def get_llm_service(
    provider: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> BaseLLMService:
    """
    LLM_PROVIDER 환경변수(또는 인자)에 따라 적절한 서비스 반환.

    provider 값:
      "anthropic" → AnthropicLLMService  (CLAUDE_MODEL 사용)
      "openai"    → OpenAICompatibleLLMService  (GPT_MODEL 사용)
      "deepseek"  → OpenAICompatibleLLMService  (DEEPSEEK_MODEL + DEEPSEEK_BASE_URL 사용)

    Example:
        llm = get_llm_service()                          # .env LLM_PROVIDER 따름
        llm = get_llm_service("deepseek")                # DeepSeek 강제 지정
        llm = get_llm_service(temperature=0.3)           # temperature 커스터마이즈
    """
    target = (provider or settings.LLM_PROVIDER).lower()
    kwargs: Dict[str, Any] = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    if target == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")
        return OpenAICompatibleLLMService(
            model=settings.GPT_MODEL,
            api_key=settings.OPENAI_API_KEY,
            **kwargs,
        )

    if target == "deepseek":
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY가 설정되지 않았습니다")
        # reasoning 모델은 thinking 토큰이 max_tokens를 선점하므로
        # call() 레벨에서도 DEEPSEEK_MAX_TOKENS 이하로 내려가지 않도록 min_max_tokens 강제
        return OpenAICompatibleLLMService(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            min_max_tokens=settings.DEEPSEEK_MAX_TOKENS,
            **kwargs,
        )

    # 기본: anthropic
    return AnthropicLLMService(**kwargs)


# ============================================
# 10. 하위 호환 별칭 + 전역 인스턴스
# ============================================

# 기존 코드에서 LLMService()로 직접 생성하는 곳은 Anthropic을 계속 사용
LLMService = AnthropicLLMService

# default_llm_service는 LLM_PROVIDER를 따름
default_llm_service: BaseLLMService = get_llm_service()


# ============================================
# 11. Export
# ============================================
__all__ = [
    "BaseLLMService",
    "AnthropicLLMService",
    "OpenAICompatibleLLMService",
    "LLMService",          # 하위 호환
    "get_llm_service",
    "default_llm_service",
    "CLAUDE_MODELS",
]

logger.info(
    f"LLM service module loaded",
    extra={"provider": settings.LLM_PROVIDER, "model": settings.CLAUDE_MODEL},
)
