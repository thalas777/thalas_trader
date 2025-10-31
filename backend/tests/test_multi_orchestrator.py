"""
Tests for Multi-Provider Orchestrator
Comprehensive test suite for consensus-based multi-LLM orchestration
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from llm_service.multi_provider_orchestrator import MultiProviderOrchestrator
from llm_service.providers.registry import ProviderRegistry
from llm_service.providers.base import (
    BaseLLMProvider,
    ProviderConfig,
    ProviderResponse,
    ProviderStatus,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthenticationError,
)
from llm_service.consensus.aggregator import ConsensusResult


# Fixtures

@pytest.fixture
def mock_provider_config():
    """Create a mock provider configuration"""
    return ProviderConfig(
        name="test_provider",
        model="test-model",
        api_key="test-key",
        max_tokens=1024,
        temperature=0.7,
        timeout=30,
        max_retries=3,
        weight=1.0,
        enabled=True,
    )


@pytest.fixture
def mock_provider(mock_provider_config):
    """Create a mock provider"""
    provider = Mock(spec=BaseLLMProvider)
    provider.config = mock_provider_config
    provider.status = ProviderStatus.ACTIVE
    provider.is_available = Mock(return_value=True)

    # Mock generate_signal as async
    async def mock_generate_signal(market_data, pair, timeframe, current_price):
        return ProviderResponse(
            provider_name=mock_provider_config.name,
            model=mock_provider_config.model,
            decision="BUY",
            confidence=0.85,
            reasoning="Test reasoning",
            risk_level="medium",
            suggested_stop_loss=45000.0,
            suggested_take_profit=55000.0,
            latency_ms=150.0,
            tokens_used=500,
            cost_usd=0.001,
        )

    provider.generate_signal = AsyncMock(side_effect=mock_generate_signal)

    return provider


@pytest.fixture
def mock_registry():
    """Create a mock registry"""
    registry = Mock(spec=ProviderRegistry)
    registry.get_registry_status = Mock(return_value={
        "total_providers": 3,
        "available_providers": 3,
        "providers_by_status": {"active": 3},
        "provider_names": ["anthropic", "openai", "gemini"],
        "registered_classes": ["anthropic", "openai", "gemini"],
    })
    return registry


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "rsi": 65.5,
        "macd": 150.0,
        "volume": 1000000,
        "price_change_24h": 2.5,
    }


# Test Orchestrator Initialization

def test_orchestrator_initialization(mock_registry):
    """Test orchestrator initialization"""
    orchestrator = MultiProviderOrchestrator(
        registry=mock_registry,
        min_providers=2,
        min_confidence=0.6,
        timeout_seconds=20.0,
    )

    assert orchestrator.registry == mock_registry
    assert orchestrator.min_providers == 2
    assert orchestrator.min_confidence == 0.6
    assert orchestrator.timeout_seconds == 20.0
    assert orchestrator.aggregator is not None


def test_orchestrator_default_initialization(mock_registry):
    """Test orchestrator with default parameters"""
    orchestrator = MultiProviderOrchestrator(registry=mock_registry)

    assert orchestrator.min_providers == 1
    assert orchestrator.min_confidence == 0.5
    assert orchestrator.timeout_seconds == 30.0


# Test Successful Consensus Generation

@pytest.mark.asyncio
async def test_generate_consensus_signal_success(mock_registry, sample_market_data):
    """Test successful consensus signal generation with multiple providers"""
    # Create multiple mock providers
    providers = []
    for i, name in enumerate(["anthropic", "openai", "gemini"]):
        provider = Mock(spec=BaseLLMProvider)
        provider.config = ProviderConfig(
            name=name,
            model=f"model-{i}",
            api_key="test-key",
            weight=1.0,
            enabled=True,
        )
        provider.status = ProviderStatus.ACTIVE
        provider.is_available = Mock(return_value=True)

        # Different decisions for testing consensus
        decisions = ["BUY", "BUY", "HOLD"]

        async def make_generate_signal(market_data, pair, timeframe, current_price, pname=name, dec=decisions[i]):
            return ProviderResponse(
                provider_name=pname,
                model=f"model-{pname}",
                decision=dec,
                confidence=0.8,
                reasoning=f"Reasoning from {pname}",
                risk_level="medium",
                latency_ms=100.0,
                tokens_used=500,
                cost_usd=0.001,
            )

        provider.generate_signal = AsyncMock(side_effect=make_generate_signal)
        providers.append(provider)

    mock_registry.get_available_providers = Mock(return_value=providers)
    mock_registry.get_provider = Mock(side_effect=lambda name: next(
        (p for p in providers if p.config.name == name), None
    ))

    orchestrator = MultiProviderOrchestrator(
        registry=mock_registry,
        min_providers=2,
    )

    result = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    assert isinstance(result, ConsensusResult)
    assert result.decision in ["BUY", "HOLD"]
    assert 0.0 <= result.confidence <= 1.0
    assert result.participating_providers == 3
    assert result.total_providers == 3
    assert result.total_latency_ms > 0
    assert result.total_cost_usd > 0


@pytest.mark.asyncio
async def test_generate_consensus_signal_unanimous(mock_registry, sample_market_data):
    """Test consensus with unanimous decision"""
    # All providers vote BUY
    providers = []
    for name in ["anthropic", "openai", "gemini"]:
        provider = Mock(spec=BaseLLMProvider)
        provider.config = ProviderConfig(
            name=name,
            model=f"model-{name}",
            api_key="test-key",
            weight=1.0,
            enabled=True,
        )
        provider.status = ProviderStatus.ACTIVE
        provider.is_available = Mock(return_value=True)

        async def make_generate_signal(market_data, pair, timeframe, current_price, pname=name):
            return ProviderResponse(
                provider_name=pname,
                model=f"model-{pname}",
                decision="BUY",
                confidence=0.9,
                reasoning=f"Strong buy signal from {pname}",
                risk_level="low",
                latency_ms=100.0,
                tokens_used=500,
                cost_usd=0.001,
            )

        provider.generate_signal = AsyncMock(side_effect=make_generate_signal)
        providers.append(provider)

    mock_registry.get_available_providers = Mock(return_value=providers)
    mock_registry.get_provider = Mock(side_effect=lambda name: next(
        (p for p in providers if p.config.name == name), None
    ))

    orchestrator = MultiProviderOrchestrator(registry=mock_registry)

    result = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    assert result.decision == "BUY"
    assert result.confidence > 0.8  # High confidence due to unanimity
    assert result.agreement_score == 1.0  # Perfect agreement


# Test Error Handling

@pytest.mark.asyncio
async def test_no_available_providers(mock_registry, sample_market_data):
    """Test error when no providers are available"""
    mock_registry.get_available_providers = Mock(return_value=[])

    orchestrator = MultiProviderOrchestrator(registry=mock_registry)

    with pytest.raises(ValueError, match="No available providers"):
        await orchestrator.generate_consensus_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="5m",
            current_price=50000.0,
        )


@pytest.mark.asyncio
async def test_insufficient_available_providers(mock_registry, sample_market_data):
    """Test error when insufficient providers are available"""
    provider = Mock(spec=BaseLLMProvider)
    provider.config = ProviderConfig(
        name="only_provider",
        model="model",
        api_key="key",
        enabled=True,
    )
    provider.status = ProviderStatus.ACTIVE
    provider.is_available = Mock(return_value=True)

    mock_registry.get_available_providers = Mock(return_value=[provider])

    orchestrator = MultiProviderOrchestrator(
        registry=mock_registry,
        min_providers=3,
    )

    with pytest.raises(ValueError, match="Insufficient available providers"):
        await orchestrator.generate_consensus_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="5m",
            current_price=50000.0,
        )


@pytest.mark.asyncio
async def test_partial_provider_failures(mock_registry, sample_market_data):
    """Test handling of partial provider failures"""
    providers = []

    # Provider 1: Success
    provider1 = Mock(spec=BaseLLMProvider)
    provider1.config = ProviderConfig(
        name="provider1",
        model="model1",
        api_key="key",
        weight=1.0,
        enabled=True,
    )
    provider1.status = ProviderStatus.ACTIVE
    provider1.is_available = Mock(return_value=True)

    async def success_generate(market_data, pair, timeframe, current_price):
        return ProviderResponse(
            provider_name="provider1",
            model="model1",
            decision="BUY",
            confidence=0.85,
            reasoning="Good signal",
            risk_level="medium",
            latency_ms=100.0,
            tokens_used=500,
            cost_usd=0.001,
        )

    provider1.generate_signal = success_generate
    providers.append(provider1)

    # Provider 2: Success
    provider2 = Mock(spec=BaseLLMProvider)
    provider2.config = ProviderConfig(
        name="provider2",
        model="model2",
        api_key="key",
        weight=1.0,
        enabled=True,
    )
    provider2.status = ProviderStatus.ACTIVE
    provider2.is_available = Mock(return_value=True)

    async def success_generate2(market_data, pair, timeframe, current_price):
        return ProviderResponse(
            provider_name="provider2",
            model="model2",
            decision="BUY",
            confidence=0.8,
            reasoning="Good signal",
            risk_level="medium",
            latency_ms=100.0,
            tokens_used=500,
            cost_usd=0.001,
        )

    provider2.generate_signal = success_generate2
    providers.append(provider2)

    # Provider 3: Failure
    provider3 = Mock(spec=BaseLLMProvider)
    provider3.config = ProviderConfig(
        name="provider3",
        model="model3",
        api_key="key",
        weight=1.0,
        enabled=True,
    )
    provider3.status = ProviderStatus.ACTIVE
    provider3.is_available = Mock(return_value=True)

    async def failure_generate(market_data, pair, timeframe, current_price):
        raise ProviderTimeoutError("provider3", "Timeout error")

    provider3.generate_signal = failure_generate
    providers.append(provider3)

    mock_registry.get_available_providers = Mock(return_value=providers)
    mock_registry.get_provider = Mock(side_effect=lambda name: next(
        (p for p in providers if p.config.name == name), None
    ))

    orchestrator = MultiProviderOrchestrator(
        registry=mock_registry,
        min_providers=2,
    )

    # Should succeed with 2 successful providers despite 1 failure
    result = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    assert isinstance(result, ConsensusResult)
    assert result.participating_providers == 2
    assert result.total_providers == 3


@pytest.mark.asyncio
async def test_all_providers_fail(mock_registry, sample_market_data):
    """Test error when all providers fail"""
    providers = []

    for name in ["provider1", "provider2"]:
        provider = Mock(spec=BaseLLMProvider)
        provider.config = ProviderConfig(
            name=name,
            model="model",
            api_key="key",
            enabled=True,
        )
        provider.status = ProviderStatus.ACTIVE
        provider.is_available = Mock(return_value=True)

        async def failure_generate(market_data, pair, timeframe, current_price):
            raise ProviderError(name, "API error")

        provider.generate_signal = failure_generate
        providers.append(provider)

    mock_registry.get_available_providers = Mock(return_value=providers)

    orchestrator = MultiProviderOrchestrator(
        registry=mock_registry,
        min_providers=2,
    )

    with pytest.raises(ValueError, match="Insufficient successful provider responses"):
        await orchestrator.generate_consensus_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="5m",
            current_price=50000.0,
        )


# Test Provider Weights

@pytest.mark.asyncio
async def test_custom_provider_weights(mock_registry, sample_market_data):
    """Test consensus with custom provider weights"""
    providers = []

    for name in ["provider1", "provider2"]:
        provider = Mock(spec=BaseLLMProvider)
        provider.config = ProviderConfig(
            name=name,
            model=f"model-{name}",
            api_key="key",
            weight=1.0,
            enabled=True,
        )
        provider.status = ProviderStatus.ACTIVE
        provider.is_available = Mock(return_value=True)

        async def make_generate(market_data, pair, timeframe, current_price, pname=name):
            return ProviderResponse(
                provider_name=pname,
                model=f"model-{pname}",
                decision="BUY",
                confidence=0.8,
                reasoning="Test",
                risk_level="medium",
                latency_ms=100.0,
                tokens_used=500,
                cost_usd=0.001,
            )

        provider.generate_signal = AsyncMock(side_effect=make_generate)
        providers.append(provider)

    mock_registry.get_available_providers = Mock(return_value=providers)
    mock_registry.get_provider = Mock(side_effect=lambda name: next(
        (p for p in providers if p.config.name == name), None
    ))

    orchestrator = MultiProviderOrchestrator(registry=mock_registry)

    # Use custom weights
    custom_weights = {
        "provider1": 0.8,
        "provider2": 0.5,
    }

    result = await orchestrator.generate_consensus_signal(
        market_data=sample_market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
        provider_weights=custom_weights,
    )

    assert isinstance(result, ConsensusResult)
    assert result.weighted_votes["BUY"] > 0


# Test Metrics

def test_get_metrics(mock_registry):
    """Test metrics retrieval"""
    orchestrator = MultiProviderOrchestrator(registry=mock_registry)

    metrics = orchestrator.get_metrics()

    assert "total_requests" in metrics
    assert "successful_requests" in metrics
    assert "failed_requests" in metrics
    assert "success_rate" in metrics
    assert "registry_status" in metrics
    assert "configuration" in metrics
    assert metrics["total_requests"] == 0


def test_reset_metrics(mock_registry):
    """Test metrics reset"""
    orchestrator = MultiProviderOrchestrator(registry=mock_registry)

    orchestrator._total_requests = 10
    orchestrator._successful_requests = 8
    orchestrator._failed_requests = 2

    orchestrator.reset_metrics()

    assert orchestrator._total_requests == 0
    assert orchestrator._successful_requests == 0
    assert orchestrator._failed_requests == 0


# Test Health Check

@pytest.mark.asyncio
async def test_health_check(mock_registry):
    """Test orchestrator health check"""
    mock_registry.health_check_all = AsyncMock(return_value={
        "provider1": True,
        "provider2": True,
        "provider3": False,
    })

    orchestrator = MultiProviderOrchestrator(
        registry=mock_registry,
        min_providers=2,
    )

    health = await orchestrator.health_check()

    assert health["status"] == "healthy"
    assert health["available_providers"] == 2
    assert health["required_providers"] == 2
    assert "provider_health" in health
    assert "timestamp" in health


@pytest.mark.asyncio
async def test_health_check_degraded(mock_registry):
    """Test health check with degraded status"""
    mock_registry.health_check_all = AsyncMock(return_value={
        "provider1": True,
        "provider2": False,
        "provider3": False,
    })

    orchestrator = MultiProviderOrchestrator(
        registry=mock_registry,
        min_providers=2,
    )

    health = await orchestrator.health_check()

    assert health["status"] == "degraded"
    assert health["available_providers"] == 1
    assert health["required_providers"] == 2


# Test Timeout Handling

@pytest.mark.asyncio
async def test_orchestration_timeout(mock_registry, sample_market_data):
    """Test timeout for entire orchestration"""
    provider = Mock(spec=BaseLLMProvider)
    provider.config = ProviderConfig(
        name="slow_provider",
        model="model",
        api_key="key",
        enabled=True,
    )
    provider.status = ProviderStatus.ACTIVE
    provider.is_available = Mock(return_value=True)

    async def slow_generate(market_data, pair, timeframe, current_price):
        await asyncio.sleep(10)  # Simulate slow provider
        return ProviderResponse(
            provider_name="slow_provider",
            model="model",
            decision="BUY",
            confidence=0.8,
            reasoning="Test",
            risk_level="medium",
            latency_ms=10000.0,
            tokens_used=500,
            cost_usd=0.001,
        )

    provider.generate_signal = slow_generate

    mock_registry.get_available_providers = Mock(return_value=[provider])

    orchestrator = MultiProviderOrchestrator(
        registry=mock_registry,
        timeout_seconds=0.5,  # Very short timeout
    )

    with pytest.raises(ValueError, match="Insufficient successful provider responses"):
        await orchestrator.generate_consensus_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="5m",
            current_price=50000.0,
        )


# Test Different Error Types

@pytest.mark.asyncio
async def test_authentication_error_handling(mock_registry, sample_market_data):
    """Test handling of authentication errors"""
    provider = Mock(spec=BaseLLMProvider)
    provider.config = ProviderConfig(
        name="auth_fail_provider",
        model="model",
        api_key="invalid_key",
        enabled=True,
    )
    provider.status = ProviderStatus.ACTIVE
    provider.is_available = Mock(return_value=True)

    async def auth_fail_generate(market_data, pair, timeframe, current_price):
        raise ProviderAuthenticationError("auth_fail_provider", "Invalid API key")

    provider.generate_signal = auth_fail_generate

    mock_registry.get_available_providers = Mock(return_value=[provider])

    orchestrator = MultiProviderOrchestrator(registry=mock_registry)

    with pytest.raises(ValueError, match="Insufficient successful provider responses"):
        await orchestrator.generate_consensus_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="5m",
            current_price=50000.0,
        )


@pytest.mark.asyncio
async def test_rate_limit_error_handling(mock_registry, sample_market_data):
    """Test handling of rate limit errors"""
    provider = Mock(spec=BaseLLMProvider)
    provider.config = ProviderConfig(
        name="rate_limited_provider",
        model="model",
        api_key="key",
        enabled=True,
    )
    provider.status = ProviderStatus.ACTIVE
    provider.is_available = Mock(return_value=True)

    async def rate_limit_generate(market_data, pair, timeframe, current_price):
        raise ProviderRateLimitError("rate_limited_provider", "Rate limit exceeded")

    provider.generate_signal = rate_limit_generate

    mock_registry.get_available_providers = Mock(return_value=[provider])

    orchestrator = MultiProviderOrchestrator(registry=mock_registry)

    with pytest.raises(ValueError, match="Insufficient successful provider responses"):
        await orchestrator.generate_consensus_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="5m",
            current_price=50000.0,
        )
