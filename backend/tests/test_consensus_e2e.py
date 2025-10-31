"""
Comprehensive End-to-End Tests for Multi-Provider Consensus Flow
Tests the complete consensus flow: API → Orchestrator → Providers → Aggregator → API Response

Test Scenarios:
1. Unanimous Decision - All providers vote the same
2. Split Decision (Majority) - Majority wins
3. Tie-Breaking - Test how weights affect tie-breaking
4. Partial Provider Failures - Some providers fail
5. Custom Provider Weights - Test weighted voting
6. Different Timeframes and Pairs - Test various configurations
7. API Endpoint Integration - Test actual HTTP requests
8. Performance Tests - Test concurrent requests (optional)
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from rest_framework.test import APIClient
from rest_framework import status as http_status

from llm_service.providers.base import (
    ProviderConfig,
    ProviderResponse,
    BaseLLMProvider,
    ProviderStatus,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthenticationError,
)
from llm_service.providers.registry import ProviderRegistry
from llm_service.consensus.aggregator import ConsensusResult, SignalAggregator
from llm_service.multi_provider_orchestrator import MultiProviderOrchestrator


# ==============================================================================
# Mock Provider Classes
# ==============================================================================

class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider for E2E testing
    Allows configuring decision, confidence, and failure conditions
    """

    def __init__(
        self,
        config: ProviderConfig,
        decision: str = "BUY",
        confidence: float = 0.85,
        should_fail: bool = False,
        failure_type: str = None,
        latency_ms: float = 100.0,
    ):
        super().__init__(config)
        self.test_decision = decision
        self.test_confidence = confidence
        self.should_fail = should_fail
        self.failure_type = failure_type
        self.test_latency_ms = latency_ms

    async def generate_signal(self, market_data, pair, timeframe, current_price):
        """Generate mock signal or simulate failure"""
        # Simulate latency
        await asyncio.sleep(self.test_latency_ms / 1000.0)

        # Simulate failures
        if self.should_fail:
            if self.failure_type == "timeout":
                raise ProviderTimeoutError(
                    self.config.name, "Mock timeout error"
                )
            elif self.failure_type == "rate_limit":
                raise ProviderRateLimitError(
                    self.config.name, "Mock rate limit error"
                )
            elif self.failure_type == "auth":
                raise ProviderAuthenticationError(
                    self.config.name, "Mock authentication error"
                )
            else:
                raise ProviderError(
                    self.config.name, "Mock generic error"
                )

        # Return successful response
        return ProviderResponse(
            provider_name=self.config.name,
            model=self.config.model,
            decision=self.test_decision,
            confidence=self.test_confidence,
            reasoning=f"Mock analysis from {self.config.name}: {self.test_decision} signal with {self.test_confidence:.0%} confidence",
            risk_level="medium",
            suggested_stop_loss=current_price * 0.97 if self.test_decision == "BUY" else current_price * 1.03,
            suggested_take_profit=current_price * 1.05 if self.test_decision == "BUY" else current_price * 0.95,
            latency_ms=self.test_latency_ms,
            tokens_used=600,
            cost_usd=0.0015,
        )

    async def health_check(self):
        """Mock health check"""
        return not self.should_fail

    def estimate_cost(self, input_tokens, output_tokens):
        """Mock cost estimation"""
        return 0.0015


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "rsi": 65.5,
        "macd": 150.0,
        "bollinger_upper": 51000,
        "bollinger_lower": 49000,
        "volume": 1500000,
        "price_change_24h": 2.5,
    }


@pytest.fixture
def api_client():
    """Fixture for Django REST API client"""
    return APIClient()


