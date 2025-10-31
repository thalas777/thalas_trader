"""
Comprehensive Unit Tests for LLM Providers
Tests all 4 providers: Anthropic, OpenAI, Gemini, Grok
Mock external API calls and test success/failure scenarios
"""
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

from llm_service.providers.base import (
    BaseLLMProvider,
    ProviderConfig,
    ProviderResponse,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthenticationError,
    ProviderStatus,
)
from llm_service.providers.anthropic_provider import AnthropicProvider
from llm_service.providers.openai_provider import OpenAIProvider
from llm_service.providers.gemini_provider import GeminiProvider
from llm_service.providers.grok_provider import GrokProvider


# ==================== FIXTURES ====================

@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "rsi": 65.5,
        "macd": 0.05,
        "bb_upper": 50000,
        "bb_lower": 48000,
        "volume": 1500000,
        "recent_candles": [
            {"open": 49000, "high": 49500, "low": 48800, "close": 49200},
            {"open": 49200, "high": 49800, "low": 49100, "close": 49600},
        ]
    }


@pytest.fixture
def anthropic_config():
    """Anthropic provider configuration"""
    return ProviderConfig(
        name="anthropic",
        model="claude-3-5-sonnet-20241022",
        api_key="test_anthropic_key",
        max_tokens=1024,
        temperature=0.7,
        timeout=30,
        max_retries=3,
        weight=1.0,
        enabled=True,
    )


@pytest.fixture
def openai_config():
    """OpenAI provider configuration"""
    return ProviderConfig(
        name="openai",
        model="gpt-4-turbo",
        api_key="test_openai_key",
        max_tokens=1024,
        temperature=0.7,
        timeout=30,
        max_retries=3,
        weight=1.0,
        enabled=True,
    )


@pytest.fixture
def gemini_config():
    """Gemini provider configuration"""
    return ProviderConfig(
        name="gemini",
        model="gemini-1.5-pro",
        api_key="test_gemini_key",
        max_tokens=1024,
        temperature=0.7,
        timeout=30,
        max_retries=3,
        weight=0.8,
        enabled=True,
    )


@pytest.fixture
def grok_config():
    """Grok provider configuration"""
    return ProviderConfig(
        name="grok",
        model="grok-beta",
        api_key="test_grok_key",
        max_tokens=1024,
        temperature=0.7,
        timeout=30,
        max_retries=3,
        weight=0.7,
        enabled=True,
        base_url="https://api.x.ai/v1",
    )


@pytest.fixture
def valid_json_response():
    """Valid JSON response from LLM"""
    return {
        "decision": "BUY",
        "confidence": 0.85,
        "reasoning": "Strong bullish indicators with RSI showing momentum",
        "risk_level": "medium",
        "suggested_stop_loss": 48000.0,
        "suggested_take_profit": 51000.0
    }


@pytest.fixture
def valid_json_response_markdown():
    """Valid JSON response wrapped in markdown code blocks"""
    return """```json
{
    "decision": "SELL",
    "confidence": 0.72,
    "reasoning": "Market showing signs of exhaustion",
    "risk_level": "low"
}
```"""


# ==================== ANTHROPIC PROVIDER TESTS ====================

@pytest.mark.asyncio
async def test_anthropic_generate_signal_success(anthropic_config, sample_market_data, valid_json_response):
    """Test successful signal generation with Anthropic"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        # Mock the API response
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(valid_json_response))]
        mock_response.usage = Mock(input_tokens=500, output_tokens=200)
        mock_response.stop_reason = "end_turn"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        # Create provider and generate signal
        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client  # Use mocked client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h",
            current_price=49500.0
        )

        # Assertions
        assert isinstance(response, ProviderResponse)
        assert response.provider_name == "anthropic"
        assert response.decision == "BUY"
        assert response.confidence == 0.85
        assert response.reasoning == "Strong bullish indicators with RSI showing momentum"
        assert response.risk_level == "medium"
        assert response.suggested_stop_loss == 48000.0
        assert response.suggested_take_profit == 51000.0
        assert response.tokens_used == 700
        assert response.cost_usd > 0
        assert response.latency_ms > 0


@pytest.mark.asyncio
async def test_anthropic_generate_signal_markdown_wrapped(anthropic_config, sample_market_data, valid_json_response_markdown):
    """Test Anthropic parsing markdown-wrapped JSON"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        mock_response = Mock()
        mock_response.content = [Mock(text=valid_json_response_markdown)]
        mock_response.usage = Mock(input_tokens=500, output_tokens=200)
        mock_response.stop_reason = "end_turn"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h",
            current_price=49500.0
        )

        assert response.decision == "SELL"
        assert response.confidence == 0.72


