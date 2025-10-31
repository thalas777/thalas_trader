"""
Multi-Provider Orchestrator for LLM Consensus System
Coordinates multiple LLM providers and aggregates their responses using consensus mechanism
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from llm_service.providers.registry import ProviderRegistry
from llm_service.providers.base import (
    BaseLLMProvider,
    ProviderResponse,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthenticationError,
)
from llm_service.consensus.aggregator import SignalAggregator, ConsensusResult

logger = logging.getLogger(__name__)


class MultiProviderOrchestrator:
    """
    Orchestrator for multi-provider LLM consensus system

    Coordinates parallel calls to multiple LLM providers and uses the
    SignalAggregator to achieve consensus on trading signals.

    Features:
    - Parallel provider execution using asyncio.gather()
    - Graceful handling of partial failures
    - Performance metrics tracking (latency, cost)
    - Configurable provider weights
    - Minimum provider threshold
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        min_providers: int = 1,
        min_confidence: float = 0.5,
        timeout_seconds: float = 30.0,
    ):
        """
        Initialize multi-provider orchestrator

        Args:
            registry: Provider registry instance
            min_providers: Minimum number of successful providers required
            min_confidence: Minimum confidence threshold for consensus
            timeout_seconds: Maximum time to wait for all providers
        """
        self.registry = registry
        self.min_providers = min_providers
        self.min_confidence = min_confidence
        self.timeout_seconds = timeout_seconds

        # Initialize signal aggregator
        self.aggregator = SignalAggregator(
            min_providers=min_providers,
            min_confidence=min_confidence
        )

        # Metrics
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0

        logger.info(
            f"MultiProviderOrchestrator initialized "
            f"(min_providers={min_providers}, "
            f"min_confidence={min_confidence}, "
            f"timeout={timeout_seconds}s)"
        )

    async def generate_consensus_signal(
        self,
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str,
        current_price: float,
        provider_weights: Optional[Dict[str, float]] = None,
    ) -> ConsensusResult:
        """
        Generate consensus trading signal from multiple LLM providers

        Args:
            market_data: Market indicators and data
            pair: Trading pair (e.g., "BTC/USDT")
            timeframe: Data timeframe (e.g., "5m", "1h")
            current_price: Current market price
            provider_weights: Optional custom weights for providers

        Returns:
            ConsensusResult with aggregated decision

        Raises:
            ValueError: If insufficient providers available or successful
            RuntimeError: If consensus cannot be reached
        """
        self._total_requests += 1
        start_time = datetime.utcnow()

        logger.info(
            f"Generating consensus signal for {pair} ({timeframe}) "
            f"at price {current_price}"
        )

        # Get available providers from registry
        available_providers = self.registry.get_available_providers()

        if not available_providers:
            self._failed_requests += 1
            raise ValueError(
                "No available providers in registry. "
                "Ensure providers are registered and enabled."
            )

        if len(available_providers) < self.min_providers:
            self._failed_requests += 1
            raise ValueError(
                f"Insufficient available providers: "
                f"{len(available_providers)} < {self.min_providers}. "
                f"Available: {[p.config.name for p in available_providers]}"
            )

        logger.info(
            f"Querying {len(available_providers)} providers: "
            f"{[p.config.name for p in available_providers]}"
        )

        # Call all providers in parallel
        responses, failures = await self._call_providers_parallel(
            providers=available_providers,
            market_data=market_data,
            pair=pair,
            timeframe=timeframe,
            current_price=current_price,
        )

        # Log failures
        if failures:
            logger.warning(
                f"{len(failures)} provider(s) failed: "
                f"{list(failures.keys())}"
            )
            for provider_name, error in failures.items():
                logger.error(
                    f"Provider {provider_name} failed: {error}",
                    exc_info=error if isinstance(error, Exception) else None
                )

        # Check if we have enough successful responses
        if len(responses) < self.min_providers:
            self._failed_requests += 1
            raise ValueError(
                f"Insufficient successful provider responses: "
                f"{len(responses)} < {self.min_providers}. "
                f"Successful: {[r.provider_name for r in responses]}, "
                f"Failed: {list(failures.keys())}"
            )

        logger.info(
            f"Received {len(responses)} successful responses from providers: "
            f"{[r.provider_name for r in responses]}"
        )

        # Build weights dictionary
        weights = self._build_weights_dict(
            responses=responses,
            custom_weights=provider_weights
        )

        logger.debug(f"Provider weights: {weights}")

        # Aggregate responses using consensus mechanism
        try:
            consensus = self.aggregator.aggregate(
                responses=responses,
                weights=weights
            )
        except Exception as e:
            self._failed_requests += 1
            logger.error(f"Consensus aggregation failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to aggregate consensus: {e}") from e

        # Calculate total orchestration latency
        end_time = datetime.utcnow()
        total_latency_ms = (end_time - start_time).total_seconds() * 1000

        # Update consensus result with orchestration metrics
        consensus.total_latency_ms = total_latency_ms
        consensus.total_providers = len(available_providers)

        self._successful_requests += 1

        logger.info(
            f"Consensus reached: {consensus.decision} "
            f"(confidence: {consensus.confidence:.2f}, "
            f"agreement: {consensus.agreement_score:.2f}, "
            f"providers: {consensus.participating_providers}/{consensus.total_providers}, "
            f"latency: {total_latency_ms:.0f}ms, "
            f"cost: ${consensus.total_cost_usd:.6f})"
        )

        return consensus

    async def _call_providers_parallel(
        self,
        providers: List[BaseLLMProvider],
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str,
        current_price: float,
    ) -> tuple[List[ProviderResponse], Dict[str, Exception]]:
        """
        Call multiple providers in parallel using asyncio.gather()

        Args:
            providers: List of provider instances
            market_data: Market data to analyze
            pair: Trading pair
            timeframe: Data timeframe
            current_price: Current price

        Returns:
            Tuple of (successful_responses, failures_dict)
        """
        # Create tasks for all providers
        tasks = [
            self._call_provider_safe(
                provider=provider,
                market_data=market_data,
                pair=pair,
                timeframe=timeframe,
                current_price=current_price,
            )
            for provider in providers
        ]

        # Execute all tasks in parallel with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Provider orchestration timeout after {self.timeout_seconds}s"
            )
            # Return timeout errors for all providers
            results = [
                ProviderTimeoutError(
                    provider.config.name,
                    f"Orchestration timeout after {self.timeout_seconds}s"
                )
                for provider in providers
            ]

        # Separate successful responses from failures
        responses = []
        failures = {}

        for provider, result in zip(providers, results):
            if isinstance(result, ProviderResponse):
                responses.append(result)
            elif isinstance(result, Exception):
                failures[provider.config.name] = result
            else:
                # Should not happen, but handle gracefully
                failures[provider.config.name] = ValueError(
                    f"Unexpected result type: {type(result)}"
                )

        return responses, failures

    async def _call_provider_safe(
        self,
        provider: BaseLLMProvider,
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str,
        current_price: float,
    ) -> ProviderResponse:
        """
        Call a single provider with error handling

        Args:
            provider: Provider instance
            market_data: Market data
            pair: Trading pair
            timeframe: Timeframe
            current_price: Current price

        Returns:
            ProviderResponse on success, raises Exception on failure
        """
        provider_name = provider.config.name

        try:
            logger.debug(f"Calling provider: {provider_name}")

            response = await provider.generate_signal(
                market_data=market_data,
                pair=pair,
                timeframe=timeframe,
                current_price=current_price,
            )

            logger.debug(
                f"Provider {provider_name} responded: "
                f"{response.decision} (confidence: {response.confidence:.2f})"
            )

            return response

        except ProviderAuthenticationError as e:
            # Auth errors are not retryable - log and propagate
            logger.error(f"Authentication failed for {provider_name}: {e}")
            raise

        except ProviderRateLimitError as e:
            # Rate limit errors - log and propagate
            logger.warning(f"Rate limit hit for {provider_name}: {e}")
            raise

        except ProviderTimeoutError as e:
            # Timeout errors - log and propagate
            logger.warning(f"Timeout for {provider_name}: {e}")
            raise

        except ProviderError as e:
            # Generic provider errors
            logger.error(f"Provider error for {provider_name}: {e}")
            raise

        except Exception as e:
            # Unexpected errors - wrap in ProviderError
            logger.error(
                f"Unexpected error for {provider_name}: {e}",
                exc_info=True
            )
            raise ProviderError(
                provider_name=provider_name,
                message=f"Unexpected error: {e}",
                original_error=e
            ) from e

    def _build_weights_dict(
        self,
        responses: List[ProviderResponse],
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Build weights dictionary for consensus aggregation

        Args:
            responses: List of provider responses
            custom_weights: Optional custom weights to override defaults

        Returns:
            Dictionary mapping provider names to weights
        """
        weights = {}

        for response in responses:
            provider_name = response.provider_name

            # Check for custom weight
            if custom_weights and provider_name in custom_weights:
                weights[provider_name] = custom_weights[provider_name]
            else:
                # Get weight from provider config
                provider = self.registry.get_provider(provider_name)
                if provider:
                    weights[provider_name] = provider.config.weight
                else:
                    # Fallback to equal weight if provider not found
                    weights[provider_name] = 1.0

        return weights

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get orchestrator performance metrics

        Returns:
            Dictionary with metrics
        """
        success_rate = (
            self._successful_requests / self._total_requests
            if self._total_requests > 0
            else 0.0
        )

        return {
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "success_rate": success_rate,
            "registry_status": self.registry.get_registry_status(),
            "configuration": {
                "min_providers": self.min_providers,
                "min_confidence": self.min_confidence,
                "timeout_seconds": self.timeout_seconds,
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all providers

        Returns:
            Dictionary with health status for each provider
        """
        logger.info("Performing health check on all providers")

        health_results = await self.registry.health_check_all()

        available_count = sum(1 for healthy in health_results.values() if healthy)

        return {
            "status": "healthy" if available_count >= self.min_providers else "degraded",
            "available_providers": available_count,
            "required_providers": self.min_providers,
            "provider_health": health_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def reset_metrics(self) -> None:
        """Reset orchestrator metrics"""
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        logger.info("Orchestrator metrics reset")
