"""
Tests for Provider Factory and Auto-Registration System
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from llm_service.provider_factory import ProviderFactory, initialize_providers
from llm_service.providers import (
    ProviderConfig,
    get_registry,
    reset_registry,
    AnthropicProvider,
    OpenAIProvider,
    GeminiProvider,
    GrokProvider,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean registry before and after each test"""
    reset_registry()
    yield
    reset_registry()


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    return {
        'ANTHROPIC_API_KEY': 'test-anthropic-key',
        'ANTHROPIC_ENABLED': 'true',
        'ANTHROPIC_MODEL': 'claude-3-5-sonnet-20241022',
        'ANTHROPIC_WEIGHT': '1.0',
        'OPENAI_API_KEY': 'test-openai-key',
        'OPENAI_ENABLED': 'false',
        'OPENAI_MODEL': 'gpt-4-turbo',
        'OPENAI_WEIGHT': '0.9',
        'GEMINI_API_KEY': 'test-gemini-key',
        'GEMINI_ENABLED': 'true',
        'GEMINI_MODEL': 'gemini-1.5-pro',
        'GEMINI_WEIGHT': '0.8',
        'GROK_API_KEY': 'test-grok-key',
        'GROK_ENABLED': 'true',
        'GROK_MODEL': 'grok-beta',
        'GROK_WEIGHT': '0.7',
    }