@pytest.mark.asyncio
async def test_anthropic_generate_signal_invalid_json(anthropic_config, sample_market_data):
    """Test Anthropic handling invalid JSON response"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        mock_response = Mock()
        mock_response.content = [Mock(text="This is not JSON at all!")]
        mock_response.usage = Mock(input_tokens=500, output_tokens=200)

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        with pytest.raises(ProviderError) as exc_info:
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )

        # Error message includes retry logic information
        assert "Could not extract valid JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_anthropic_generate_signal_missing_fields(anthropic_config, sample_market_data):
    """Test Anthropic handling response with missing required fields"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        incomplete_response = {"decision": "BUY"}  # Missing confidence and reasoning

        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(incomplete_response))]
        mock_response.usage = Mock(input_tokens=500, output_tokens=200)

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        with pytest.raises(ProviderError):
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )


@pytest.mark.asyncio
async def test_anthropic_health_check_success(anthropic_config):
    """Test Anthropic health check success"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        mock_response = Mock()
        mock_response.content = [Mock(text="pong")]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        result = await provider.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_anthropic_health_check_failure(anthropic_config):
    """Test Anthropic health check failure"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        result = await provider.health_check()
        assert result is False


def test_anthropic_estimate_cost(anthropic_config):
    """Test Anthropic cost estimation"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(anthropic_config)

        # Test with claude-3-5-sonnet pricing: $3/M input, $15/M output
        cost = provider.estimate_cost(prompt_tokens=1000, completion_tokens=500)
        expected_cost = (1000 / 1_000_000 * 3.0) + (500 / 1_000_000 * 15.0)
        assert abs(cost - expected_cost) < 0.0001


# ==================== OPENAI PROVIDER TESTS ====================

@pytest.mark.asyncio
async def test_openai_generate_signal_success(openai_config, sample_market_data, valid_json_response):
    """Test successful signal generation with OpenAI"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI') as mock_openai:
        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps(valid_json_response)), finish_reason="stop")]
        mock_response.usage = Mock(prompt_tokens=500, completion_tokens=200, total_tokens=700)

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        provider.client = mock_client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="ETH/USDT",
            timeframe="5m",
            current_price=3200.0
        )

        assert isinstance(response, ProviderResponse)
        assert response.provider_name == "openai"
        assert response.decision == "BUY"
        assert response.confidence == 0.85
        assert response.tokens_used == 700
        assert response.cost_usd > 0


@pytest.mark.asyncio
async def test_openai_generate_signal_markdown_wrapped(openai_config, sample_market_data, valid_json_response_markdown):
    """Test OpenAI parsing markdown-wrapped JSON"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI') as mock_openai:
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=valid_json_response_markdown), finish_reason="stop")]
        mock_response.usage = Mock(prompt_tokens=500, completion_tokens=200, total_tokens=700)

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        provider.client = mock_client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h"
        )

        assert response.decision == "SELL"
        assert response.confidence == 0.72


@pytest.mark.asyncio
async def test_openai_health_check_success(openai_config):
    """Test OpenAI health check success"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI') as mock_openai:
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="pong"))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        provider.client = mock_client

        result = await provider.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_openai_health_check_failure(openai_config):
    """Test OpenAI health check failure"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        provider.client = mock_client

        result = await provider.health_check()
        assert result is False


def test_openai_estimate_cost(openai_config):
    """Test OpenAI cost estimation"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI'):
        provider = OpenAIProvider(openai_config)

        # Test with gpt-4-turbo pricing: $10/M input, $30/M output
        cost = provider.estimate_cost(prompt_tokens=1000, completion_tokens=500)
        expected_cost = (1000 / 1_000_000 * 10.0) + (500 / 1_000_000 * 30.0)
        assert abs(cost - expected_cost) < 0.0001


