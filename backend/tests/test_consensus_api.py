"""
Tests for LLM Consensus API Endpoint
Tests the /api/v1/strategies/llm-consensus endpoint
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from rest_framework.test import APIClient
from rest_framework import status as http_status

from llm_service.providers.base import (
    ProviderConfig,
    ProviderResponse,
    BaseLLMProvider,
)
from llm_service.providers.registry import ProviderRegistry
from llm_service.consensus.aggregator import ConsensusResult
from llm_service.multi_provider_orchestrator import MultiProviderOrchestrator


class MockProvider(BaseLLMProvider):
    """Mock LLM provider for testing"""

    def __init__(self, config: ProviderConfig, decision: str = "BUY", confidence: float = 0.85):
        super().__init__(config)
        self.test_decision = decision
        self.test_confidence = confidence

    async def generate_signal(self, market_data, pair, timeframe, current_price):
        """Generate mock signal"""
        return ProviderResponse(
            provider_name=self.config.name,
            model=self.config.model,
            decision=self.test_decision,
            confidence=self.test_confidence,
            reasoning=f"Mock reasoning from {self.config.name}",
            risk_level="medium",
            suggested_stop_loss=current_price * 0.97,
            suggested_take_profit=current_price * 1.05,
            latency_ms=100.0,
            tokens_used=500,
            cost_usd=0.001,
        )

    async def health_check(self):
        """Mock health check"""
        return True

    def estimate_cost(self, input_tokens, output_tokens):
        """Mock cost estimation"""
        return 0.001


@pytest.fixture
def api_client():
    """Fixture for Django REST API client"""
    return APIClient()


@pytest.fixture
def mock_registry():
    """Fixture for mock provider registry"""
    registry = ProviderRegistry()

    # Create mock providers
    provider1 = MockProvider(
        ProviderConfig(
            name="MockProvider1",
            model="mock-model-1",
            api_key="test-key-1",
            weight=1.0,
        ),
        decision="BUY",
        confidence=0.85,
    )

    provider2 = MockProvider(
        ProviderConfig(
            name="MockProvider2",
            model="mock-model-2",
            api_key="test-key-2",
            weight=1.0,
        ),
        decision="BUY",
        confidence=0.90,
    )

    provider3 = MockProvider(
        ProviderConfig(
            name="MockProvider3",
            model="mock-model-3",
            api_key="test-key-3",
            weight=0.8,
        ),
        decision="HOLD",
        confidence=0.75,
    )

    # Register providers
    registry.register_provider("MockProvider1", provider1)
    registry.register_provider("MockProvider2", provider2)
    registry.register_provider("MockProvider3", provider3)

    return registry


@pytest.fixture
def sample_request_data():
    """Fixture for sample API request data"""
    return {
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


@pytest.mark.django_db
class TestConsensusAPIEndpoint:
    """Test suite for consensus API endpoint"""

    def test_consensus_endpoint_success(self, api_client, mock_registry, sample_request_data):
        """Test successful consensus signal generation"""
        with patch("api.views.strategies.get_registry", return_value=mock_registry):
            response = api_client.post(
                "/api/v1/strategies/llm-consensus",
                data=sample_request_data,
                format="json",
            )

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "decision" in data
        assert "confidence" in data
        assert "reasoning" in data
        assert "risk_level" in data
        assert "consensus_metadata" in data
        assert "provider_responses" in data

        # Verify consensus metadata
        metadata = data["consensus_metadata"]
        assert metadata["total_providers"] == 3
        assert metadata["participating_providers"] == 3
        assert "agreement_score" in metadata
        assert "weighted_confidence" in metadata
        assert "vote_breakdown" in metadata
        assert "weighted_votes" in metadata
        assert "total_latency_ms" in metadata
        assert "total_cost_usd" in metadata
        assert "total_tokens" in metadata
        assert "timestamp" in metadata

        # Verify provider responses
        assert len(data["provider_responses"]) == 3
        for provider_resp in data["provider_responses"]:
            assert "provider" in provider_resp
            assert "decision" in provider_resp
            assert "confidence" in provider_resp
            assert "reasoning" in provider_resp

    def test_consensus_endpoint_with_weights(self, api_client, mock_registry, sample_request_data):
        """Test consensus with custom provider weights"""
        request_data = {
            **sample_request_data,
            "provider_weights": {
                "MockProvider1": 1.0,
                "MockProvider2": 0.9,
                "MockProvider3": 0.5,
            }
        }

        with patch("api.views.strategies.get_registry", return_value=mock_registry):
            response = api_client.post(
                "/api/v1/strategies/llm-consensus",
                data=request_data,
                format="json",
            )

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data["decision"] in ["BUY", "SELL", "HOLD"]

    def test_consensus_endpoint_no_providers(self, api_client, sample_request_data):
        """Test endpoint when no providers are available"""
        empty_registry = ProviderRegistry()

        with patch("api.views.strategies.get_registry", return_value=empty_registry):
            response = api_client.post(
                "/api/v1/strategies/llm-consensus",
                data=sample_request_data,
                format="json",
            )

        assert response.status_code == http_status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "error" in data
        assert "No LLM providers available" in data["error"]

    def test_consensus_endpoint_invalid_request(self, api_client):
        """Test endpoint with invalid request data"""
        invalid_data = {
            "pair": "BTC/USDT",
            # Missing required fields: market_data, current_price
        }

        response = api_client.post(
            "/api/v1/strategies/llm-consensus",
            data=invalid_data,
            format="json",
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert "details" in data

    def test_consensus_endpoint_invalid_timeframe(self, api_client, sample_request_data):
        """Test endpoint with invalid timeframe"""
        invalid_data = {
            **sample_request_data,
            "timeframe": "invalid",
        }

        response = api_client.post(
            "/api/v1/strategies/llm-consensus",
            data=invalid_data,
            format="json",
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_consensus_endpoint_invalid_weights(self, api_client, sample_request_data):
        """Test endpoint with invalid provider weights"""
        invalid_data = {
            **sample_request_data,
            "provider_weights": {
                "MockProvider1": 1.5,  # Invalid: > 1.0
            }
        }

        response = api_client.post(
            "/api/v1/strategies/llm-consensus",
            data=invalid_data,
            format="json",
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_consensus_health_check(self, api_client, mock_registry):
        """Test GET endpoint for health check"""
        with patch("api.views.strategies.get_registry", return_value=mock_registry):
            response = api_client.get("/api/v1/strategies/llm-consensus")

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()

        # Verify health check response
        assert "status" in data
        assert "available_providers" in data
        assert "required_providers" in data
        assert "provider_health" in data
        assert "metrics" in data

    def test_consensus_health_check_no_providers(self, api_client):
        """Test health check when no providers are available"""
        empty_registry = ProviderRegistry()

        with patch("api.views.strategies.get_registry", return_value=empty_registry):
            response = api_client.get("/api/v1/strategies/llm-consensus")

        # Should return 200 OK with degraded status
        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "degraded"
        assert data["available_providers"] == 0


@pytest.mark.asyncio
async def test_consensus_endpoint_integration():
    """Integration test for consensus endpoint logic"""
    # Create mock registry
    registry = ProviderRegistry()

    provider1 = MockProvider(
        ProviderConfig(name="Test1", model="model1", api_key="key1"),
        decision="BUY",
        confidence=0.85,
    )
    provider2 = MockProvider(
        ProviderConfig(name="Test2", model="model2", api_key="key2"),
        decision="BUY",
        confidence=0.90,
    )

    registry.register_provider("Test1", provider1)
    registry.register_provider("Test2", provider2)

    # Create orchestrator
    orchestrator = MultiProviderOrchestrator(
        registry=registry,
        min_providers=1,
        min_confidence=0.5,
        timeout_seconds=30.0,
    )

    # Generate consensus
    consensus = await orchestrator.generate_consensus_signal(
        market_data={"rsi": 65.5},
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
    )

    # Verify consensus result
    assert isinstance(consensus, ConsensusResult)
    assert consensus.decision == "BUY"
    assert consensus.confidence > 0
    assert len(consensus.provider_responses) == 2
    assert consensus.total_providers == 2
    assert consensus.participating_providers == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