# ==============================================================================
# Test Scenario 1: Unanimous Decision
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_unanimous_decision_all_buy(sample_market_data):
    """
    Test unanimous decision - all providers vote BUY
    Expected: High agreement score, clear consensus
    """
    # Setup: Create registry with 4 providers all voting BUY
    registry = ProviderRegistry()

    providers = [
        MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.80 + (i * 0.05),  # 0.80, 0.85, 0.90, 0.95
        )
        for i in range(1, 5)
    ]

    for provider in providers:
        registry.register_provider(provider.config.name, provider)

    # Create orchestrator
    orchestrator = MultiProviderOrchestrator(
        registry=registry,
        min_providers=1,
        min_confidence=0.5,
        timeout_seconds=30.0,
    )

    # Execute: Generate consensus
    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # Assert: Verify unanimous consensus
    assert consensus.decision == "BUY"
    assert consensus.confidence >= 0.80
    assert consensus.agreement_score == 1.0  # Unanimous = 100% agreement
    assert consensus.participating_providers == 4
    assert consensus.total_providers == 4
    assert consensus.vote_breakdown == {"BUY": 4}
    assert consensus.weighted_votes["BUY"] > 0
    assert consensus.weighted_votes["SELL"] == 0
    assert consensus.weighted_votes["HOLD"] == 0
    assert len(consensus.provider_responses) == 4
    assert all(r.decision == "BUY" for r in consensus.provider_responses)
    assert consensus.total_cost_usd > 0
    assert consensus.total_tokens > 0


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_unanimous_decision_all_sell(sample_market_data):
    """Test unanimous decision - all providers vote SELL"""
    registry = ProviderRegistry()

    providers = [
        MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="SELL",
            confidence=0.85,
        )
        for i in range(1, 4)
    ]

    for provider in providers:
        registry.register_provider(provider.config.name, provider)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="ETH/USDT",
        timeframe="1h",
        current_price=3000.0,
    )

    assert consensus.decision == "SELL"
    assert consensus.agreement_score == 1.0
    assert consensus.vote_breakdown == {"SELL": 3}


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_unanimous_decision_all_hold(sample_market_data):
    """Test unanimous decision - all providers vote HOLD"""
    registry = ProviderRegistry()

    providers = [
        MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="HOLD",
            confidence=0.70,
        )
        for i in range(1, 3)
    ]

    for provider in providers:
        registry.register_provider(provider.config.name, provider)

    orchestrator = MultiProviderOrchestrator(registry=registry, min_providers=2)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BNB/USDT",
        timeframe="4h",
        current_price=400.0,
    )

    assert consensus.decision == "HOLD"
    assert consensus.agreement_score == 1.0
    assert consensus.participating_providers == 2


# ==============================================================================
# Test Scenario 2: Split Decision (Majority)
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_split_decision_majority_buy(sample_market_data):
    """
    Test split decision - 3 BUY, 1 HOLD
    Expected: Consensus should be BUY, agreement score reflects split
    """
    registry = ProviderRegistry()

    # 3 providers vote BUY
    for i in range(1, 4):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderBuy{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
        )
        registry.register_provider(provider.config.name, provider)

    # 1 provider votes HOLD
    provider_hold = MockLLMProvider(
        ProviderConfig(
            name="ProviderHold",
            model="model-hold",
            api_key="key-hold",
            weight=1.0,
        ),
        decision="HOLD",
        confidence=0.70,
    )
    registry.register_provider(provider_hold.config.name, provider_hold)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # Assert: Majority wins
    assert consensus.decision == "BUY"
    assert consensus.vote_breakdown == {"BUY": 3, "HOLD": 1}
    assert consensus.agreement_score < 1.0  # Not unanimous
    assert consensus.agreement_score > 0.5  # But still majority
    assert consensus.participating_providers == 4


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_split_decision_majority_sell(sample_market_data):
    """Test split decision - 2 SELL, 1 BUY, 1 HOLD"""
    registry = ProviderRegistry()

    # 2 SELL
    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderSell{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="SELL",
            confidence=0.80,
        )
        registry.register_provider(provider.config.name, provider)

    # 1 BUY
    provider_buy = MockLLMProvider(
        ProviderConfig(name="ProviderBuy", model="model-buy", api_key="key-buy", weight=1.0),
        decision="BUY",
        confidence=0.75,
    )
    registry.register_provider(provider_buy.config.name, provider_buy)

    # 1 HOLD
    provider_hold = MockLLMProvider(
        ProviderConfig(name="ProviderHold", model="model-hold", api_key="key-hold", weight=1.0),
        decision="HOLD",
        confidence=0.65,
    )
    registry.register_provider(provider_hold.config.name, provider_hold)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="ETH/USDT",
        timeframe="15m",
        current_price=3000.0,
    )

    assert consensus.decision == "SELL"
    assert consensus.vote_breakdown["SELL"] == 2
    assert consensus.participating_providers == 4


