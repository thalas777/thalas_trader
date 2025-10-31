#!/usr/bin/env python
"""
Manual test script for consensus API endpoint
Tests the /api/v1/strategies/llm-consensus endpoint with mock providers
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

# Add testserver to ALLOWED_HOSTS
from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from rest_framework.test import APIClient
from llm_service.providers.registry import ProviderRegistry, reset_registry
from llm_service.providers.base import ProviderConfig, ProviderResponse, BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Mock provider for testing"""

    def __init__(self, config: ProviderConfig, decision="BUY", confidence=0.85):
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
            reasoning=f"Mock analysis from {self.config.name}: Market shows {self.test_decision} signal",
            risk_level="medium",
            suggested_stop_loss=current_price * 0.97 if self.test_decision == "BUY" else current_price * 1.03,
            suggested_take_profit=current_price * 1.05 if self.test_decision == "BUY" else current_price * 0.95,
            latency_ms=120.0,
            tokens_used=600,
            cost_usd=0.0015,
        )

    async def health_check(self):
        """Mock health check"""
        return True

    def estimate_cost(self, input_tokens, output_tokens):
        """Mock cost estimation"""
        return 0.0015


def setup_mock_providers():
    """Set up mock providers in the registry"""
    from llm_service.providers.registry import get_registry
    from unittest.mock import patch

    # Reset registry
    reset_registry()

    # Get fresh registry
    registry = get_registry()

    # Create mock providers with different opinions
    provider1 = MockLLMProvider(
        ProviderConfig(
            name="Anthropic-Mock",
            model="claude-3-sonnet",
            api_key="mock-key-1",
            weight=1.0,
        ),
        decision="BUY",
        confidence=0.88,
    )

    provider2 = MockLLMProvider(
        ProviderConfig(
            name="OpenAI-Mock",
            model="gpt-4",
            api_key="mock-key-2",
            weight=1.0,
        ),
        decision="BUY",
        confidence=0.92,
    )

    provider3 = MockLLMProvider(
        ProviderConfig(
            name="Gemini-Mock",
            model="gemini-pro",
            api_key="mock-key-3",
            weight=0.8,
        ),
        decision="HOLD",
        confidence=0.75,
    )

    provider4 = MockLLMProvider(
        ProviderConfig(
            name="Grok-Mock",
            model="grok-1",
            api_key="mock-key-4",
            weight=0.7,
        ),
        decision="BUY",
        confidence=0.80,
    )

    # Register providers
    registry.register_provider("Anthropic-Mock", provider1)
    registry.register_provider("OpenAI-Mock", provider2)
    registry.register_provider("Gemini-Mock", provider3)
    registry.register_provider("Grok-Mock", provider4)

    print("✓ Mock providers registered:")
    print(f"  - Anthropic-Mock: BUY (confidence: 0.88)")
    print(f"  - OpenAI-Mock: BUY (confidence: 0.92)")
    print(f"  - Gemini-Mock: HOLD (confidence: 0.75)")
    print(f"  - Grok-Mock: BUY (confidence: 0.80)")
    print()

    return registry


def test_consensus_endpoint():
    """Test the consensus API endpoint"""
    from unittest.mock import patch

    # Setup mock providers
    registry = setup_mock_providers()

    # Create API client
    client = APIClient()

    # Prepare request data
    request_data = {
        "market_data": {
            "rsi": 65.5,
            "macd": 150.0,
            "bollinger_upper": 51000,
            "bollinger_lower": 49000,
            "volume": 1500000,
        },
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "current_price": 50000.0,
    }

    print("=" * 80)
    print("TESTING CONSENSUS ENDPOINT")
    print("=" * 80)
    print()

    # Test 1: POST request - Generate consensus signal
    print("Test 1: POST /api/v1/strategies/llm-consensus")
    print("-" * 80)

    with patch("api.views.strategies.get_registry", return_value=registry):
        response = client.post(
            "/api/v1/strategies/llm-consensus",
            data=request_data,
            format="json",
        )

    print(f"Status Code: {response.status_code}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("✓ SUCCESS - Consensus signal generated")
        print()
        print(f"Decision: {data['decision']}")
        print(f"Confidence: {data['confidence']:.2f}")
        print(f"Risk Level: {data['risk_level']}")
        print(f"Stop Loss: ${data['suggested_stop_loss']:.2f}" if data.get('suggested_stop_loss') else "Stop Loss: N/A")
        print(f"Take Profit: ${data['suggested_take_profit']:.2f}" if data.get('suggested_take_profit') else "Take Profit: N/A")
        print()
        print("Consensus Metadata:")
        metadata = data['consensus_metadata']
        print(f"  - Total Providers: {metadata['total_providers']}")
        print(f"  - Participating: {metadata['participating_providers']}")
        print(f"  - Agreement Score: {metadata['agreement_score']:.2f}")
        print(f"  - Vote Breakdown: {metadata['vote_breakdown']}")
        print(f"  - Weighted Votes: {json.dumps({k: round(v, 2) for k, v in metadata['weighted_votes'].items()})}")
        print(f"  - Total Latency: {metadata['total_latency_ms']:.0f}ms")
        print(f"  - Total Cost: ${metadata['total_cost_usd']:.6f}")
        print(f"  - Total Tokens: {metadata['total_tokens']}")
        print()
        print("Provider Responses:")
        for resp in data['provider_responses']:
            print(f"  - {resp['provider']}: {resp['decision']} (confidence: {resp['confidence']:.2f})")
    else:
        print("✗ FAILED")
        print(f"Error: {response.json()}")

    print()
    print("=" * 80)

    # Test 2: GET request - Health check
    print("Test 2: GET /api/v1/strategies/llm-consensus (Health Check)")
    print("-" * 80)

    with patch("api.views.strategies.get_registry", return_value=registry):
        response = client.get("/api/v1/strategies/llm-consensus")

    print(f"Status Code: {response.status_code}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("✓ SUCCESS - Health check passed")
        print()
        print(f"Status: {data['status']}")
        print(f"Available Providers: {data['available_providers']}/{data['required_providers']}")
        print(f"Provider Health: {json.dumps(data['provider_health'], indent=2)}")
    else:
        print("✗ FAILED")
        print(f"Error: {response.json()}")

    print()
    print("=" * 80)

    # Test 3: POST with custom weights
    print("Test 3: POST with custom provider weights")
    print("-" * 80)

    request_data_with_weights = {
        **request_data,
        "provider_weights": {
            "Anthropic-Mock": 1.0,
            "OpenAI-Mock": 0.9,
            "Gemini-Mock": 0.5,
            "Grok-Mock": 0.7,
        }
    }

    with patch("api.views.strategies.get_registry", return_value=registry):
        response = client.post(
            "/api/v1/strategies/llm-consensus",
            data=request_data_with_weights,
            format="json",
        )

    print(f"Status Code: {response.status_code}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("✓ SUCCESS - Consensus with custom weights")
        print()
        print(f"Decision: {data['decision']}")
        print(f"Confidence: {data['confidence']:.2f}")
        print(f"Weighted Votes: {json.dumps({k: round(v, 2) for k, v in data['consensus_metadata']['weighted_votes'].items()})}")
    else:
        print("✗ FAILED")
        print(f"Error: {response.json()}")

    print()
    print("=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    test_consensus_endpoint()