class TestProviderFactory:
    """Test ProviderFactory functionality"""

    def test_get_env_value_string(self):
        """Test getting string environment values"""
        with patch.dict(os.environ, {'TEST_KEY': 'test_value'}):
            value = ProviderFactory.get_env_value('TEST_KEY')
            assert value == 'test_value'

    def test_get_env_value_boolean_true(self):
        """Test converting string to boolean (true)"""
        test_cases = ['true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON']
        for test_val in test_cases:
            with patch.dict(os.environ, {'TEST_KEY': test_val}):
                value = ProviderFactory.get_env_value('TEST_KEY')
                assert value is True, f"Failed for input: {test_val}"

    def test_get_env_value_boolean_false(self):
        """Test converting string to boolean (false)"""
        test_cases = ['false', 'False', 'FALSE', '0', 'no', 'NO', 'off', 'OFF']
        for test_val in test_cases:
            with patch.dict(os.environ, {'TEST_KEY': test_val}):
                value = ProviderFactory.get_env_value('TEST_KEY')
                assert value is False, f"Failed for input: {test_val}"

    def test_get_env_value_default(self):
        """Test default value when env var not set"""
        value = ProviderFactory.get_env_value('NONEXISTENT_KEY', 'default_value')
        assert value == 'default_value'

    def test_load_provider_config_missing_api_key(self):
        """Test that config is None when API key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            config = ProviderFactory.load_provider_config('anthropic')
            assert config is None

    def test_load_provider_config_valid(self, mock_env_vars):
        """Test loading valid provider configuration"""
        with patch.dict(os.environ, mock_env_vars):
            config = ProviderFactory.load_provider_config('anthropic')

            assert config is not None
            assert config.name == 'anthropic'
            assert config.model == 'claude-3-5-sonnet-20241022'
            assert config.api_key == 'test-anthropic-key'
            assert config.enabled is True
            assert config.weight == 1.0
            assert config.max_tokens == 1024
            assert config.temperature == 0.7
            assert config.timeout == 30
            assert config.max_retries == 3

    def test_load_provider_config_disabled(self, mock_env_vars):
        """Test loading disabled provider configuration"""
        with patch.dict(os.environ, mock_env_vars):
            config = ProviderFactory.load_provider_config('openai')

            assert config is not None
            assert config.name == 'openai'
            assert config.enabled is False

    def test_load_provider_config_defaults(self):
        """Test that defaults are used when optional vars not set"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}, clear=True):
            config = ProviderFactory.load_provider_config('anthropic')

            assert config is not None
            assert config.enabled is True
            assert config.weight == 1.0
            assert config.max_tokens == 1024
            assert config.temperature == 0.7
            assert config.timeout == 30
            assert config.max_retries == 3

    def test_load_provider_config_invalid_weight(self):
        """Test handling of invalid weight value"""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'ANTHROPIC_WEIGHT': 'invalid'
        }, clear=True):
            config = ProviderFactory.load_provider_config('anthropic')

            assert config is not None
            assert config.weight == 1.0  # Should use default

    def test_create_providers_from_env_no_keys(self):
        """Test that no providers are created when no API keys"""
        with patch.dict(os.environ, {}, clear=True):
            providers = ProviderFactory.create_providers_from_env()
            assert len(providers) == 0

    def test_create_providers_from_env_multiple(self, mock_env_vars):
        """Test creating multiple providers from environment"""
        with patch.dict(os.environ, mock_env_vars):
            providers = ProviderFactory.create_providers_from_env()

            assert len(providers) == 4
            provider_names = [p.config.name for p in providers]
            assert 'anthropic' in provider_names
            assert 'openai' in provider_names
            assert 'gemini' in provider_names
            assert 'grok' in provider_names

    def test_create_providers_from_env_correct_types(self, mock_env_vars):
        """Test that correct provider types are instantiated"""
        with patch.dict(os.environ, mock_env_vars):
            providers = ProviderFactory.create_providers_from_env()

            provider_dict = {p.config.name: p for p in providers}
            assert isinstance(provider_dict['anthropic'], AnthropicProvider)
            assert isinstance(provider_dict['openai'], OpenAIProvider)
            assert isinstance(provider_dict['gemini'], GeminiProvider)
            assert isinstance(provider_dict['grok'], GrokProvider)

    def test_register_provider_classes(self):
        """Test registering provider classes in registry"""
        registry = get_registry()
        ProviderFactory.register_provider_classes(registry)

        status = registry.get_registry_status()
        assert len(status['registered_classes']) == 4
        assert 'anthropic' in status['registered_classes']
        assert 'openai' in status['registered_classes']
        assert 'gemini' in status['registered_classes']
        assert 'grok' in status['registered_classes']

    def test_initialize_registry(self, mock_env_vars):
        """Test full registry initialization"""
        with patch.dict(os.environ, mock_env_vars):
            registry = ProviderFactory.initialize_registry()

            status = registry.get_registry_status()
            assert status['total_providers'] == 4
            # Only enabled providers are available (openai is disabled)
            assert status['available_providers'] == 3

    def test_initialize_registry_empty(self):
        """Test registry initialization with no providers"""
        with patch.dict(os.environ, {}, clear=True):
            registry = ProviderFactory.initialize_registry()

            status = registry.get_registry_status()
            assert status['total_providers'] == 0
            assert status['available_providers'] == 0

    def test_get_provider_status_summary(self, mock_env_vars):
        """Test getting provider status summary"""
        with patch.dict(os.environ, mock_env_vars):
            ProviderFactory.initialize_registry()
            summary = ProviderFactory.get_provider_status_summary()

            assert 'registry' in summary
            assert 'providers' in summary
            assert summary['registry']['total_providers'] == 4
            assert len(summary['providers']) == 4

            # Check individual provider details
            assert 'anthropic' in summary['providers']
            assert summary['providers']['anthropic']['enabled'] is True
            assert 'openai' in summary['providers']
            assert summary['providers']['openai']['enabled'] is False

    def test_initialize_providers_convenience_function(self, mock_env_vars):
        """Test the convenience initialize_providers function"""
        with patch.dict(os.environ, mock_env_vars):
            registry = initialize_providers()

            assert registry is not None
            status = registry.get_registry_status()
            assert status['total_providers'] == 4

    @pytest.mark.asyncio
    async def test_health_check_all_providers(self, mock_env_vars):
        """Test health check on all providers"""
        with patch.dict(os.environ, mock_env_vars):
            ProviderFactory.initialize_registry()

            # Mock the health_check method for all providers (needs to be async)
            registry = get_registry()
            for name, provider in registry.get_all_providers().items():
                async def mock_health_check():
                    return True
                provider.health_check = mock_health_check

            results = await ProviderFactory.health_check_all_providers()

            assert len(results) == 4
            assert all(results.values())  # All should be healthy

    def test_provider_classes_mapping(self):
        """Test that all provider classes are properly mapped"""
        assert len(ProviderFactory.PROVIDER_CLASSES) == 4
        assert ProviderFactory.PROVIDER_CLASSES['anthropic'] == AnthropicProvider
        assert ProviderFactory.PROVIDER_CLASSES['openai'] == OpenAIProvider
        assert ProviderFactory.PROVIDER_CLASSES['gemini'] == GeminiProvider
        assert ProviderFactory.PROVIDER_CLASSES['grok'] == GrokProvider

    def test_default_models_mapping(self):
        """Test that all default models are properly defined"""
        assert len(ProviderFactory.DEFAULT_MODELS) == 4
        assert ProviderFactory.DEFAULT_MODELS['anthropic'] == 'claude-3-5-sonnet-20241022'
        assert ProviderFactory.DEFAULT_MODELS['openai'] == 'gpt-4-turbo'
        assert ProviderFactory.DEFAULT_MODELS['gemini'] == 'gemini-1.5-pro'
        assert ProviderFactory.DEFAULT_MODELS['grok'] == 'grok-beta'

    def test_load_provider_config_with_base_url(self):
        """Test loading provider config with custom base URL"""
        with patch.dict(os.environ, {
            'GROK_API_KEY': 'test-key',
            'GROK_BASE_URL': 'https://custom-api.example.com/v1'
        }, clear=True):
            config = ProviderFactory.load_provider_config('grok')

            assert config is not None
            assert config.base_url == 'https://custom-api.example.com/v1'

    def test_load_provider_config_custom_values(self):
        """Test loading provider config with custom values"""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'ANTHROPIC_MAX_TOKENS': '2048',
            'ANTHROPIC_TEMPERATURE': '0.5',
            'ANTHROPIC_TIMEOUT': '60',
            'ANTHROPIC_MAX_RETRIES': '5',
            'ANTHROPIC_WEIGHT': '0.95',
        }, clear=True):
            config = ProviderFactory.load_provider_config('anthropic')

            assert config is not None
            assert config.max_tokens == 2048
            assert config.temperature == 0.5
            assert config.timeout == 60
            assert config.max_retries == 5
            assert config.weight == 0.95


