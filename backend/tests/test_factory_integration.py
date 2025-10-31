"""
Integration tests for Provider Factory with MultiProviderOrchestrator
Verifies that providers initialized via environment variables work with the orchestrator
"""
import os
import pytest
from unittest.mock import patch, AsyncMock

from llm_service.provider_factory import ProviderFactory
from llm_service.providers import get_registry, reset_registry, ProviderResponse
from llm_service.multi_provider_orchestrator import MultiProviderOrchestrator


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean registry before and after each test"""
    reset_registry()
    yield
    reset_registry()


@pytest.fixture
def full_env_config():
    """Complete environment configuration for all providers"""
    return {
        'ANTHROPIC_API_KEY': 'test-anthropic-key',
        'ANTHROPIC_ENABLED': 'true',
        'ANTHROPIC_MODEL': 'claude-3-5-sonnet-20241022',
        'ANTHROPIC_WEIGHT': '1.0',
        'OPENAI_API_KEY': 'test-openai-key',
        'OPENAI_ENABLED': 'true',
        'OPENAI_MODEL': 'gpt-4-turbo',
        'OPENAI_WEIGHT': '0.9',
        'GEMINI_API_KEY': 'test-gemini-key',
        'GEMINI_ENABLED': 'true',
        'GEMINI_MODEL': 'gemini-1.5-pro',
        'GEMINI_WEIGHT': '0.8',
        'GROK_API_KEY': 'test-grok-key',
        'GROK_ENABLED': 'false',
        'GROK_MODEL': 'grok-beta',
        'GROK_WEIGHT': '0.7',
    }


@pytest.mark.asyncio
class TestProviderFactoryIntegration:
    """Integration tests for Provider Factory with Orchestrator"""

    async def test_factory_to_orchestrator_workflow(self, full_env_config):
        """Test complete workflow from factory initialization to consensus generation"""
        with patch.dict(os.environ, full_env_config):
            # Step 1: Initialize providers via factory
            registry = ProviderFactory.initialize_registry()

            # Verify providers registered
            status = registry.get_registry_status()
            assert status['total_providers'] == 4
            assert status['available_providers'] == 3  # Grok disabled

            # Step 2: Create orchestrator with registry
            orchestrator = MultiProviderOrchestrator(registry=registry)

            # Verify orchestrator has correct providers through registry
            available_providers = registry.get_available_providers()
            assert len(available_providers) == 3
            provider_names = [p.config.name for p in available_providers]
            assert 'anthropic' in provider_names
            assert 'openai' in provider_names
            assert 'gemini' in provider_names
            assert 'grok' not in provider_names  # Disabled

            # Step 3: Mock provider responses
            mock_response = ProviderResponse(
                provider_name="test",
                model="test-model",
                decision="BUY",
                confidence=0.85,
                reasoning="Test reasoning",
                risk_level="medium",
                latency_ms=100.0,
                tokens_used=100,
                cost_usd=0.01
            )

            for provider in available_providers:
                provider.generate_signal = AsyncMock(return_value=mock_response)

            # Step 4: Generate consensus signal
            market_data = {
                'rsi': 45.0,
                'macd': 0.5,
                'volume': 1000000,
            }

            result = await orchestrator.generate_consensus_signal(
                market_data=market_data,
                pair="BTC/USDT",
                timeframe="5m",
                current_price=50000.0
            )

            # Verify consensus result
            assert result.decision == "BUY"
            assert result.confidence > 0
            assert result.total_providers == 3
            assert result.participating_providers == 3
            assert len(result.provider_responses) == 3

    async def test_factory_respects_enabled_flag(self, full_env_config):
        """Test that factory respects ENABLED flag and orchestrator uses only enabled providers"""
        # Disable OpenAI
        config = full_env_config.copy()
        config['OPENAI_ENABLED'] = 'false'

        with patch.dict(os.environ, config):
            registry = ProviderFactory.initialize_registry()

            # Should have 4 registered but only 2 available (Anthropic, Gemini)
            status = registry.get_registry_status()
            assert status['total_providers'] == 4
            assert status['available_providers'] == 2

            orchestrator = MultiProviderOrchestrator(registry=registry)

            # Orchestrator should only get available providers through registry
            available = registry.get_available_providers()
            assert len(available) == 2
            provider_names = [p.config.name for p in available]
            assert 'anthropic' in provider_names
            assert 'gemini' in provider_names
            assert 'openai' not in provider_names
            assert 'grok' not in provider_names

    async def test_factory_weight_configuration(self, full_env_config):
        """Test that factory weight configuration is used by orchestrator"""
        with patch.dict(os.environ, full_env_config):
            registry = ProviderFactory.initialize_registry()
            orchestrator = MultiProviderOrchestrator(registry=registry)

            # Check that weights are correctly set in registry providers
            available = registry.get_available_providers()
            provider_weights = {p.config.name: p.config.weight for p in available}
            assert provider_weights['anthropic'] == 1.0
            assert provider_weights['openai'] == 0.9
            assert provider_weights['gemini'] == 0.8

    async def test_runtime_enable_disable(self, full_env_config):
        """Test runtime enable/disable of providers affects orchestrator"""
        with patch.dict(os.environ, full_env_config):
            registry = ProviderFactory.initialize_registry()

            # Initially 3 available
            assert len(registry.get_available_providers()) == 3

            # Disable Anthropic at runtime
            registry.disable_provider('anthropic')
            assert len(registry.get_available_providers()) == 2

            # Verify available providers after disabling
            assert len(registry.get_available_providers()) == 2

            # Re-enable Anthropic
            registry.enable_provider('anthropic')
            assert len(registry.get_available_providers()) == 3

            # Create orchestrator - should have access to all available providers
            orchestrator = MultiProviderOrchestrator(registry=registry)
            assert len(registry.get_available_providers()) == 3

    async def test_minimal_configuration(self):
        """Test that factory works with minimal configuration (API keys only)"""
        minimal_config = {
            'ANTHROPIC_API_KEY': 'test-key-1',
            'OPENAI_API_KEY': 'test-key-2',
        }

        with patch.dict(os.environ, minimal_config, clear=True):
            registry = ProviderFactory.initialize_registry()

            # Should have 2 providers with default settings
            status = registry.get_registry_status()
            assert status['total_providers'] == 2
            assert status['available_providers'] == 2

            # Verify default values
            anthropic = registry.get_provider('anthropic')
            assert anthropic.config.weight == 1.0
            assert anthropic.config.enabled is True
            assert anthropic.config.max_tokens == 1024
            assert anthropic.config.temperature == 0.7

            openai = registry.get_provider('openai')
            assert openai.config.weight == 1.0
            assert openai.config.enabled is True

    async def test_custom_configuration(self):
        """Test that factory handles custom configuration correctly"""
        custom_config = {
            'ANTHROPIC_API_KEY': 'test-key',
            'ANTHROPIC_WEIGHT': '0.95',
            'ANTHROPIC_MAX_TOKENS': '2048',
            'ANTHROPIC_TEMPERATURE': '0.5',
            'ANTHROPIC_TIMEOUT': '60',
            'ANTHROPIC_MAX_RETRIES': '5',
        }

        with patch.dict(os.environ, custom_config, clear=True):
            registry = ProviderFactory.initialize_registry()

            anthropic = registry.get_provider('anthropic')
            assert anthropic.config.weight == 0.95
            assert anthropic.config.max_tokens == 2048
            assert anthropic.config.temperature == 0.5
            assert anthropic.config.timeout == 60
            assert anthropic.config.max_retries == 5

    async def test_no_api_keys_graceful_degradation(self):
        """Test that system handles missing API keys gracefully"""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise exception
            registry = ProviderFactory.initialize_registry()

            # Should have no providers
            status = registry.get_registry_status()
            assert status['total_providers'] == 0
            assert status['available_providers'] == 0

            # Orchestrator should handle empty registry
            orchestrator = MultiProviderOrchestrator(registry=registry)
            assert len(registry.get_available_providers()) == 0

    async def test_provider_status_summary_integration(self, full_env_config):
        """Test getting provider status summary after initialization"""
        with patch.dict(os.environ, full_env_config):
            ProviderFactory.initialize_registry()

            summary = ProviderFactory.get_provider_status_summary()

            # Check registry summary
            assert summary['registry']['total_providers'] == 4
            assert summary['registry']['available_providers'] == 3

            # Check individual provider details
            assert 'anthropic' in summary['providers']
            assert 'openai' in summary['providers']
            assert 'gemini' in summary['providers']
            assert 'grok' in summary['providers']

            # Verify enabled status
            assert summary['providers']['anthropic']['enabled'] is True
            assert summary['providers']['openai']['enabled'] is True
            assert summary['providers']['gemini']['enabled'] is True
            assert summary['providers']['grok']['enabled'] is False

    async def test_weighted_providers_sorting(self, full_env_config):
        """Test that weighted providers are sorted correctly"""
        with patch.dict(os.environ, full_env_config):
            registry = ProviderFactory.initialize_registry()

            # Get weighted providers
            weighted = registry.get_weighted_providers()

            # Should be 3 available providers (grok disabled)
            assert len(weighted) == 3

            # Should be sorted by weight descending
            weights = [w for _, w in weighted]
            assert weights == sorted(weights, reverse=True)

            # Verify specific weights
            assert weighted[0][1] == 1.0  # anthropic
            assert weighted[1][1] == 0.9  # openai
            assert weighted[2][1] == 0.8  # gemini

    async def test_health_check_integration(self, full_env_config):
        """Test health check workflow from factory to registry"""
        with patch.dict(os.environ, full_env_config):
            registry = ProviderFactory.initialize_registry()

            # Mock health checks for all providers
            for name, provider in registry.get_all_providers().items():
                async def mock_health_check():
                    return True
                provider.health_check = mock_health_check

            # Run health check via factory
            results = await ProviderFactory.health_check_all_providers()

            # All providers should be healthy
            assert len(results) == 4
            assert results['anthropic'] is True
            assert results['openai'] is True
            assert results['gemini'] is True
            assert results['grok'] is True

    async def test_orchestrator_uses_factory_weights(self, full_env_config):
        """Test that orchestrator respects weights from factory configuration"""
        with patch.dict(os.environ, full_env_config):
            registry = ProviderFactory.initialize_registry()
            orchestrator = MultiProviderOrchestrator(registry=registry)

            # Mock provider responses with different decisions
            available = registry.get_available_providers()
            for i, provider in enumerate(available):
                decision = ["BUY", "SELL", "HOLD"][i % 3]
                mock_response = ProviderResponse(
                    provider_name=provider.config.name,
                    model=provider.config.model,
                    decision=decision,
                    confidence=0.8,
                    reasoning="Test",
                    risk_level="medium",
                    latency_ms=100.0,
                    tokens_used=100,
                    cost_usd=0.01
                )
                provider.generate_signal = AsyncMock(return_value=mock_response)

            # Generate consensus with factory weights
            result = await orchestrator.generate_consensus_signal(
                market_data={'test': 'data'},
                pair="BTC/USDT",
                timeframe="5m",
                current_price=50000.0
            )

            # Verify weights were used in consensus
            # (weighted_confidence should reflect provider weights)
            assert result.weighted_confidence > 0
            assert result.participating_providers == 3