# ==================== GEMINI PROVIDER TESTS ====================

@pytest.mark.asyncio
async def test_gemini_generate_signal_success(gemini_config, sample_market_data, valid_json_response):
    """Test successful signal generation with Gemini"""
    with patch('llm_service.providers.gemini_provider.genai') as mock_genai:
        # Mock the API response
        mock_response = Mock()
        mock_response.text = json.dumps(valid_json_response)
        mock_response.finish_reason = "STOP"

        mock_model = Mock()
        mock_model.generate_content = Mock(return_value=mock_response)

        mock_genai.configure = Mock()
        mock_genai.GenerativeModel = Mock(return_value=mock_model)

        provider = GeminiProvider(gemini_config)

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h",
            current_price=49500.0
        )

        assert isinstance(response, ProviderResponse)
        assert response.provider_name == "gemini"
        assert response.decision == "BUY"
        assert response.confidence == 0.85
        assert response.cost_usd > 0


@pytest.mark.asyncio
async def test_gemini_generate_signal_markdown_wrapped(gemini_config, sample_market_data, valid_json_response_markdown):
    """Test Gemini parsing markdown-wrapped JSON"""
    with patch('llm_service.providers.gemini_provider.genai') as mock_genai:
        mock_response = Mock()
        mock_response.text = valid_json_response_markdown

        mock_model = Mock()
        mock_model.generate_content = Mock(return_value=mock_response)

        mock_genai.configure = Mock()
        mock_genai.GenerativeModel = Mock(return_value=mock_model)

        provider = GeminiProvider(gemini_config)

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h"
        )

        assert response.decision == "SELL"
        assert response.confidence == 0.72


@pytest.mark.asyncio
async def test_gemini_generate_signal_invalid_json(gemini_config, sample_market_data):
    """Test Gemini handling invalid JSON response"""
    with patch('llm_service.providers.gemini_provider.genai') as mock_genai:
        mock_response = Mock()
        mock_response.text = "Not valid JSON!"

        mock_model = Mock()
        mock_model.generate_content = Mock(return_value=mock_response)

        mock_genai.configure = Mock()
        mock_genai.GenerativeModel = Mock(return_value=mock_model)

        provider = GeminiProvider(gemini_config)

        with pytest.raises(ProviderError) as exc_info:
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )

        assert "Failed to parse Gemini response as JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_health_check_success(gemini_config):
    """Test Gemini health check success"""
    with patch('llm_service.providers.gemini_provider.genai') as mock_genai:
        mock_response = Mock()
        mock_response.text = "pong"

        mock_model = Mock()
        mock_model.generate_content = Mock(return_value=mock_response)

        mock_genai.configure = Mock()
        mock_genai.GenerativeModel = Mock(return_value=mock_model)

        provider = GeminiProvider(gemini_config)

        result = await provider.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_gemini_health_check_failure(gemini_config):
    """Test Gemini health check failure"""
    with patch('llm_service.providers.gemini_provider.genai') as mock_genai:
        mock_model = Mock()
        mock_model.generate_content = Mock(side_effect=Exception("API Error"))

        mock_genai.configure = Mock()
        mock_genai.GenerativeModel = Mock(return_value=mock_model)

        provider = GeminiProvider(gemini_config)

        result = await provider.health_check()
        assert result is False


def test_gemini_estimate_cost(gemini_config):
    """Test Gemini cost estimation"""
    with patch('llm_service.providers.gemini_provider.genai'):
        provider = GeminiProvider(gemini_config)

        # Test with gemini-1.5-pro pricing: $3.5/M input, $10.5/M output
        cost = provider.estimate_cost(prompt_tokens=1000, completion_tokens=500)
        expected_cost = (1000 / 1_000_000 * 3.5) + (500 / 1_000_000 * 10.5)
        assert abs(cost - expected_cost) < 0.0001