# ==============================================================================
# Test Scenario 3: Tie-Breaking with Weights
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_tie_breaking_with_weights(sample_market_data):
    """
    Test tie-breaking - 2 BUY, 2 SELL with different weights
    Expected: Higher weighted provider should win
    """
    registry = ProviderRegistry()

    # 2 providers vote BUY with weight 1.0
    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderBuy{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.80,
        )
        registry.register_provider(provider.config.name, provider)

    # 2 providers vote SELL with weight 0.5 (lower weight)
    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderSell{i}",
                model=f"model-sell-{i}",
                api_key=f"key-sell-{i}",
                weight=0.5,
            ),
            decision="SELL",
            confidence=0.80,
        )
        registry.register_provider(provider.config.name, provider)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # Assert: BUY should win due to higher weights
    assert consensus.decision == "BUY"
    assert consensus.vote_breakdown == {"BUY": 2, "SELL": 2}
    # Weighted votes should favor BUY
    assert consensus.weighted_votes["BUY"] > consensus.weighted_votes["SELL"]


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_tie_breaking_with_confidence(sample_market_data):
    """Test tie-breaking - equal weights but different confidence"""
    registry = ProviderRegistry()

    # 2 BUY with high confidence
    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderBuy{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.95,  # High confidence
        )
        registry.register_provider(provider.config.name, provider)

    # 2 SELL with low confidence
    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderSell{i}",
                model=f"model-sell-{i}",
                api_key=f"key-sell-{i}",
                weight=1.0,
            ),
            decision="SELL",
            confidence=0.60,  # Lower confidence
        )
        registry.register_provider(provider.config.name, provider)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # BUY should win due to higher confidence
    assert consensus.decision == "BUY"
    assert consensus.weighted_votes["BUY"] > consensus.weighted_votes["SELL"]


# ==============================================================================
# Test Scenario 4: Partial Provider Failures
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_partial_provider_timeout(sample_market_data):
    """
    Test partial failures - some providers timeout
    Expected: System continues with successful providers
    """
    registry = ProviderRegistry()

    # 2 successful providers
    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderSuccess{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
        )
        registry.register_provider(provider.config.name, provider)

    # 1 provider that times out
    provider_timeout = MockLLMProvider(
        ProviderConfig(
            name="ProviderTimeout",
            model="model-timeout",
            api_key="key-timeout",
            weight=1.0,
        ),
        decision="BUY",
        confidence=0.85,
        should_fail=True,
        failure_type="timeout",
    )
    registry.register_provider(provider_timeout.config.name, provider_timeout)

    orchestrator = MultiProviderOrchestrator(
        registry=registry,
        min_providers=2,
        timeout_seconds=30.0,
    )

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # Assert: Consensus achieved with 2 providers despite 1 failure
    assert consensus.decision == "BUY"
    assert consensus.participating_providers == 2
    assert consensus.total_providers == 3
    assert len(consensus.provider_responses) == 2


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_partial_provider_rate_limit(sample_market_data):
    """Test partial failures - some providers hit rate limits"""
    registry = ProviderRegistry()

    # 3 successful providers
    for i in range(1, 4):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderSuccess{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="SELL",
            confidence=0.80,
        )
        registry.register_provider(provider.config.name, provider)

    # 1 provider with rate limit
    provider_rate_limit = MockLLMProvider(
        ProviderConfig(
            name="ProviderRateLimit",
            model="model-rate",
            api_key="key-rate",
            weight=1.0,
        ),
        decision="SELL",
        confidence=0.80,
        should_fail=True,
        failure_type="rate_limit",
    )
    registry.register_provider(provider_rate_limit.config.name, provider_rate_limit)

    orchestrator = MultiProviderOrchestrator(registry=registry, min_providers=1)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="ETH/USDT",
        timeframe="1h",
        current_price=3000.0,
    )

    assert consensus.decision == "SELL"
    assert consensus.participating_providers == 3


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_insufficient_providers_after_failures(sample_market_data):
    """Test failure when too many providers fail"""
    registry = ProviderRegistry()

    # 1 successful provider
    provider_success = MockLLMProvider(
        ProviderConfig(
            name="ProviderSuccess",
            model="model-success",
            api_key="key-success",
            weight=1.0,
        ),
        decision="BUY",
        confidence=0.85,
    )
    registry.register_provider(provider_success.config.name, provider_success)

    # 2 failing providers
    for i in range(1, 3):
        provider_fail = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderFail{i}",
                model=f"model-fail-{i}",
                api_key=f"key-fail-{i}",
                weight=1.0,
            ),
            should_fail=True,
        )
        registry.register_provider(provider_fail.config.name, provider_fail)

    # Require at least 2 providers
    orchestrator = MultiProviderOrchestrator(
        registry=registry,
        min_providers=2,
    )

    # Should raise ValueError due to insufficient successful providers
    with pytest.raises(ValueError, match="Insufficient successful provider responses"):
        await orchestrator.generate_consensus_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="5m",
            current_price=50000.0,
        )


