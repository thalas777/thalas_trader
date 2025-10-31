"""
Google Gemini Provider Implementation
Supports Gemini models for trading signal generation
"""
import json
import logging
import time
import asyncio
from typing import Dict, Any, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .base import (
    BaseLLMProvider,
    ProviderConfig,
    ProviderResponse,
    ProviderError,
    ProviderTimeoutError,
    ProviderAuthenticationError,
)

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini provider implementation

    Supports Gemini models including:
    - gemini-1.5-pro
    - gemini-1.5-flash
    - gemini-1.0-pro
    """

    # Pricing per 1M tokens (as of Oct 2024)
    PRICING = {
        "gemini-1.5-pro": {"input": 3.5, "output": 10.5},
        "gemini-1.5-flash": {"input": 0.35, "output": 1.05},
        "gemini-1.0-pro": {"input": 0.5, "output": 1.5},
    }

    def __init__(self, config: ProviderConfig):
        """
        Initialize Gemini provider

        Args:
            config: Provider configuration

        Raises:
            ProviderError: If Gemini library not installed or configuration invalid
        """
        if not GEMINI_AVAILABLE:
            raise ProviderError(
                "gemini",
                "Google Generative AI library not installed. "
                "Install with: pip install google-generativeai==0.8.3"
            )

        super().__init__(config)

        try:
            # Configure API key
            genai.configure(api_key=config.api_key)

            # Initialize model
            generation_config = {
                "temperature": config.temperature,
                "max_output_tokens": config.max_tokens,
            }

            self.model = genai.GenerativeModel(
                model_name=config.model,
                generation_config=generation_config,
            )

            logger.info(f"Gemini provider initialized with model {config.model}")

        except Exception as e:
            raise ProviderError("gemini", f"Failed to initialize client: {e}", e)

    async def generate_signal(
        self,
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str,
        current_price: Optional[float] = None,
    ) -> ProviderResponse:
        """
        Generate trading signal using Gemini

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

            # Call Gemini API (run in executor since it's sync)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.model.generate_content,
                prompt
            )

            # Extract response text
            response_text = response.text

            # Parse response
            signal_data = self._parse_response(response_text)

            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000

            # Estimate token usage (Gemini doesn't always provide exact counts)
            prompt_tokens = self._estimate_tokens(prompt)
            completion_tokens = self._estimate_tokens(response_text)
            tokens_used = prompt_tokens + completion_tokens

            cost_usd = self.estimate_cost(prompt_tokens, completion_tokens)

            # Update metrics
            self.update_metrics(latency_ms)

            # Build response
            gemini_response = ProviderResponse(
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
                    "prompt_tokens_estimated": prompt_tokens,
                    "completion_tokens_estimated": completion_tokens,
                    "finish_reason": getattr(response, 'finish_reason', None),
                }
            )

            logger.info(
                f"Gemini signal generated: {signal_data['decision']} "
                f"(confidence: {signal_data['confidence']:.2f}, "
                f"latency: {latency_ms:.0f}ms, tokens: ~{tokens_used})"
            )

            return gemini_response

        except json.JSONDecodeError as e:
            error = ProviderError(
                self.config.name,
                f"Failed to parse Gemini response as JSON: {e}",
                e
            )
            self.update_metrics(0, error)
            raise error

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error = ProviderError(
                self.config.name,
                f"Gemini API call failed: {e}",
                e
            )
            self.update_metrics(latency_ms, error)
            raise error

    async def health_check(self) -> bool:
        """
        Check if Gemini API is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple API call to check connectivity
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.model.generate_content,
                "ping"
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
        # Get model-specific pricing or use gemini-1.5-pro as default
        pricing = self.PRICING.get(
            self.config.model,
            self.PRICING["gemini-1.5-pro"]
        )

        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini's JSON response

        Args:
            response_text: Raw response text from Gemini

        Returns:
            Parsed signal data

        Raises:
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If response missing required fields
        """
        # Handle cases where Gemini wraps JSON in markdown code blocks
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

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation)

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4