# ==================== GROK PROVIDER TESTS ====================

@pytest.mark.asyncio
async def test_grok_generate_signal_success(grok_config, sample_market_data, valid_json_response):
    """Test successful signal generation with Grok"""
    with patch('llm_service.providers.grok_provider.AsyncOpenAI') as mock_openai:
        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps(valid_json_response)), finish_reason="stop")]
        mock_response.usage = Mock(prompt_tokens=500, completion_tokens=200, total_tokens=700)

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = GrokProvider(grok_config)
        provider.client = mock_client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h",
            current_price=49500.0
        )

        assert isinstance(response, ProviderResponse)
        assert response.provider_name == "grok"
        assert response.decision == "BUY"
        assert response.confidence == 0.85
        assert response.tokens_used == 700
        assert response.cost_usd > 0


@pytest.mark.asyncio
async def test_grok_generate_signal_markdown_wrapped(grok_config, sample_market_data, valid_json_response_markdown):
    """Test Grok parsing markdown-wrapped JSON"""
    with patch('llm_service.providers.grok_provider.AsyncOpenAI') as mock_openai:
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=valid_json_response_markdown), finish_reason="stop")]
        mock_response.usage = Mock(prompt_tokens=500, completion_tokens=200, total_tokens=700)

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = GrokProvider(grok_config)
        provider.client = mock_client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h"
        )

        assert response.decision == "SELL"
        assert response.confidence == 0.72


@pytest.mark.asyncio
async def test_grok_health_check_success(grok_config):
    """Test Grok health check success"""
    with patch('llm_service.providers.grok_provider.AsyncOpenAI') as mock_openai:
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="pong"))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = GrokProvider(grok_config)
        provider.client = mock_client

        result = await provider.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_grok_health_check_failure(grok_config):
    """Test Grok health check failure"""
    with patch('llm_service.providers.grok_provider.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_openai.return_value = mock_client

        provider = GrokProvider(grok_config)
        provider.client = mock_client

        result = await provider.health_check()
        assert result is False


def test_grok_estimate_cost(grok_config):
    """Test Grok cost estimation"""
    with patch('llm_service.providers.grok_provider.AsyncOpenAI'):
        provider = GrokProvider(grok_config)

        # Test with grok-beta pricing: $5/M input, $15/M output
        cost = provider.estimate_cost(prompt_tokens=1000, completion_tokens=500)
        expected_cost = (1000 / 1_000_000 * 5.0) + (500 / 1_000_000 * 15.0)
        assert abs(cost - expected_cost) < 0.0001


# ==================== EDGE CASE TESTS ====================

@pytest.mark.asyncio
async def test_all_providers_invalid_decision(anthropic_config, sample_market_data):
    """Test all providers reject invalid decision values"""
    invalid_response = {
        "decision": "MAYBE",  # Invalid decision
        "confidence": 0.5,
        "reasoning": "Not sure"
    }

    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(invalid_response))]
        mock_response.usage = Mock(input_tokens=500, output_tokens=200)

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        with pytest.raises(ProviderError) as exc_info:
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )

        assert "Invalid decision" in str(exc_info.value)


@pytest.mark.asyncio
async def test_all_providers_invalid_confidence(anthropic_config, sample_market_data):
    """Test all providers reject invalid confidence values"""
    invalid_response = {
        "decision": "BUY",
        "confidence": 1.5,  # Invalid confidence (> 1.0)
        "reasoning": "Very confident!"
    }

    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(invalid_response))]
        mock_response.usage = Mock(input_tokens=500, output_tokens=200)

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        with pytest.raises(ProviderError) as exc_info:
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )

        assert "Invalid confidence" in str(exc_info.value)


# ==================== BASE PROVIDER TESTS ====================

def test_provider_config_validation():
    """Test provider configuration validation"""
    # Test valid config
    config = ProviderConfig(
        name="test",
        model="test-model",
        api_key="test_key",
        weight=0.5
    )
    assert config.weight == 0.5

    # Test invalid weight (> 1.0)
    with pytest.raises(ValueError):
        ProviderConfig(
            name="test",
            model="test-model",
            api_key="test_key",
            weight=1.5
        )

    # Test invalid weight (< 0)
    with pytest.raises(ValueError):
        ProviderConfig(
            name="test",
            model="test-model",
            api_key="test_key",
            weight=-0.5
        )