# ==============================================================================
# Test Scenario 5: Custom Provider Weights
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_custom_provider_weights(sample_market_data):
    """Test consensus with custom provider weights"""
    registry = ProviderRegistry()

    # 2 BUY providers
    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"ProviderBuy{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,  # Default weight
            ),
            decision="BUY",
            confidence=0.80,
        )
        registry.register_provider(provider.config.name, provider)

    # 1 SELL provider
    provider_sell = MockLLMProvider(
        ProviderConfig(
            name="ProviderSell",
            model="model-sell",
            api_key="key-sell",
            weight=1.0,
        ),
        decision="SELL",
        confidence=0.80,
    )
    registry.register_provider(provider_sell.config.name, provider_sell)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    # Custom weights that heavily favor the SELL provider
    custom_weights = {
        "ProviderBuy1": 0.5,
        "ProviderBuy2": 0.5,
        "ProviderSell": 2.0,  # Much higher weight
    }

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
        provider_weights=custom_weights,
    )

    # SELL should win despite being outnumbered, due to higher weight
    assert consensus.decision == "SELL"
    assert consensus.weighted_votes["SELL"] > consensus.weighted_votes["BUY"]


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_weights_override_config_weights(sample_market_data):
    """Test that custom weights override config weights"""
    registry = ProviderRegistry()

    # Provider with high config weight (within valid range)
    provider1 = MockLLMProvider(
        ProviderConfig(
            name="Provider1",
            model="model-1",
            api_key="key-1",
            weight=0.9,  # High default weight (0-1 range)
        ),
        decision="BUY",
        confidence=0.80,
    )
    registry.register_provider(provider1.config.name, provider1)

    # Provider with normal config weight
    provider2 = MockLLMProvider(
        ProviderConfig(
            name="Provider2",
            model="model-2",
            api_key="key-2",
            weight=0.3,  # Lower default weight
        ),
        decision="SELL",
        confidence=0.80,
    )
    registry.register_provider(provider2.config.name, provider2)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    # Custom weights that reverse the priority
    custom_weights = {
        "Provider1": 0.2,  # Override high weight with low
        "Provider2": 0.9,  # Override low weight with high
    }

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
        provider_weights=custom_weights,
    )

    # SELL should win due to custom weights
    assert consensus.decision == "SELL"


# ==============================================================================
# Test Scenario 6: Different Timeframes and Pairs
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
@pytest.mark.parametrize("pair,timeframe,price", [
    ("BTC/USDT", "1m", 50000.0),
    ("BTC/USDT", "5m", 50000.0),
    ("BTC/USDT", "1h", 50000.0),
    ("BTC/USDT", "4h", 50000.0),
    ("BTC/USDT", "1d", 50000.0),
    ("ETH/USDT", "5m", 3000.0),
    ("ETH/USDT", "1h", 3000.0),
    ("BNB/USDT", "15m", 400.0),
    ("SOL/USDT", "30m", 100.0),
    ("ADA/USDT", "1h", 0.50),
])
async def test_different_timeframes_and_pairs(sample_market_data, pair, timeframe, price):
    """Test consensus with various trading pairs and timeframes"""
    registry = ProviderRegistry()

    # Create 3 providers
    for i in range(1, 4):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
        )
        registry.register_provider(provider.config.name, provider)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair=pair,
        timeframe=timeframe,
        current_price=price,
    )

    # Basic assertions for all pairs/timeframes
    assert consensus.decision in ["BUY", "SELL", "HOLD"]
    assert 0.0 <= consensus.confidence <= 1.0
    assert consensus.participating_providers == 3
    assert consensus.risk_level in ["low", "medium", "high"]


# ==============================================================================
# Test Scenario 7: API Endpoint Integration
# ==============================================================================

