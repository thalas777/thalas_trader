"""
Anthropic Claude Provider Implementation
Supports Claude models for trading signal generation with async support,
retry logic with exponential backoff, comprehensive error handling, and logging.
"""
import asyncio
import json
import logging
import random
import re
import time
from typing import Dict, Any, Optional

try:
    from anthropic import Anthropic, AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base import (
    BaseLLMProvider,
    ProviderConfig,
    ProviderResponse,
    ProviderStatus,
    ProviderError,
    ProviderTimeoutError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
)

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude provider implementation

    Supports all Claude models including:
    - claude-3-5-sonnet-20241022
    - claude-3-opus-20240229
    - claude-3-sonnet-20240229
    - claude-3-haiku-20240307
    """

    # Pricing per 1M tokens (as of Oct 2024)
    PRICING = {
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }

    def __init__(self, config: ProviderConfig):
        """
        Initialize Anthropic provider

        Args:
            config: Provider configuration

        Raises:
            ProviderError: If Anthropic library not installed or configuration invalid
        """
        if not ANTHROPIC_AVAILABLE:
            raise ProviderError(
                "anthropic",
                "Anthropic library not installed. Install with: pip install anthropic"
            )

        super().__init__(config)

        try:
            self.client = AsyncAnthropic(
                api_key=config.api_key,
                timeout=config.timeout,
                max_retries=config.max_retries,
            )
            self.sync_client = Anthropic(
                api_key=config.api_key,
                timeout=config.timeout,
                max_retries=config.max_retries,
            )
        except Exception as e:
            raise ProviderError("anthropic", f"Failed to initialize client: {e}", e)

    async def generate_signal(
        self,
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str,
        current_price: Optional[float] = None,
    ) -> ProviderResponse:
        """
        Generate trading signal using Claude with retry logic and exponential backoff

        Args:
            market_data: Market indicators and data
            pair: Trading pair
            timeframe: Data timeframe
            current_price: Current price

        Returns:
            ProviderResponse with trading signal

        Raises:
            ProviderError: If signal generation fails after all retries
            ProviderTimeoutError: If request times out
            ProviderRateLimitError: If rate limit is hit
            ProviderAuthenticationError: If authentication fails
        """
        start_time = time.time()
        last_error: Optional[Exception] = None

        # Build prompt once
        prompt = self.build_prompt(market_data, pair, timeframe, current_price)

        logger.debug(
            f"Generating signal for {pair} on {timeframe} timeframe "
            f"using {self.config.model}"
        )

        for attempt in range(self.config.max_retries):
            try:
                # Call Claude API with async support
                message = await self._call_api_with_timeout(prompt)

                # Extract response text
                response_text = message.content[0].text

                logger.debug(
                    f"Received response from Claude (attempt {attempt + 1}): "
                    f"{len(response_text)} characters"
                )

                # Parse response with error handling
                signal_data = self._parse_response(response_text)

                # Calculate metrics
                latency_ms = (time.time() - start_time) * 1000
                tokens_used = message.usage.input_tokens + message.usage.output_tokens
                cost_usd = self.estimate_cost(
                    message.usage.input_tokens,
                    message.usage.output_tokens
                )

                # Update metrics
                self.update_metrics(latency_ms)
                self.set_status(ProviderStatus.ACTIVE)

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
                        "input_tokens": message.usage.input_tokens,
                        "output_tokens": message.usage.output_tokens,
                        "stop_reason": message.stop_reason,
                        "model": self.config.model,
                        "pair": pair,
                        "timeframe": timeframe,
                    }
                )

                logger.info(
                    f"Claude signal generated: {signal_data['decision']} "
                    f"(confidence: {signal_data['confidence']:.2f}, "
                    f"latency: {latency_ms:.0f}ms, tokens: {tokens_used})"
                )

                return response

            except (ProviderTimeoutError, ProviderRateLimitError) as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    wait_time = self._get_backoff_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries} failed "
                        f"({type(e).__name__}). Retrying in {wait_time:.2f}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"All {self.config.max_retries} attempts failed. "
                        f"Last error: {e}"
                    )
                    self.update_metrics(0, e)
                    self.set_status(ProviderStatus.DEGRADED)
                    raise e

            except ProviderAuthenticationError as e:
                # Don't retry on auth errors
                logger.error(f"Authentication failed: {e}")
                self.update_metrics(0, e)
                self.set_status(ProviderStatus.UNAVAILABLE)
                raise e

            except json.JSONDecodeError as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    logger.warning(
                        f"JSON parsing failed on attempt {attempt + 1}. "
                        f"Retrying... Error: {e}"
                    )
                    await asyncio.sleep(self._get_backoff_delay(attempt))
                else:
                    logger.error(
                        f"Failed to parse response as JSON after {self.config.max_retries} "
                        f"attempts: {e}"
                    )
                    error = ProviderError(
                        self.config.name,
                        f"Failed to parse Claude response as JSON: {e}",
                        e
                    )
                    self.update_metrics(0, error)
                    self.set_status(ProviderStatus.DEGRADED)
                    raise error

            except ProviderError as e:
                last_error = e
                logger.warning(
                    f"Provider error on attempt {attempt + 1}: {e}"
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self._get_backoff_delay(attempt))
                else:
                    logger.error(
                        f"All {self.config.max_retries} attempts failed with: {e}"
                    )
                    self.update_metrics(0, e)
                    self.set_status(ProviderStatus.DEGRADED)
                    raise e

            except Exception as e:
                last_error = e
                latency_ms = (time.time() - start_time) * 1000
                error = ProviderError(
                    self.config.name,
                    f"Unexpected error in signal generation: {e}",
                    e
                )

                if attempt < self.config.max_retries - 1:
                    logger.warning(
                        f"Unexpected error on attempt {attempt + 1}, retrying: {e}"
                    )
                    await asyncio.sleep(self._get_backoff_delay(attempt))
                else:
                    logger.error(
                        f"Claude API call failed after {self.config.max_retries} "
                        f"attempts: {e}"
                    )
                    self.update_metrics(latency_ms, error)
                    self.set_status(ProviderStatus.DEGRADED)
                    raise error

        # This should not be reached, but just in case
        if last_error:
            error = ProviderError(
                self.config.name,
                f"All retries exhausted: {last_error}",
                last_error
            )
            self.update_metrics(0, error)
            self.set_status(ProviderStatus.DEGRADED)
            raise error

    async def health_check(self) -> bool:
        """
        Check if Anthropic API is accessible with timeout protection

        Returns:
            True if healthy, False otherwise
        """
        try:
            logger.debug(f"Starting health check for {self.config.name}")

            # Use timeout for health check
            try:
                message = await asyncio.wait_for(
                    self.client.messages.create(
                        model=self.config.model,
                        max_tokens=10,
                        messages=[{"role": "user", "content": "ping"}],
                    ),
                    timeout=self.config.timeout
                )
                logger.info(f"{self.config.name} health check: OK")
                self.set_status(ProviderStatus.ACTIVE)
                return True

            except asyncio.TimeoutError:
                logger.warning(f"{self.config.name} health check timed out")
                self.set_status(ProviderStatus.DEGRADED)
                return False

        except Exception as e:
            logger.error(f"{self.config.name} health check failed: {e}")
            self.set_status(ProviderStatus.UNAVAILABLE)
            return False

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate cost of API call based on token counts

        Pricing data is as of Oct 2024. Costs are calculated as:
        - Input cost = (prompt_tokens / 1,000,000) * input_price_per_million
        - Output cost = (completion_tokens / 1,000,000) * output_price_per_million
        - Total cost = input_cost + output_cost

        Args:
            prompt_tokens: Number of input tokens used
            completion_tokens: Number of output tokens generated

        Returns:
            Estimated cost in USD (rounded to 6 decimal places)
        """
        pricing = self.PRICING.get(
            self.config.model,
            self.PRICING["claude-3-5-sonnet-20241022"]  # Default pricing
        )

        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        logger.debug(
            f"Cost estimation for {self.config.model}: "
            f"input={prompt_tokens} tokens (${input_cost:.6f}), "
            f"output={completion_tokens} tokens (${output_cost:.6f}), "
            f"total=${total_cost:.6f}"
        )

        return round(total_cost, 6)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's JSON response with comprehensive error handling

        Handles edge cases including:
        - JSON wrapped in markdown code blocks (```json...```)
        - JSON wrapped in triple backticks (```...```)
        - Extra whitespace and newlines
        - Different case variations of JSON keys
        - Missing optional fields
        - Invalid data types for fields

        Args:
            response_text: Raw response text from Claude

        Returns:
            Parsed and validated signal data dictionary

        Raises:
            json.JSONDecodeError: If response cannot be parsed as valid JSON
            ValueError: If response missing required fields or invalid values
        """
        if not response_text:
            raise ValueError("Response text is empty")

        # Try multiple strategies to extract JSON
        json_str = self._extract_json(response_text)

        logger.debug(f"Extracted JSON string: {json_str[:100]}...")

        # Parse JSON
        try:
            signal = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Attempted to parse: {json_str[:200]}")
            raise

        if not isinstance(signal, dict):
            raise ValueError(
                f"Expected JSON object, got {type(signal).__name__}"
            )

        # Normalize keys to lowercase for case-insensitive matching
        signal_lower = {k.lower(): v for k, v in signal.items()}

        # Validate and extract required fields
        required_fields = ["decision", "confidence", "reasoning"]
        normalized_signal = {}

        for field in required_fields:
            if field not in signal_lower:
                raise ValueError(
                    f"Missing required field: '{field}'. "
                    f"Available fields: {list(signal_lower.keys())}"
                )
            normalized_signal[field] = signal_lower[field]

        # Validate decision value
        decision = str(normalized_signal["decision"]).upper().strip()
        if decision not in ["BUY", "SELL", "HOLD"]:
            raise ValueError(
                f"Invalid decision value: '{decision}'. "
                f"Must be one of: BUY, SELL, HOLD"
            )
        normalized_signal["decision"] = decision

        # Validate and normalize confidence
        try:
            confidence = float(normalized_signal["confidence"])
            if not 0 <= confidence <= 1:
                raise ValueError(
                    f"Confidence must be between 0 and 1, got {confidence}"
                )
            normalized_signal["confidence"] = confidence
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid confidence value: {normalized_signal['confidence']}. "
                f"Must be a number between 0 and 1. Error: {e}"
            )

        # Validate reasoning is a string
        reasoning = str(normalized_signal["reasoning"]).strip()
        if not reasoning:
            raise ValueError("Reasoning cannot be empty")
        normalized_signal["reasoning"] = reasoning

        # Handle optional fields
        for optional_field in ["risk_level", "suggested_stop_loss", "suggested_take_profit"]:
            if optional_field in signal_lower:
                value = signal_lower[optional_field]

                if optional_field == "risk_level":
                    if value:
                        risk = str(value).lower().strip()
                        if risk not in ["low", "medium", "high"]:
                            logger.warning(
                                f"Invalid risk_level: {risk}. "
                                f"Using None instead"
                            )
                            normalized_signal[optional_field] = None
                        else:
                            normalized_signal[optional_field] = risk
                    else:
                        normalized_signal[optional_field] = None

                else:  # suggested_stop_loss or suggested_take_profit
                    try:
                        if value is not None:
                            normalized_signal[optional_field] = float(value)
                        else:
                            normalized_signal[optional_field] = None
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid {optional_field}: {value}. "
                            f"Using None instead"
                        )
                        normalized_signal[optional_field] = None
            else:
                normalized_signal[optional_field] = None

        logger.debug(f"Parsed signal: {normalized_signal}")

        return normalized_signal

    def _extract_json(self, response_text: str) -> str:
        """
        Extract JSON from response text with multiple fallback strategies

        Args:
            response_text: Raw response text

        Returns:
            JSON string ready to parse

        Raises:
            ValueError: If no valid JSON can be extracted
        """
        strategies = [
            # Strategy 1: Extract from ```json...``` blocks
            lambda text: (
                text.split("```json")[1].split("```")[0].strip()
                if "```json" in text else None
            ),
            # Strategy 2: Extract from ```...``` blocks
            lambda text: (
                text.split("```")[1].split("```")[0].strip()
                if text.count("```") >= 2 else None
            ),
            # Strategy 3: Find JSON object using regex
            lambda text: self._find_json_in_text(text),
            # Strategy 4: Try to use the text as-is
            lambda text: text.strip(),
        ]

        for strategy in strategies:
            try:
                json_str = strategy(response_text)
                if json_str:
                    # Validate it's JSON by attempting to parse
                    json.loads(json_str)
                    return json_str
            except (json.JSONDecodeError, IndexError, AttributeError):
                continue

        raise ValueError(
            "Could not extract valid JSON from response. "
            f"Response preview: {response_text[:200]}"
        )

    def _find_json_in_text(self, text: str) -> Optional[str]:
        """
        Find JSON object in text using regex pattern matching

        Args:
            text: Text to search

        Returns:
            JSON string if found, None otherwise
        """
        # Look for patterns like {...} at the start
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
        if match:
            return match.group(0)
        return None

    def _get_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter

        Uses formula: delay = min(max_delay, 2^attempt + random_jitter)

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        base_delay = 2 ** attempt
        max_delay = 60  # Cap at 60 seconds
        jitter = random.uniform(0, 1)  # Random jitter between 0-1 second

        delay = min(max_delay, base_delay + jitter)
        logger.debug(f"Backoff delay for attempt {attempt + 1}: {delay:.2f}s")

        return delay

    async def _call_api_with_timeout(self, prompt: str):
        """
        Call Claude API with timeout protection

        Args:
            prompt: The prompt to send to Claude

        Returns:
            API response message object

        Raises:
            ProviderTimeoutError: If the request times out
            ProviderAuthenticationError: If authentication fails
            ProviderRateLimitError: If rate limited
            ProviderError: For other API errors
        """
        try:
            message = await asyncio.wait_for(
                self.client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=self.config.timeout
            )
            return message

        except asyncio.TimeoutError as e:
            error = ProviderTimeoutError(
                self.config.name,
                f"API request timed out after {self.config.timeout}s",
                e
            )
            logger.error(f"Timeout: {error}")
            raise error

        except Exception as e:
            error_str = str(e).lower()

            # Check for authentication errors
            if "authentication" in error_str or "unauthorized" in error_str or "api key" in error_str:
                error = ProviderAuthenticationError(
                    self.config.name,
                    f"Authentication failed: {e}",
                    e
                )
                logger.error(f"Auth error: {error}")
                raise error

            # Check for rate limit errors
            if "rate limit" in error_str or "429" in str(e) or "too many requests" in error_str:
                error = ProviderRateLimitError(
                    self.config.name,
                    f"Rate limited: {e}",
                    e
                )
                logger.warning(f"Rate limit hit: {error}")
                raise error

            # For other errors, wrap as ProviderError
            error = ProviderError(
                self.config.name,
                f"API call failed: {e}",
                e
            )
            logger.error(f"API error: {error}")
            raise error