def test_provider_status_tracking(anthropic_config):
    """Test provider status and metrics tracking"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(anthropic_config)

        # Initial status
        assert provider.status == ProviderStatus.ACTIVE
        assert provider._request_count == 0
        assert provider._error_count == 0

        # Update metrics without error
        provider.update_metrics(latency_ms=150.0)
        assert provider._request_count == 1
        assert provider._error_count == 0

        # Update metrics with error
        error = Exception("Test error")
        provider.update_metrics(latency_ms=0, error=error)
        assert provider._request_count == 2
        assert provider._error_count == 1
        assert provider._last_error == error


def test_provider_get_status(anthropic_config):
    """Test provider status reporting"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(anthropic_config)

        # Add some metrics
        provider.update_metrics(100.0)
        provider.update_metrics(200.0)

        status = provider.get_status()

        assert status["name"] == "anthropic"
        assert status["model"] == "claude-3-5-sonnet-20241022"
        assert status["status"] == "active"
        assert status["enabled"] is True
        assert status["weight"] == 1.0
        assert status["requests"] == 2
        assert status["errors"] == 0
        assert status["error_rate"] == 0.0
        assert status["avg_latency_ms"] == 150.0


def test_provider_is_available(anthropic_config):
    """Test provider availability check"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(anthropic_config)

        # Available by default
        assert provider.is_available() is True

        # Unavailable when disabled
        provider.config.enabled = False
        assert provider.is_available() is False

        # Unavailable when status is UNAVAILABLE
        provider.config.enabled = True
        provider.set_status(ProviderStatus.UNAVAILABLE)
        assert provider.is_available() is False

        # Unavailable when circuit is open
        provider.set_status(ProviderStatus.CIRCUIT_OPEN)
        assert provider.is_available() is False


def test_provider_build_prompt(anthropic_config, sample_market_data):
    """Test prompt building"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(anthropic_config)

        prompt = provider.build_prompt(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h",
            current_price=49500.0
        )

        assert "BTC/USDT" in prompt
        assert "1h" in prompt
        assert "49500.0" in prompt
        assert "rsi" in prompt.lower()
        assert "macd" in prompt.lower()
        assert "BUY" in prompt
        assert "SELL" in prompt
        assert "HOLD" in prompt


def test_provider_response_to_dict():
    """Test ProviderResponse serialization"""
    response = ProviderResponse(
        provider_name="test",
        model="test-model",
        decision="BUY",
        confidence=0.85,
        reasoning="Test reasoning",
        risk_level="medium",
        suggested_stop_loss=48000.0,
        suggested_take_profit=51000.0,
        latency_ms=150.0,
        tokens_used=700,
        cost_usd=0.015,
    )

    data = response.to_dict()

    assert data["provider_name"] == "test"
    assert data["decision"] == "BUY"
    assert data["confidence"] == 0.85
    assert data["risk_level"] == "medium"
    assert data["latency_ms"] == 150.0
    assert data["tokens_used"] == 700
    assert data["cost_usd"] == 0.015
    assert "timestamp" in data


# ==================== ERROR SCENARIO TESTS ====================

@pytest.mark.asyncio
async def test_anthropic_api_timeout(anthropic_config, sample_market_data):
    """Test handling of API timeout"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=asyncio.TimeoutError("Request timeout"))
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        with pytest.raises(ProviderError):
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )

        # Check error tracking
        assert provider._error_count == 1


@pytest.mark.asyncio
async def test_multiple_json_code_blocks(anthropic_config, sample_market_data):
    """Test handling response with multiple JSON code blocks (takes first one)"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:
        response_with_multiple_blocks = """
Here's my analysis:

```json
{
    "decision": "BUY",
    "confidence": 0.9,
    "reasoning": "Strong buy signal"
}
```

And here's another analysis:

```json
{
    "decision": "SELL",
    "confidence": 0.1,
    "reasoning": "Ignore this"
}
```
"""

        mock_response = Mock()
        mock_response.content = [Mock(text=response_with_multiple_blocks)]
        mock_response.usage = Mock(input_tokens=500, output_tokens=200)
        mock_response.stop_reason = "end_turn"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h"
        )

        # Should parse the first JSON block
        assert response.decision == "BUY"
        assert response.confidence == 0.9