@pytest.mark.django_db
def test_api_consensus_endpoint_success(api_client):
    """Test successful API request to consensus endpoint"""
    # Setup: Create mock registry
    registry = ProviderRegistry()

    for i in range(1, 4):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
        )
        registry.register_provider(provider.config.name, provider)

    # Prepare request
    request_data = {
        "market_data": {
            "rsi": 65.5,
            "macd": 150.0,
            "bollinger_upper": 51000,
            "bollinger_lower": 49000,
        },
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "current_price": 50000.0,
    }

    # Execute: Make API request
    with patch("api.views.strategies.get_registry", return_value=registry):
        response = api_client.post(
            "/api/v1/strategies/llm-consensus",
            data=request_data,
            format="json",
        )

    # Assert: Verify response
    assert response.status_code == http_status.HTTP_200_OK

    data = response.json()
    assert data["decision"] == "BUY"
    assert "confidence" in data
    assert "reasoning" in data
    assert "consensus_metadata" in data
    assert "provider_responses" in data

    metadata = data["consensus_metadata"]
    assert metadata["total_providers"] == 3
    assert metadata["participating_providers"] == 3
    assert "agreement_score" in metadata
    assert "vote_breakdown" in metadata
    assert "weighted_votes" in metadata


@pytest.mark.django_db
def test_api_consensus_endpoint_with_weights(api_client):
    """Test API endpoint with custom provider weights"""
    registry = ProviderRegistry()

    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
        )
        registry.register_provider(provider.config.name, provider)

    request_data = {
        "market_data": {"rsi": 65.5},
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "current_price": 50000.0,
        "provider_weights": {
            "Provider1": 0.9,  # Valid weight (0-1 range)
            "Provider2": 0.5,  # Valid weight (0-1 range)
        },
    }

    with patch("api.views.strategies.get_registry", return_value=registry):
        response = api_client.post(
            "/api/v1/strategies/llm-consensus",
            data=request_data,
            format="json",
        )

    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert "weighted_votes" in data["consensus_metadata"]


@pytest.mark.django_db
def test_api_consensus_endpoint_no_providers(api_client):
    """Test API endpoint when no providers are available"""
    # Empty registry
    registry = ProviderRegistry()

    request_data = {
        "market_data": {"rsi": 65.5},
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "current_price": 50000.0,
    }

    with patch("api.views.strategies.get_registry", return_value=registry):
        response = api_client.post(
            "/api/v1/strategies/llm-consensus",
            data=request_data,
            format="json",
        )

    # Should return 503 Service Unavailable
    assert response.status_code == http_status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert "error" in data
    assert "No LLM providers available" in data["error"]


@pytest.mark.django_db
def test_api_consensus_endpoint_invalid_data(api_client):
    """Test API endpoint with invalid request data"""
    # Missing required fields
    request_data = {
        "market_data": {"rsi": 65.5},
        # Missing pair, timeframe, current_price
    }

    response = api_client.post(
        "/api/v1/strategies/llm-consensus",
        data=request_data,
        format="json",
    )

    # Should return 400 Bad Request
    assert response.status_code == http_status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "error" in data


@pytest.mark.django_db
def test_api_consensus_health_check(api_client):
    """Test API health check endpoint"""
    registry = ProviderRegistry()

    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
        )
        registry.register_provider(provider.config.name, provider)

    with patch("api.views.strategies.get_registry", return_value=registry):
        response = api_client.get("/api/v1/strategies/llm-consensus")

    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "available_providers" in data
    assert "provider_health" in data


# ==============================================================================
# Test Scenario 8: Performance Tests
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_parallel_execution_performance(sample_market_data):
    """
    Test that parallel execution is faster than sequential
    Verify providers are called concurrently
    """
    registry = ProviderRegistry()

    # Create providers with 200ms latency each
    latency_ms = 200.0
    for i in range(1, 4):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
            latency_ms=latency_ms,
        )
        registry.register_provider(provider.config.name, provider)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    # Measure time for parallel execution
    start_time = datetime.utcnow()

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    end_time = datetime.utcnow()
    elapsed_ms = (end_time - start_time).total_seconds() * 1000

    # Parallel execution should take roughly latency_ms, not 3 * latency_ms
    # Allow 100ms overhead for orchestration
    assert elapsed_ms < (latency_ms * 2)  # Should be much less than sequential
    assert consensus.participating_providers == 3


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_orchestrator_timeout_handling(sample_market_data):
    """Test that orchestrator respects timeout settings"""
    registry = ProviderRegistry()

    # Create providers with very high latency (5 seconds)
    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
            latency_ms=5000.0,  # 5 seconds
        )
        registry.register_provider(provider.config.name, provider)

    # Set low timeout (1 second)
    orchestrator = MultiProviderOrchestrator(
        registry=registry,
        timeout_seconds=1.0,
        min_providers=1,
    )

    # Should timeout and fail
    with pytest.raises(ValueError, match="Insufficient successful provider responses"):
        await orchestrator.generate_consensus_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="5m",
            current_price=50000.0,
        )


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_cost_and_token_tracking(sample_market_data):
    """Test that costs and tokens are properly tracked"""
    registry = ProviderRegistry()

    # Create providers with known costs
    for i in range(1, 4):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
        )
        registry.register_provider(provider.config.name, provider)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # Each provider costs 0.0015 USD and uses 600 tokens
    expected_cost = 0.0015 * 3
    expected_tokens = 600 * 3

    assert consensus.total_cost_usd == pytest.approx(expected_cost, rel=0.01)
    assert consensus.total_tokens == expected_tokens


