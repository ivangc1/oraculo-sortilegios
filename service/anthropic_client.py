"""AsyncAnthropic singleton. Cache system fijo, version pinned, parseo seguro.

Sonnet 4.6: adaptive thinking con effort configurable por modo.
CRITICO: NO anadir retries manuales. El SDK ya reintenta 2x (429, 500).
"""

import anthropic
from loguru import logger

from bot.config import Settings
from service.models import InterpretationRequest, InterpretationResponse
from service.prompts.master import MASTER_SYSTEM_PROMPT


def calculate_real_cost(usage) -> float:
    """Coste real basado en desglose de tokens cache hit/miss/write."""
    fresh_input = usage.input_tokens - (getattr(usage, "cache_read_input_tokens", 0) or 0)
    cached_input = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0

    cost = (
        (fresh_input / 1_000_000) * 3.00
        + (cached_input / 1_000_000) * 0.30
        + (cache_write / 1_000_000) * 3.75
        + (usage.output_tokens / 1_000_000) * 15.00
    )
    return round(cost, 6)


class AnthropicService:
    """Singleton. Se crea una vez, se reutiliza en todas las llamadas."""

    def __init__(self, settings: Settings):
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            default_headers={"anthropic-version": settings.ANTHROPIC_API_VERSION},
            max_retries=2,
            timeout=30.0,
        )
        self._model = "claude-sonnet-4-6"

    async def interpret(
        self,
        request: InterpretationRequest,
        user_message: str,
    ) -> InterpretationResponse:
        """Envia peticion a la API. System prompt cacheado.

        TODO: reactivar adaptive thinking cuando la API sea estable.
        Por ahora, llamada directa sin thinking para evitar empty responses
        y errores 400 con effort/output_config.
        """
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=request.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": MASTER_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APITimeoutError:
            logger.warning("Anthropic API timeout")
            return InterpretationResponse(error="timeout")
        except anthropic.RateLimitError:
            logger.warning("Anthropic rate limit")
            return InterpretationResponse(error="rate_limit")
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e.status_code}")
            return InterpretationResponse(error="api_error")

        try:
            text = response.content[0].text
            stop = response.stop_reason
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
        except (IndexError, AttributeError) as e:
            logger.error(f"Unexpected response format: {e}")
            return InterpretationResponse(error="api_format_error")

        if not text or text.strip() == "":
            logger.error(f"Empty response: {request.mode}/{request.variant}")
            return InterpretationResponse(error="empty_response")

        return InterpretationResponse(
            text=text,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_usd=calculate_real_cost(response.usage),
            cached=(getattr(response.usage, "cache_read_input_tokens", 0) or 0) > 0,
            truncated=(stop == "max_tokens"),
            error=None,
        )

    async def count_tokens(self, text: str) -> int:
        """Cuenta tokens exactos via API (gratis). Para verificar system prompt."""
        try:
            result = await self._client.messages.count_tokens(
                model=self._model,
                system=[{"type": "text", "text": text}],
                messages=[{"role": "user", "content": "test"}],
            )
            return result.input_tokens
        except Exception as e:
            logger.warning(f"Token count failed: {e}")
            return 0

    async def close(self):
        await self._client.close()
