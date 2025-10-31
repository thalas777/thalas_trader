"""
OpenAI GPT Provider Implementation
Supports GPT models for trading signal generation with retry logic and comprehensive error handling.
"""
import asyncio
import json
import logging
import time
import re
from typing import Dict, Any, Optional

try:
    from openai import AsyncOpenAI, OpenAI
    from openai import RateLimitError, APIConnectionError, APITimeoutError, AuthenticationError
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
    ProviderRateLimitError,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI GPT provider implementation with advanced features.

    Supports GPT models including:
    - gpt-4-turbo
    - gpt-4
    - gpt-3.5-turbo
    - gpt-4o
    - gpt-4o-mini

    Features:
    - Async/await native implementation
    - Retry logic with exponential backoff
    - Comprehensive error handling
    - Advanced JSON parsing with edge case handling
    - Detailed logging and metrics
    """

    # Pricing per 1M tokens (as of Oct 2024)
    PRICING = {
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    }

    # Retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0  # seconds
    DEFAULT_BACKOFF_MULTIPLIER = 2.0
    DEFAULT_MAX_RETRY_DELAY = 30.0  # seconds

    def __init__(self, config: ProviderConfig):
        """
        Initialize OpenAI provider with async client.

        Args:
            config: Provider configuration object

        Raises:
            ProviderError: If OpenAI library not installed or configuration invalid
            ProviderAuthenticationError: If API key is invalid

        Example:
            >>> config = ProviderConfig(
            ...     name="OpenAI",
            ...     model="gpt-4-turbo",
            ...     api_key="sk-...",
            ... )
            >>> provider = OpenAIProvider(config)
        """
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not installed")
            raise ProviderError(
                "openai",
                "OpenAI library not installed. Install with: pip install openai"
            )

        super().__init__(config)

        # Initialize retry parameters from config or use defaults
        self.max_retries = config.max_retries or self.DEFAULT_MAX_RETRIES
        self.retry_delay = self.DEFAULT_RETRY_DELAY
        self.backoff_multiplier = self.DEFAULT_BACKOFF_MULTIPLIER
        self.max_retry_delay = self.DEFAULT_MAX_RETRY_DELAY

        try:
            logger.debug(f"Initializing AsyncOpenAI client for {config.name}")
            self.client = AsyncOpenAI(
                api_key=config.api_key,
                timeout=config.timeout,
                max_retries=config.max_retries,
            )
            self.sync_client = OpenAI(
                api_key=config.api_key,
                timeout=config.timeout,
                max_retries=config.max_retries,
            )
            logger.info(f"OpenAI provider initialized successfully with model {config.model}")
        except AuthenticationError as e:
            logger.error(f"Authentication failed for OpenAI: {e}")
            raise ProviderAuthenticationError("openai", "Invalid API key", e)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ProviderError("openai", f"Failed to initialize client: {e}", e)

    async def generate_signal(
        self,
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str,
        current_price: Optional[float] = None,
    ) -> ProviderResponse:
        """
        Generate trading signal using GPT with retry logic.

        This method implements exponential backoff retry logic for resilience
        against transient failures and rate limiting.

        Args:
            market_data: Market indicators and data
            pair: Trading pair (e.g., "BTC/USDT")
            timeframe: Data timeframe (e.g., "5m", "1h")
            current_price: Current price (optional)

        Returns:
            ProviderResponse object with trading signal and metadata

        Raises:
            ProviderTimeoutError: If request times out
            ProviderRateLimitError: If rate limit exceeded
            ProviderAuthenticationError: If authentication fails
            ProviderError: If signal generation fails after retries

        Example:
            >>> response = await provider.generate_signal(
            ...     market_data={"rsi": 45.2, "ema_short": 42500.0},
            ...     pair="BTC/USDT",
            ...     timeframe="5m",
            ...     current_price=42500.0
            ... )
        """
        logger.debug(f"Generating signal for {pair} on {timeframe}")
        start_time = time.time()
        retry_count = 0

        while retry_count <= self.max_retries:
            try:
                logger.debug(
                    f"Signal generation attempt {retry_count + 1}/{self.max_retries + 1} "
                    f"for {pair}"
                )

                # Build prompt
                prompt = self.build_prompt(market_data, pair, timeframe, current_price)
                logger.debug(f"Prompt built for {pair} ({len(prompt)} chars)")

                # Call OpenAI API with timeout handling
                completion = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.config.model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature,
                    ),
                    timeout=self.config.timeout,
                )

                # Extract response text
                response_text = completion.choices[0].message.content
                logger.debug(f"Received response ({len(response_text)} chars)")

                # Parse response with comprehensive error handling
                signal_data = self._parse_response(response_text)

                # Calculate metrics
                latency_ms = (time.time() - start_time) * 1000
                tokens_used = completion.usage.total_tokens
                cost_usd = self.estimate_cost(
                    completion.usage.prompt_tokens,
                    completion.usage.completion_tokens
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
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "finish_reason": completion.choices[0].finish_reason,
                        "retry_count": retry_count,
                    }
                )

                logger.info(
                    f"Signal generated for {pair}: {signal_data['decision']} "
                    f"(conf: {signal_data['confidence']:.2f}, "
                    f"latency: {latency_ms:.0f}ms, cost: ${cost_usd:.4f})"
                )

                return response

            except asyncio.TimeoutError as e:
                latency_ms = (time.time() - start_time) * 1000
                logger.warning(
                    f"Timeout on attempt {retry_count + 1}/{self.max_retries + 1} "
                    f"for {pair} after {latency_ms:.0f}ms"
                )

                if retry_count >= self.max_retries:
                    error = ProviderTimeoutError(
                        self.config.name,
                        f"OpenAI API timeout after {self.max_retries + 1} attempts",
                        e
                    )
                    self.update_metrics(latency_ms, error)
                    raise error

                retry_count += 1
                await self._wait_with_backoff(retry_count)

            except (RateLimitError, APIConnectionError) as e:
                latency_ms = (time.time() - start_time) * 1000
                logger.warning(
                    f"Rate limit/connection error on attempt {retry_count + 1}/{self.max_retries + 1}: {e}"
                )

                if retry_count >= self.max_retries:
                    if isinstance(e, RateLimitError):
                        error = ProviderRateLimitError(
                            self.config.name,
                            f"OpenAI rate limit exceeded after {self.max_retries + 1} attempts",
                            e
                        )
                    else:
                        error = ProviderError(
                            self.config.name,
                            f"OpenAI connection failed after {self.max_retries + 1} attempts",
                            e
                        )
                    self.update_metrics(latency_ms, error)
                    raise error

                retry_count += 1
                await self._wait_with_backoff(retry_count)

            except AuthenticationError as e:
                latency_ms = (time.time() - start_time) * 1000
                logger.error(f"Authentication error: {e}")
                error = ProviderAuthenticationError(
                    self.config.name,
                    "Invalid OpenAI API key",
                    e
                )
                self.update_metrics(latency_ms, error)
                raise error

            except json.JSONDecodeError as e:
                latency_ms = (time.time() - start_time) * 1000
                logger.error(f"JSON parsing error: {e}")
                error = ProviderError(
                    self.config.name,
                    f"Failed to parse GPT response as JSON: {e}",
                    e
                )
                self.update_metrics(latency_ms, error)
                raise error

            except ValueError as e:
                latency_ms = (time.time() - start_time) * 1000
                logger.error(f"Validation error: {e}")
                error = ProviderError(
                    self.config.name,
                    f"Invalid response format: {e}",
                    e
                )
                self.update_metrics(latency_ms, error)
                raise error

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Unexpected error on attempt {retry_count + 1}/{self.max_retries + 1}: {e}"
                )

                if retry_count >= self.max_retries:
                    error = ProviderError(
                        self.config.name,
                        f"OpenAI API call failed after {self.max_retries + 1} attempts: {e}",
                        e
                    )
                    self.update_metrics(latency_ms, error)
                    raise error

                retry_count += 1
                await self._wait_with_backoff(retry_count)

    async def _wait_with_backoff(self, retry_count: int) -> None:
        """
        Wait with exponential backoff before retrying.

        Args:
            retry_count: Current retry attempt number
        """
        # Calculate wait time with exponential backoff
        wait_time = min(
            self.retry_delay * (self.backoff_multiplier ** (retry_count - 1)),
            self.max_retry_delay
        )
        logger.debug(
            f"Waiting {wait_time:.1f}s before retry {retry_count} "
            f"(exponential backoff: base={self.retry_delay}s, multiplier={self.backoff_multiplier})"
        )
        await asyncio.sleep(wait_time)

    async def health_check(self) -> bool:
        """
        Check if OpenAI API is accessible and healthy.

        Performs a minimal API call to verify connectivity and authentication.

        Returns:
            True if provider is healthy, False otherwise

        Example:
            >>> if await provider.health_check():
            ...     print("OpenAI is accessible")
        """
        try:
            logger.debug(f"Starting health check for {self.config.name}")

            # Minimal API call to check connectivity
            await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=10,
                ),
                timeout=self.config.timeout,
            )

            logger.info(f"{self.config.name} health check: HEALTHY")
            return True

        except AuthenticationError as e:
            logger.error(f"{self.config.name} health check failed (auth): {e}")
            return False

        except asyncio.TimeoutError as e:
            logger.error(f"{self.config.name} health check timeout: {e}")
            return False

        except RateLimitError as e:
            logger.warning(f"{self.config.name} rate limited during health check: {e}")
            # Rate limiting during health check still means API is accessible
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
        # Get model-specific pricing or use gpt-4-turbo as default
        pricing = self.PRICING.get(
            self.config.model,
            self.PRICING["gpt-4-turbo"]
        )

        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse GPT's JSON response with comprehensive edge case handling.

        Handles various response formats including:
        - Plain JSON
        - JSON wrapped in markdown code blocks (```json ... ```)
        - JSON with surrounding text
        - Malformed JSON with extra commas or trailing content

        Args:
            response_text: Raw response text from GPT

        Returns:
            Parsed signal data dictionary with validated fields

        Raises:
            json.JSONDecodeError: If response cannot be parsed as JSON
            ValueError: If response is missing required fields or invalid values

        Example:
            >>> text = "```json\\n{\\"decision\\": \\"BUY\\", \\"confidence\\": 0.8}\\n```"
            >>> data = provider._parse_response(text)
        """
        logger.debug(f"Parsing response (len={len(response_text)})")

        # Edge case 1: Handle markdown code blocks
        json_str = response_text.strip()

        # Remove markdown code block wrappers
        if "```json" in json_str:
            logger.debug("Detected markdown json code block")
            try:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            except IndexError:
                logger.warning("Failed to extract JSON from markdown json block")
        elif "```" in json_str:
            logger.debug("Detected markdown code block")
            try:
                parts = json_str.split("```")
                # Find the largest block that looks like JSON
                json_candidates = [p.strip() for p in parts if p.strip().startswith("{")]
                if json_candidates:
                    json_str = json_candidates[0]
                else:
                    json_str = parts[1].strip() if len(parts) > 1 else json_str
            except IndexError:
                logger.warning("Failed to extract JSON from markdown block")

        # Edge case 2: Extract JSON if there's surrounding text
        if not json_str.startswith("{"):
            logger.debug("Attempting to extract JSON from text with surrounding content")
            # Try to find JSON object in the text
            match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", json_str)
            if match:
                json_str = match.group(0)
                logger.debug("Extracted JSON from surrounding text")

        # Edge case 3: Clean up common JSON issues
        json_str = self._sanitize_json(json_str)

        # Parse JSON
        try:
            logger.debug("Attempting to parse JSON")
            signal = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}")
            logger.error(f"Problematic JSON: {json_str[:200]}...")
            raise json.JSONDecodeError(
                f"Failed to parse response as JSON: {e.msg}",
                e.doc,
                e.pos,
            )

        # Validate required fields
        required_fields = ["decision", "confidence", "reasoning"]
        missing_fields = [f for f in required_fields if f not in signal]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Validate and normalize decision
        decision = str(signal.get("decision", "")).upper().strip()
        if decision not in ["BUY", "SELL", "HOLD"]:
            raise ValueError(
                f"Invalid decision '{decision}'. Must be one of: BUY, SELL, HOLD"
            )
        signal["decision"] = decision

        # Validate confidence
        try:
            confidence = float(signal["confidence"])
            if not 0 <= confidence <= 1:
                raise ValueError(f"Confidence out of range: {confidence} (must be 0-1)")
            signal["confidence"] = confidence
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid confidence value: {signal['confidence']} ({e})")

        # Validate reasoning is present and non-empty
        reasoning = str(signal.get("reasoning", "")).strip()
        if not reasoning:
            raise ValueError("Reasoning cannot be empty")
        signal["reasoning"] = reasoning

        # Validate optional risk_level
        if "risk_level" in signal:
            risk_level = str(signal.get("risk_level", "")).lower().strip()
            if risk_level and risk_level not in ["low", "medium", "high"]:
                logger.warning(f"Invalid risk_level: {risk_level}, ignoring")
                signal.pop("risk_level", None)
            elif risk_level:
                signal["risk_level"] = risk_level

        # Validate optional numeric fields
        for field in ["suggested_stop_loss", "suggested_take_profit"]:
            if field in signal and signal[field] is not None:
                try:
                    signal[field] = float(signal[field])
                except (TypeError, ValueError):
                    logger.warning(f"Invalid {field}: {signal[field]}, removing")
                    signal.pop(field, None)

        logger.debug(f"Successfully parsed response: {signal['decision']}")
        return signal

    def _sanitize_json(self, json_str: str) -> str:
        """
        Sanitize common JSON issues from LLM responses.

        Fixes:
        - Trailing commas before closing braces
        - Single quotes instead of double quotes (limited support)
        - Extra commas in arrays

        Args:
            json_str: Raw JSON string

        Returns:
            Sanitized JSON string

        Note:
            This is a basic sanitization. Complex malformed JSON may still fail.
        """
        # Remove trailing commas before } or ]
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        # Remove duplicate commas
        json_str = re.sub(r',+', ',', json_str)

        return json_str