# ==================== PERFORMANCE TESTS ====================

@pytest.mark.asyncio
async def test_concurrent_provider_calls(anthropic_config, openai_config, sample_market_data, valid_json_response):
    """Test multiple providers can be called concurrently"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic, \
         patch('llm_service.providers.openai_provider.AsyncOpenAI') as mock_openai:

        # Mock Anthropic
        anthropic_mock_response = Mock()
        anthropic_mock_response.content = [Mock(text=json.dumps(valid_json_response))]
        anthropic_mock_response.usage = Mock(input_tokens=500, output_tokens=200)
        anthropic_mock_response.stop_reason = "end_turn"

        anthropic_mock_client = AsyncMock()
        anthropic_mock_client.messages.create = AsyncMock(return_value=anthropic_mock_response)
        mock_anthropic.return_value = anthropic_mock_client

        # Mock OpenAI
        openai_mock_response = Mock()
        openai_mock_response.choices = [Mock(message=Mock(content=json.dumps(valid_json_response)), finish_reason="stop")]
        openai_mock_response.usage = Mock(prompt_tokens=500, completion_tokens=200, total_tokens=700)

        openai_mock_client = AsyncMock()
        openai_mock_client.chat.completions.create = AsyncMock(return_value=openai_mock_response)
        mock_openai.return_value = openai_mock_client

        # Create providers
        anthropic_provider = AnthropicProvider(anthropic_config)
        anthropic_provider.client = anthropic_mock_client

        openai_provider = OpenAIProvider(openai_config)
        openai_provider.client = openai_mock_client

        # Call both concurrently
        responses = await asyncio.gather(
            anthropic_provider.generate_signal(sample_market_data, "BTC/USDT", "1h"),
            openai_provider.generate_signal(sample_market_data, "BTC/USDT", "1h"),
        )

        assert len(responses) == 2
        assert responses[0].provider_name == "anthropic"
        assert responses[1].provider_name == "openai"
        assert all(r.decision == "BUY" for r in responses)


# ==================== RETRY LOGIC TESTS ====================

@pytest.mark.asyncio
async def test_anthropic_retry_on_rate_limit(anthropic_config, sample_market_data, valid_json_response):
    """Test retry logic when rate limited"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic, \
         patch('llm_service.providers.anthropic_provider.asyncio.sleep') as mock_sleep:

        # First call fails with rate limit, second succeeds
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(valid_json_response))]
        mock_response.usage = Mock(input_tokens=500, output_tokens=200)
        mock_response.stop_reason = "end_turn"

        mock_client = AsyncMock()
        # Fail first time with ProviderRateLimitError, succeed second time
        mock_client.messages.create = AsyncMock(
            side_effect=[
                ProviderRateLimitError("anthropic", "Rate limit exceeded"),
                mock_response
            ]
        )
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h"
        )

        # Should succeed after retry
        assert response.decision == "BUY"
        # Sleep should have been called for backoff
        assert mock_sleep.call_count >= 1


@pytest.mark.asyncio
async def test_anthropic_authentication_error_no_retry(anthropic_config, sample_market_data):
    """Test that authentication errors don't retry"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:

        mock_client = AsyncMock()
        # Always fail with auth error
        mock_client.messages.create = AsyncMock(
            side_effect=ProviderAuthenticationError("anthropic", "Invalid API key")
        )
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        with pytest.raises(ProviderAuthenticationError):
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )

        # Should only call once (no retries on auth error)
        assert mock_client.messages.create.call_count == 1
        # Status should be set to UNAVAILABLE
        assert provider.status == ProviderStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_health_check_with_timeout(anthropic_config):
    """Test health check timeout handling"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic, \
         patch('llm_service.providers.anthropic_provider.asyncio.wait_for') as mock_wait_for:

        mock_wait_for.side_effect = asyncio.TimeoutError()

        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        provider.client = mock_client

        result = await provider.health_check()

        assert result is False
        assert provider.status == ProviderStatus.DEGRADED