class TestIntegration:
    """Integration tests for provider factory"""

    def test_full_workflow(self, mock_env_vars):
        """Test complete workflow from env vars to registered providers"""
        with patch.dict(os.environ, mock_env_vars):
            # Initialize registry
            registry = initialize_providers()

            # Check registry status
            status = registry.get_registry_status()
            assert status['total_providers'] == 4

            # Get specific provider
            anthropic = registry.get_provider('anthropic')
            assert anthropic is not None
            assert anthropic.config.model == 'claude-3-5-sonnet-20241022'

            # Get available providers (openai is disabled)
            available = registry.get_available_providers()
            assert len(available) == 3

            # Get weighted providers
            weighted = registry.get_weighted_providers()
            assert len(weighted) == 3
            # Should be sorted by weight descending
            assert weighted[0][1] >= weighted[1][1] >= weighted[2][1]

    def test_enable_disable_workflow(self, mock_env_vars):
        """Test enabling and disabling providers after initialization"""
        with patch.dict(os.environ, mock_env_vars):
            registry = initialize_providers()

            # OpenAI starts disabled
            openai = registry.get_provider('openai')
            assert openai.config.enabled is False
            assert len(registry.get_available_providers()) == 3

            # Enable OpenAI
            registry.enable_provider('openai')
            assert openai.config.enabled is True
            assert len(registry.get_available_providers()) == 4

            # Disable Anthropic
            registry.disable_provider('anthropic')
            anthropic = registry.get_provider('anthropic')
            assert anthropic.config.enabled is False
            assert len(registry.get_available_providers()) == 3
