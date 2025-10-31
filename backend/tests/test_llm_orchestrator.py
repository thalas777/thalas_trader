"""
Unit tests for LLM Orchestrator
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from llm_service.orchestrator import LLMOrchestrator, LLMOrchestratorError


class TestLLMOrchestrator:
    """Test suite for LLMOrchestrator"""

    @pytest.fixture
    def mock_anthropic_response(self):
        """Mock Anthropic API response"""
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = json.dumps({
            "decision": "BUY",
            "confidence": 0.85,
            "reasoning": "Strong bullish indicators",
            "risk_level": "medium"
        })
        mock_message.content = [mock_content]
        return mock_message

    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing"""
        return {
            "rsi": 45.2,
            "ema_short": 42500.0,
            "ema_long": 42300.0,
            "volume": 1250000,
            "recent_candles": [
                {"open": 42400, "high": 42600, "low": 42300, "close": 42500, "volume": 1200000}
            ]
        }

    def test_orchestrator_init_without_api_key(self):
        """Test orchestrator raises error without API key"""
        with patch('django.conf.settings.ANTHROPIC_API_KEY', ''):
            with pytest.raises(LLMOrchestratorError):
                LLMOrchestrator(provider='anthropic')

    def test_orchestrator_unsupported_provider(self):
        """Test orchestrator raises error for unsupported provider"""
        with pytest.raises(LLMOrchestratorError):
            LLMOrchestrator(provider='invalid_provider')

    @patch('llm_service.orchestrator.Anthropic')
    @patch('django.conf.settings.ANTHROPIC_API_KEY', 'test-key')
    def test_orchestrator_init_anthropic(self, mock_anthropic_class):
        """Test orchestrator initializes with Anthropic"""
        orchestrator = LLMOrchestrator(provider='anthropic')
        assert orchestrator.provider == 'anthropic'
        assert orchestrator.anthropic_client is not None

    def test_parse_llm_response_valid_json(self):
        """Test parsing valid JSON response"""
        with patch('django.conf.settings.ANTHROPIC_API_KEY', 'test-key'):
            with patch('llm_service.orchestrator.Anthropic'):
                orchestrator = LLMOrchestrator(provider='anthropic')

                valid_response = json.dumps({
                    "decision": "BUY",
                    "confidence": 0.85,
                    "reasoning": "Test reasoning"
                })

                result = orchestrator._parse_llm_response(valid_response)
                assert result['decision'] == 'BUY'
                assert result['confidence'] == 0.85

    def test_parse_llm_response_with_markdown(self):
        """Test parsing response with markdown code blocks"""
        with patch('django.conf.settings.ANTHROPIC_API_KEY', 'test-key'):
            with patch('llm_service.orchestrator.Anthropic'):
                orchestrator = LLMOrchestrator(provider='anthropic')

                markdown_response = """```json
                {
                    "decision": "SELL",
                    "confidence": 0.75,
                    "reasoning": "Test"
                }
                ```"""

                result = orchestrator._parse_llm_response(markdown_response)
                assert result['decision'] == 'SELL'

    def test_parse_llm_response_invalid_decision(self):
        """Test parsing response with invalid decision"""
        with patch('django.conf.settings.ANTHROPIC_API_KEY', 'test-key'):
            with patch('llm_service.orchestrator.Anthropic'):
                orchestrator = LLMOrchestrator(provider='anthropic')

                invalid_response = json.dumps({
                    "decision": "INVALID",
                    "confidence": 0.85,
                    "reasoning": "Test"
                })

                with pytest.raises(LLMOrchestratorError):
                    orchestrator._parse_llm_response(invalid_response)

    def test_parse_llm_response_invalid_confidence(self):
        """Test parsing response with invalid confidence"""
        with patch('django.conf.settings.ANTHROPIC_API_KEY', 'test-key'):
            with patch('llm_service.orchestrator.Anthropic'):
                orchestrator = LLMOrchestrator(provider='anthropic')

                invalid_response = json.dumps({
                    "decision": "BUY",
                    "confidence": 1.5,  # Invalid: > 1.0
                    "reasoning": "Test"
                })

                with pytest.raises(LLMOrchestratorError):
                    orchestrator._parse_llm_response(invalid_response)

    def test_parse_llm_response_missing_fields(self):
        """Test parsing response with missing required fields"""
        with patch('django.conf.settings.ANTHROPIC_API_KEY', 'test-key'):
            with patch('llm_service.orchestrator.Anthropic'):
                orchestrator = LLMOrchestrator(provider='anthropic')

                incomplete_response = json.dumps({
                    "decision": "BUY"
                    # Missing confidence and reasoning
                })

                with pytest.raises(LLMOrchestratorError):
                    orchestrator._parse_llm_response(incomplete_response)

    def test_format_market_data(self, sample_market_data):
        """Test market data formatting"""
        with patch('django.conf.settings.ANTHROPIC_API_KEY', 'test-key'):
            with patch('llm_service.orchestrator.Anthropic'):
                orchestrator = LLMOrchestrator(provider='anthropic')

                formatted = orchestrator._format_market_data(sample_market_data)
                assert isinstance(formatted, str)
                assert "rsi" in formatted
                assert "45.2" in formatted

    @patch('llm_service.orchestrator.Anthropic')
    @patch('django.conf.settings.ANTHROPIC_API_KEY', 'test-key')
    def test_generate_trading_signal(self, mock_anthropic_class, mock_anthropic_response, sample_market_data):
        """Test full signal generation flow"""
        # Setup mock
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client

        orchestrator = LLMOrchestrator(provider='anthropic')

        signal = orchestrator.generate_trading_signal(
            market_data=sample_market_data,
            pair="BTC/USDT",
            timeframe="5m",
            current_price=42500.0
        )

        assert signal['decision'] in ['BUY', 'SELL', 'HOLD']
        assert 0 <= signal['confidence'] <= 1
        assert 'reasoning' in signal

    @patch('llm_service.orchestrator.Anthropic')
    @patch('django.conf.settings.ANTHROPIC_API_KEY', 'test-key')
    def test_health_check(self, mock_anthropic_class):
        """Test health check returns configuration"""
        orchestrator = LLMOrchestrator(provider='anthropic')
        health = orchestrator.health_check()

        assert 'provider' in health
        assert 'model' in health
        assert 'configured' in health
        assert health['provider'] == 'anthropic'