# ==================== ADDITIONAL PROVIDER TESTS ====================

def test_openai_different_model_pricing(openai_config):
    """Test OpenAI pricing for different models"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI'):
        # Test GPT-4o pricing
        openai_config.model = "gpt-4o"
        provider = OpenAIProvider(openai_config)

        cost = provider.estimate_cost(prompt_tokens=1000, completion_tokens=500)
        expected_cost = (1000 / 1_000_000 * 5.0) + (500 / 1_000_000 * 15.0)
        assert abs(cost - expected_cost) < 0.0001


def test_gemini_token_estimation(gemini_config):
    """Test Gemini token estimation"""
    with patch('llm_service.providers.gemini_provider.genai'):
        provider = GeminiProvider(gemini_config)

        # Test token estimation
        test_text = "This is a test message with some words"
        tokens = provider._estimate_tokens(test_text)

        # Should be roughly len / 4
        assert tokens == len(test_text) // 4


@pytest.mark.asyncio
async def test_all_decisions_valid(anthropic_config, sample_market_data):
    """Test all valid decision types (BUY, SELL, HOLD)"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic') as mock_anthropic:

        for decision in ["BUY", "SELL", "HOLD"]:
            response_data = {
                "decision": decision,
                "confidence": 0.75,
                "reasoning": f"Testing {decision} decision"
            }

            mock_response = Mock()
            mock_response.content = [Mock(text=json.dumps(response_data))]
            mock_response.usage = Mock(input_tokens=500, output_tokens=200)
            mock_response.stop_reason = "end_turn"

            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            provider = AnthropicProvider(anthropic_config)
            provider.client = mock_client

            response = await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )

            assert response.decision == decision


def test_provider_format_market_data(anthropic_config):
    """Test market data formatting"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(anthropic_config)

        market_data = {
            "rsi": 65.123456,
            "macd": 0.05,
            "volume": 1500000,
            "recent_candles": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Long list
        }

        formatted = provider.format_market_data(market_data)

        # Should format floats to 4 decimals
        assert "65.1235" in formatted
        # Should truncate long lists
        assert "showing first 5" in formatted
        assert "rsi" in formatted


@pytest.mark.asyncio
async def test_provider_error_with_original_exception():
    """Test ProviderError stores original exception"""
    original_error = ValueError("Original error message")
    provider_error = ProviderError(
        "test_provider",
        "Wrapped error message",
        original_error
    )

    assert provider_error.provider_name == "test_provider"
    assert provider_error.original_error == original_error
    assert "test_provider" in str(provider_error)
    assert "Wrapped error message" in str(provider_error)


@pytest.mark.asyncio
async def test_grok_with_custom_base_url(grok_config):
    """Test Grok provider with custom base URL"""
    custom_url = "https://custom.api.endpoint/v1"
    grok_config.base_url = custom_url

    with patch('llm_service.providers.grok_provider.AsyncOpenAI') as mock_openai:
        provider = GrokProvider(grok_config)

        # Verify custom URL was used
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs['base_url'] == custom_url


@pytest.mark.asyncio
async def test_openai_with_no_usage_data(openai_config, sample_market_data):
    """Test OpenAI handling response without usage data"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI') as mock_openai:
        valid_response = {
            "decision": "BUY",
            "confidence": 0.8,
            "reasoning": "Test"
        }

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps(valid_response)), finish_reason="stop")]
        # No usage data
        mock_response.usage = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        provider.client = mock_client

        with pytest.raises(ProviderError):
            # Should fail because we try to access usage.total_tokens
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )


