"""
xAI Grok Provider Implementation
Supports Grok models for trading signal generation
Uses OpenAI-compatible API
"""
import json
import logging
import time
from typing import Dict, Any, Optional

try:
    from openai import AsyncOpenAI, OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .base import (
    BaseLLMProvider,
    ProviderConfig,
    ProviderResponse,
    ProviderError,
    ProviderTimeoutError,
    ProviderAuthenticationError,
)

logger = logging.getLogger(__name__)


class GrokProvider(BaseLLMProvider):
    """
    xAI Grok provider implementation

    Uses OpenAI-compatible API endpoint.
    Supports Grok models including:
    - grok-beta
    - grok-vision-beta
    """

    # Default base URL for xAI API
    DEFAULT_BASE_URL = "https://api.x.ai/v1"

    # Pricing per 1M tokens (estimated, adjust based on actual pricing)
    PRICING = {
        "grok-beta": {"input": 5.0, "output": 15.0},
        "grok-vision-beta": {"input": 5.0, "output": 15.0},
    }

    def __init__(self, config: ProviderConfig):
        """
        Initialize Grok provider

        Args:
            config: Provider configuration

        Raises:
            ProviderError: If OpenAI library not installed or configuration invalid
        """
        if not OPENAI_AVAILABLE:
            raise ProviderError(
                "grok",
                "OpenAI library not installed (required for Grok). "
                "Install with: pip install openai"
            )

        super().__init__(config)

        # Use custom base URL or default
        base_url = config.base_url or self.DEFAULT_BASE_URL

        try:
            self.client = AsyncOpenAI(
                api_key=config.api_key,
                base_url=base_url,
                timeout=config.timeout,
                max_retries=config.max_retries,
            )
            self.sync_client = OpenAI(
                api_key=config.api_key,
                base_url=base_url,
                timeout=config.timeout,
                max_retries=config.max_retries,
            )
            logger.info(f"Grok provider initialized with model {config.model} at {base_url}")

        except Exception as e:
            raise ProviderError("grok", f"Failed to initialize client: {e}", e)

    async def generate_signal(
        self,
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str,
        current_price: Optional[float] = None,
    ) -> ProviderResponse:
        """
        Generate trading signal using Grok

        Args:
            market_data: Market indicators and data
            pair: Trading pair
            timeframe: Data timeframe
            current_price: Current price

        Returns:
            ProviderResponse with trading signal

        Raises:
            ProviderError: If signal generation fails
        """
        start_time = time.time()

        try:
            # Build prompt
            prompt = self.build_prompt(market_data, pair, timeframe, current_price)

            # Call Grok API (OpenAI-compatible)
            completion = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            # Extract response text
            response_text = completion.choices[0].message.content

            # Parse response
            signal_data = self._parse_response(response_text)

            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            tokens_used = completion.usage.total_tokens if completion.usage else 0
            cost_usd = self.estimate_cost(
                completion.usage.prompt_tokens if completion.usage else 0,
                completion.usage.completion_tokens if completion.usage else 0
            )

            # Update metrics
            self.update_metrics(latency_ms)

            # Build response
            response = ProviderResponse(
                provider_name=self.config.name,
                model=self.config.model,
                decision=signal_data["decision"],
                confidence=signal_data["confidence"],
                reasoning=signal_data["reasoning"],
                risk_level=signal_data.get("risk_level"),
                suggested_stop_loss=signal_data.get("suggested_stop_loss"),
                suggested_take_profit=signal_data.get("suggested_take_profit"),
                raw_response=response_text,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                metadata={
                    "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
                    "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
                    "finish_reason": completion.choices[0].finish_reason,
                }
            )

            logger.info(
                f"Grok signal generated: {signal_data['decision']} "
                f"(confidence: {signal_data['confidence']:.2f}, "
                f"latency: {latency_ms:.0f}ms, tokens: {tokens_used})"
            )

            return response

        except json.JSONDecodeError as e:
            error = ProviderError(
                self.config.name,
                f"Failed to parse Grok response as JSON: {e}",
                e
            )
            self.update_metrics(0, error)
            raise error

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error = ProviderError(
                self.config.name,
                f"Grok API call failed: {e}",
                e
            )
            self.update_metrics(latency_ms, error)
            raise error

    async def health_check(self) -> bool:
        """
        Check if Grok API is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple API call to check connectivity
            await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=10,
            )
            logger.info(f"{self.config.name} health check: OK")
            return True

        except Exception as e:
            logger.error(f"{self.config.name} health check failed: {e}")
            return False

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate cost of API call

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Get model-specific pricing or use grok-beta as default
        pricing = self.PRICING.get(
            self.config.model,
            self.PRICING["grok-beta"]
        )

        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Grok's JSON response

        Args:
            response_text: Raw response text from Grok

        Returns:
            Parsed signal data

        Raises:
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If response missing required fields
        """
        # Handle cases where Grok wraps JSON in markdown code blocks
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()

        signal = json.loads(json_str)

        # Validate required fields
        required_fields = ["decision", "confidence", "reasoning"]
        for field in required_fields:
            if field not in signal:
                raise ValueError(f"Missing required field: {field}")

        # Validate decision value
        if signal["decision"] not in ["BUY", "SELL", "HOLD"]:
            raise ValueError(f"Invalid decision: {signal['decision']}")

        # Validate confidence range
        if not 0 <= signal["confidence"] <= 1:
            raise ValueError(f"Invalid confidence: {signal['confidence']}")

        return signal