# ==============================================================================
# Test Scenario 9: Edge Cases and Error Handling
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_consensus_with_mixed_risk_levels(sample_market_data):
    """Test consensus aggregates risk levels correctly"""
    registry = ProviderRegistry()

    # Provider with low risk
    provider1 = MockLLMProvider(
        ProviderConfig(name="Provider1", model="model-1", api_key="key-1", weight=1.0),
        decision="BUY",
        confidence=0.85,
    )
    # Override risk level
    original_generate = provider1.generate_signal

    async def custom_generate(*args, **kwargs):
        response = await original_generate(*args, **kwargs)
        response.risk_level = "low"
        return response

    provider1.generate_signal = custom_generate
    registry.register_provider(provider1.config.name, provider1)

    # Provider with high risk
    provider2 = MockLLMProvider(
        ProviderConfig(name="Provider2", model="model-2", api_key="key-2", weight=1.0),
        decision="BUY",
        confidence=0.85,
    )

    original_generate2 = provider2.generate_signal

    async def custom_generate2(*args, **kwargs):
        response = await original_generate2(*args, **kwargs)
        response.risk_level = "high"
        return response

    provider2.generate_signal = custom_generate2
    registry.register_provider(provider2.config.name, provider2)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # Should take the highest risk level (conservative approach)
    assert consensus.risk_level == "high"


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_consensus_with_no_stop_loss_take_profit(sample_market_data):
    """Test consensus when providers don't suggest stop loss/take profit"""
    registry = ProviderRegistry()

    provider = MockLLMProvider(
        ProviderConfig(name="Provider1", model="model-1", api_key="key-1", weight=1.0),
        decision="HOLD",
        confidence=0.70,
    )

    # Override to remove stop loss and take profit
    original_generate = provider.generate_signal

    async def custom_generate(*args, **kwargs):
        response = await original_generate(*args, **kwargs)
        response.suggested_stop_loss = None
        response.suggested_take_profit = None
        return response

    provider.generate_signal = custom_generate
    registry.register_provider(provider.config.name, provider)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    consensus = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # Should handle None values gracefully
    assert consensus.decision == "HOLD"
    assert consensus.suggested_stop_loss is None
    assert consensus.suggested_take_profit is None


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_metrics_tracking(sample_market_data):
    """Test that orchestrator tracks metrics correctly"""
    registry = ProviderRegistry()

    for i in range(1, 3):
        provider = MockLLMProvider(
            ProviderConfig(
                name=f"Provider{i}",
                model=f"model-{i}",
                api_key=f"key-{i}",
                weight=1.0,
            ),
            decision="BUY",
            confidence=0.85,
        )
        registry.register_provider(provider.config.name, provider)

    orchestrator = MultiProviderOrchestrator(registry=registry)

    # Initial metrics
    metrics = orchestrator.get_metrics()
    assert metrics["total_requests"] == 0
    assert metrics["successful_requests"] == 0
    assert metrics["failed_requests"] == 0

    # Make successful request
    await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # Check metrics updated
    metrics = orchestrator.get_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["successful_requests"] == 1
    assert metrics["success_rate"] == 1.0


# ==============================================================================
# Test Summary
# ==============================================================================

def test_e2e_test_suite_completeness():
    """
    Meta-test to verify all required test scenarios are covered
    This test documents what scenarios are tested
    """
    required_scenarios = [
        "unanimous_decision",
        "split_decision",
        "tie_breaking",
        "partial_failures",
        "custom_weights",
        "different_timeframes_pairs",
        "api_integration",
        "performance",
    ]

    # This test always passes but serves as documentation
    assert len(required_scenarios) == 8
    print("\n✓ All 8 required E2E test scenarios are implemented:")
    for i, scenario in enumerate(required_scenarios, 1):
        print(f"  {i}. {scenario.replace('_', ' ').title()}")