def test_provider_set_status_logging(anthropic_config):
    """Test that status changes are logged"""
    with patch('llm_service.providers.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(anthropic_config)

        # Change status
        original_status = provider.status
        provider.set_status(ProviderStatus.DEGRADED)

        assert provider.status == ProviderStatus.DEGRADED
        assert provider.status != original_status

        # Setting same status again shouldn't log
        provider.set_status(ProviderStatus.DEGRADED)
        assert provider.status == ProviderStatus.DEGRADED


# ==================== OPENAI RETRY & ERROR TESTS ====================

@pytest.mark.asyncio
async def test_openai_retry_on_timeout(openai_config, sample_market_data, valid_json_response):
    """Test OpenAI retry logic on timeout"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI') as mock_openai, \
         patch('llm_service.providers.openai_provider.asyncio.wait_for') as mock_wait_for:

        # First call times out, second succeeds
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps(valid_json_response)), finish_reason="stop")]
        mock_response.usage = Mock(prompt_tokens=500, completion_tokens=200, total_tokens=700)

        # First call fails, second succeeds
        mock_wait_for.side_effect = [
            asyncio.TimeoutError(),
            mock_response
        ]

        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        provider.client = mock_client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h"
        )

        # Should succeed after retry
        assert response.decision == "BUY"
        assert mock_wait_for.call_count == 2


@pytest.mark.asyncio
async def test_openai_max_retries_exceeded(openai_config, sample_market_data):
    """Test OpenAI fails after max retries"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI') as mock_openai, \
         patch('llm_service.providers.openai_provider.asyncio.wait_for') as mock_wait_for:

        # Always timeout
        mock_wait_for.side_effect = asyncio.TimeoutError()

        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        provider.client = mock_client

        with pytest.raises(ProviderTimeoutError):
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )


@pytest.mark.asyncio
async def test_openai_json_parsing_error(openai_config, sample_market_data):
    """Test OpenAI handles JSON parsing errors"""
    with patch('llm_service.providers.openai_provider.AsyncOpenAI') as mock_openai, \
         patch('llm_service.providers.openai_provider.asyncio.wait_for') as mock_wait_for:

        # Return invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Not valid JSON!"), finish_reason="stop")]
        mock_response.usage = Mock(prompt_tokens=500, completion_tokens=200, total_tokens=700)

        mock_wait_for.return_value = mock_response

        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        provider.client = mock_client

        with pytest.raises(ProviderError):
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )


@pytest.mark.asyncio
async def test_gemini_api_error_retry(gemini_config, sample_market_data, valid_json_response):
    """Test Gemini handles API errors gracefully"""
    with patch('llm_service.providers.gemini_provider.genai') as mock_genai:
        mock_response = Mock()
        mock_response.text = json.dumps(valid_json_response)

        mock_model = Mock()
        # Fail first time, succeed second time
        mock_model.generate_content = Mock(
            side_effect=[Exception("API Error"), mock_response]
        )

        mock_genai.configure = Mock()
        mock_genai.GenerativeModel = Mock(return_value=mock_model)

        provider = GeminiProvider(gemini_config)

        # First call will fail and raise ProviderError
        with pytest.raises(ProviderError):
            await provider.generate_signal(
                market_data=sample_market_data,
                pair="BTC/USDT",
                timeframe="1h"
            )


@pytest.mark.asyncio
async def test_grok_missing_usage_data(grok_config, sample_market_data, valid_json_response):
    """Test Grok handles missing usage data"""
    with patch('llm_service.providers.grok_provider.AsyncOpenAI') as mock_openai:
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps(valid_json_response)), finish_reason="stop")]
        mock_response.usage = None  # No usage data

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = GrokProvider(grok_config)
        provider.client = mock_client

        response = await provider.generate_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="1h"
        )

        # Should handle None usage gracefully
        assert response.decision == "BUY"
        assert response.tokens_used == 0
        assert response.cost_usd >= 0


def test_provider_config_invalid_max_tokens():
    """Test provider config validates max_tokens"""
    with pytest.raises(ValueError):
        ProviderConfig(
            name="test",
            model="test-model",
            api_key="test_key",
            max_tokens=0  # Invalid
        )


def test_provider_config_invalid_timeout():
    """Test provider config validates timeout"""
    with pytest.raises(ValueError):
        ProviderConfig(
            name="test",
            model="test-model",
            api_key="test_key",
            timeout=0  # Invalid
        )
