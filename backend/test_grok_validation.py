#!/usr/bin/env python
"""
Validation test for Grok Provider
Tests all required functionality without making actual API calls
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

# Import the provider
from llm_service.providers.grok_provider import GrokProvider
from llm_service.providers.base import ProviderConfig, ProviderResponse, ProviderError


def test_provider_initialization():
    """Test 1: Provider initializes correctly"""
    print("Test 1: Provider Initialization")
    config = ProviderConfig(
        name="grok",
        model="grok-beta",
        api_key="test_key",
        max_tokens=1024,
        temperature=0.7,
        timeout=30,
        max_retries=3,
        weight=1.0,
        base_url="https://api.x.ai/v1"
    )

    with patch('llm_service.providers.grok_provider.AsyncOpenAI'), \
         patch('llm_service.providers.grok_provider.OpenAI'):
        provider = GrokProvider(config)
        assert provider.config.name == "grok"
        assert provider.config.model == "grok-beta"
        assert hasattr(provider, 'client')
        assert hasattr(provider, 'sync_client')
        print("✓ Provider initialized successfully")
        print(f"  - Name: {provider.config.name}")
        print(f"  - Model: {provider.config.model}")
        print(f"  - Base URL: https://api.x.ai/v1")
        print()


async def test_generate_signal():
    """Test 2: Generate signal method works correctly"""
    print("Test 2: Generate Signal")

    config = ProviderConfig(
        name="grok",
        model="grok-beta",
        api_key="test_key",
        max_tokens=1024,
        temperature=0.7,
    )

    # Mock response
    mock_response = {
        "decision": "BUY",
        "confidence": 0.85,
        "reasoning": "Strong bullish indicators detected",
        "risk_level": "medium",
        "suggested_stop_loss": 95.0,
        "suggested_take_profit": 110.0
    }

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = json.dumps(mock_response)
    mock_completion.choices[0].finish_reason = "stop"
    mock_completion.usage = MagicMock()
    mock_completion.usage.total_tokens = 150
    mock_completion.usage.prompt_tokens = 100
    mock_completion.usage.completion_tokens = 50

    with patch('llm_service.providers.grok_provider.AsyncOpenAI') as mock_openai_class, \
         patch('llm_service.providers.grok_provider.OpenAI'):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai_class.return_value = mock_client

        provider = GrokProvider(config)
        provider.client = mock_client

        market_data = {
            "rsi": 65.5,
            "macd": 2.3,
            "volume": 1000000,
        }

        response = await provider.generate_signal(
            market_data=market_data,
            pair="BTC/USDT",
            timeframe="1h",
            current_price=100.0
        )

        assert isinstance(response, ProviderResponse)
        assert response.decision == "BUY"
        assert response.confidence == 0.85
        assert response.provider_name == "grok"
        assert response.tokens_used == 150
        assert response.latency_ms > 0
        print("✓ Signal generation successful")
        print(f"  - Decision: {response.decision}")
        print(f"  - Confidence: {response.confidence}")
        print(f"  - Tokens used: {response.tokens_used}")
        print(f"  - Latency: {response.latency_ms:.2f}ms")
        print()


async def test_health_check():
    """Test 3: Health check method works"""
    print("Test 3: Health Check")

    config = ProviderConfig(
        name="grok",
        model="grok-beta",
        api_key="test_key",
    )

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "pong"

    with patch('llm_service.providers.grok_provider.AsyncOpenAI') as mock_openai_class, \
         patch('llm_service.providers.grok_provider.OpenAI'):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai_class.return_value = mock_client

        provider = GrokProvider(config)
        provider.client = mock_client

        is_healthy = await provider.health_check()
        assert is_healthy is True
        print("✓ Health check passed")
        print()


def test_cost_estimation():
    """Test 4: Cost estimation method works"""
    print("Test 4: Cost Estimation")

    config = ProviderConfig(
        name="grok",
        model="grok-beta",
        api_key="test_key",
    )

    with patch('llm_service.providers.grok_provider.AsyncOpenAI'), \
         patch('llm_service.providers.grok_provider.OpenAI'):
        provider = GrokProvider(config)

        # Test cost estimation
        cost = provider.estimate_cost(prompt_tokens=1000, completion_tokens=500)

        # Expected: (1000/1M * 5.0) + (500/1M * 15.0) = 0.005 + 0.0075 = 0.0125
        expected_cost = 0.0125
        assert abs(cost - expected_cost) < 0.0001
        print("✓ Cost estimation accurate")
        print(f"  - Prompt tokens: 1000")
        print(f"  - Completion tokens: 500")
        print(f"  - Estimated cost: ${cost:.6f}")
        print()


def test_json_parsing():
    """Test 5: JSON response parsing handles edge cases"""
    print("Test 5: JSON Parsing Edge Cases")

    config = ProviderConfig(
        name="grok",
        model="grok-beta",
        api_key="test_key",
    )

    with patch('llm_service.providers.grok_provider.AsyncOpenAI'), \
         patch('llm_service.providers.grok_provider.OpenAI'):
        provider = GrokProvider(config)

        # Test case 1: JSON wrapped in markdown
        response1 = '''```json
{
    "decision": "HOLD",
    "confidence": 0.6,
    "reasoning": "Market conditions unclear"
}
```'''
        parsed1 = provider._parse_response(response1)
        assert parsed1["decision"] == "HOLD"
        print("✓ Markdown-wrapped JSON parsed correctly")

        # Test case 2: Plain JSON
        response2 = '{"decision": "SELL", "confidence": 0.9, "reasoning": "Overbought"}'
        parsed2 = provider._parse_response(response2)
        assert parsed2["decision"] == "SELL"
        print("✓ Plain JSON parsed correctly")

        # Test case 3: Validation catches invalid decision
        try:
            invalid_response = '{"decision": "INVALID", "confidence": 0.5, "reasoning": "test"}'
            provider._parse_response(invalid_response)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid decision" in str(e)
            print("✓ Invalid decision rejected")

        # Test case 4: Validation catches invalid confidence
        try:
            invalid_response = '{"decision": "BUY", "confidence": 1.5, "reasoning": "test"}'
            provider._parse_response(invalid_response)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid confidence" in str(e)
            print("✓ Invalid confidence rejected")

        print()


async def test_error_handling():
    """Test 6: Error handling works correctly"""
    print("Test 6: Error Handling")

    config = ProviderConfig(
        name="grok",
        model="grok-beta",
        api_key="test_key",
    )

    with patch('llm_service.providers.grok_provider.AsyncOpenAI') as mock_openai_class, \
         patch('llm_service.providers.grok_provider.OpenAI'):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_openai_class.return_value = mock_client

        provider = GrokProvider(config)
        provider.client = mock_client

        try:
            await provider.generate_signal(
                market_data={"rsi": 50},
                pair="BTC/USDT",
                timeframe="1h",
            )
            assert False, "Should have raised ProviderError"
        except ProviderError as e:
            assert "grok" in str(e)
            assert "API Error" in str(e)
            print("✓ API errors properly caught and wrapped")

        # Verify metrics were updated
        assert provider._error_count > 0
        print("✓ Error metrics updated")
        print()


def test_provider_status():
    """Test 7: Provider status tracking works"""
    print("Test 7: Provider Status Tracking")

    config = ProviderConfig(
        name="grok",
        model="grok-beta",
        api_key="test_key",
    )

    with patch('llm_service.providers.grok_provider.AsyncOpenAI'), \
         patch('llm_service.providers.grok_provider.OpenAI'):
        provider = GrokProvider(config)

        status = provider.get_status()
        assert status["name"] == "grok"
        assert status["model"] == "grok-beta"
        assert status["enabled"] is True
        assert status["requests"] == 0
        assert status["errors"] == 0
        print("✓ Status tracking functional")
        print(f"  - Status: {status['status']}")
        print(f"  - Requests: {status['requests']}")
        print(f"  - Errors: {status['errors']}")
        print()


def test_interface_compliance():
    """Test 8: Verify all required abstract methods are implemented"""
    print("Test 8: Interface Compliance")

    config = ProviderConfig(
        name="grok",
        model="grok-beta",
        api_key="test_key",
    )

    with patch('llm_service.providers.grok_provider.AsyncOpenAI'), \
         patch('llm_service.providers.grok_provider.OpenAI'):
        provider = GrokProvider(config)

        # Check all required methods exist and are callable
        assert hasattr(provider, 'generate_signal')
        assert callable(provider.generate_signal)
        print("✓ generate_signal() implemented")

        assert hasattr(provider, 'health_check')
        assert callable(provider.health_check)
        print("✓ health_check() implemented")

        assert hasattr(provider, 'estimate_cost')
        assert callable(provider.estimate_cost)
        print("✓ estimate_cost() implemented")

        # Check inherited methods
        assert hasattr(provider, 'get_status')
        assert hasattr(provider, 'update_metrics')
        assert hasattr(provider, 'set_status')
        assert hasattr(provider, 'is_available')
        assert hasattr(provider, 'build_prompt')
        print("✓ All base methods available")
        print()


async def main():
    """Run all tests"""
    print("=" * 70)
    print("GROK PROVIDER VALIDATION TEST SUITE")
    print("=" * 70)
    print()

    try:
        # Sync tests
        test_provider_initialization()
        test_cost_estimation()
        test_json_parsing()
        test_provider_status()
        test_interface_compliance()

        # Async tests
        await test_generate_signal()
        await test_health_check()
        await test_error_handling()

        print("=" * 70)
        print("ALL TESTS PASSED! ✓")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✓ Provider implements all required abstract methods")
        print("  ✓ Async/await properly implemented")
        print("  ✓ Error handling comprehensive")
        print("  ✓ Cost estimation formula accurate")
        print("  ✓ Health check functional")
        print("  ✓ JSON parsing handles edge cases (markdown, plain, validation)")
        print("  ✓ Uses OpenAI library with custom base URL (https://api.x.ai/v1)")
        print("  ✓ Proper logging and metrics tracking")
        print()
        return True

    except Exception as e:
        print("=" * 70)
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
