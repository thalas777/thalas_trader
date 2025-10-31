"""
Provider Factory for Auto-Registration and Initialization
Automatically registers LLM providers based on environment variables
"""
import os
import logging
from typing import List, Dict, Any, Optional

from .providers import (
    BaseLLMProvider,
    ProviderConfig,
    ProviderRegistry,
    get_registry,
    AnthropicProvider,
    OpenAIProvider,
    GeminiProvider,
    GrokProvider,
)

logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory for creating and registering LLM providers from environment variables

    Supports automatic provider initialization based on environment configuration.
    Each provider requires an API key and can be enabled/disabled via env vars.
    """

    # Mapping of provider names to their classes
    PROVIDER_CLASSES = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "grok": GrokProvider,
    }

    # Default model configurations for each provider
    DEFAULT_MODELS = {
        "anthropic": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4-turbo",
        "gemini": "gemini-1.5-pro",
        "grok": "grok-beta",
    }

    @classmethod
    def get_env_value(cls, key: str, default: Any = None) -> Any:
        """
        Get environment variable value with type conversion

        Args:
            key: Environment variable key
            default: Default value if not found

        Returns:
            Environment variable value with appropriate type
        """
        value = os.getenv(key, default)

        # Convert string booleans to bool
        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif value.lower() in ('false', '0', 'no', 'off'):
                return False

        return value

    @classmethod
    def load_provider_config(cls, provider_name: str) -> Optional[ProviderConfig]:
        """
        Load provider configuration from environment variables

        Environment variable format:
        - {PROVIDER}_API_KEY: API key (required)
        - {PROVIDER}_ENABLED: Enable/disable (default: true)
        - {PROVIDER}_MODEL: Model name (default: provider-specific)
        - {PROVIDER}_WEIGHT: Consensus weight (default: 1.0)
        - {PROVIDER}_MAX_TOKENS: Max tokens (default: 1024)
        - {PROVIDER}_TEMPERATURE: Temperature (default: 0.7)
        - {PROVIDER}_TIMEOUT: Timeout in seconds (default: 30)
        - {PROVIDER}_MAX_RETRIES: Max retry attempts (default: 3)

        Args:
            provider_name: Name of the provider (e.g., "anthropic", "openai")

        Returns:
            ProviderConfig if valid configuration found, None otherwise
        """
        provider_upper = provider_name.upper()

        # Check for API key (required)
        api_key = cls.get_env_value(f"{provider_upper}_API_KEY")
        if not api_key:
            logger.warning(f"Skipping {provider_name}: No API key found ({provider_upper}_API_KEY)")
            return None

        # Check if provider is enabled
        enabled = cls.get_env_value(f"{provider_upper}_ENABLED", True)
        if not enabled:
            logger.info(f"Provider {provider_name} is disabled via environment variable")

        # Load configuration with defaults
        model = cls.get_env_value(
            f"{provider_upper}_MODEL",
            cls.DEFAULT_MODELS.get(provider_name, "default")
        )

        try:
            weight = float(cls.get_env_value(f"{provider_upper}_WEIGHT", "1.0"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid weight for {provider_name}, using 1.0")
            weight = 1.0

        try:
            max_tokens = int(cls.get_env_value(f"{provider_upper}_MAX_TOKENS", "1024"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid max_tokens for {provider_name}, using 1024")
            max_tokens = 1024

        try:
            temperature = float(cls.get_env_value(f"{provider_upper}_TEMPERATURE", "0.7"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid temperature for {provider_name}, using 0.7")
            temperature = 0.7

        try:
            timeout = int(cls.get_env_value(f"{provider_upper}_TIMEOUT", "30"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid timeout for {provider_name}, using 30")
            timeout = 30

        try:
            max_retries = int(cls.get_env_value(f"{provider_upper}_MAX_RETRIES", "3"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid max_retries for {provider_name}, using 3")
            max_retries = 3

        # Get optional base URL (for custom endpoints like Grok)
        base_url = cls.get_env_value(f"{provider_upper}_BASE_URL")

        config = ProviderConfig(
            name=provider_name,
            model=model,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
            weight=weight,
            enabled=enabled,
            base_url=base_url,
        )

        logger.info(
            f"Loaded configuration for {provider_name}: "
            f"model={model}, enabled={enabled}, weight={weight}"
        )

        return config

    @classmethod
    def create_providers_from_env(cls) -> List[BaseLLMProvider]:
        """
        Create provider instances from environment variables

        Scans for all supported providers and creates instances for those
        with valid API keys.

        Returns:
            List of instantiated provider instances
        """
        providers = []

        for provider_name, provider_class in cls.PROVIDER_CLASSES.items():
            try:
                # Load configuration from environment
                config = cls.load_provider_config(provider_name)

                if config is None:
                    continue

                # Create provider instance
                provider = provider_class(config)
                providers.append(provider)

                logger.info(
                    f"Created {provider_name} provider: "
                    f"model={config.model}, enabled={config.enabled}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to create {provider_name} provider: {e}",
                    exc_info=True
                )

        return providers

    @classmethod
    def register_provider_classes(cls, registry: ProviderRegistry) -> None:
        """
        Register provider classes in the registry

        This allows the registry to create provider instances on-demand.

        Args:
            registry: ProviderRegistry instance
        """
        for provider_name, provider_class in cls.PROVIDER_CLASSES.items():
            registry.register_provider_class(provider_name, provider_class)
            logger.debug(f"Registered provider class: {provider_name}")

    @classmethod
    def initialize_registry(cls) -> ProviderRegistry:
        """
        Initialize the global provider registry with all configured providers

        This is the main entry point for provider initialization. It:
        1. Gets or creates the global registry
        2. Registers all provider classes
        3. Creates providers from environment variables
        4. Registers provider instances

        Returns:
            Initialized ProviderRegistry with all configured providers
        """
        logger.info("Initializing provider registry from environment variables")

        # Get global registry instance
        registry = get_registry()

        # Register provider classes
        cls.register_provider_classes(registry)

        # Create providers from environment
        providers = cls.create_providers_from_env()

        # Register provider instances
        for provider in providers:
            registry.register_provider(provider.config.name, provider)

        # Log summary
        status = registry.get_registry_status()
        logger.info(
            f"Provider registry initialized: "
            f"{status['total_providers']} total, "
            f"{status['available_providers']} available"
        )

        if providers:
            logger.info(f"Registered providers: {', '.join([p.config.name for p in providers])}")
        else:
            logger.warning("No providers were registered! Check your API key configuration.")

        return registry

    @classmethod
    def get_provider_status_summary(cls) -> Dict[str, Any]:
        """
        Get a summary of all provider statuses

        Returns:
            Dictionary with provider status information
        """
        registry = get_registry()
        status = registry.get_registry_status()

        # Get detailed status for each provider
        provider_details = {}
        for name, provider in registry.get_all_providers().items():
            provider_details[name] = provider.get_status()

        return {
            "registry": status,
            "providers": provider_details,
        }

    @classmethod
    async def health_check_all_providers(cls) -> Dict[str, bool]:
        """
        Perform health check on all registered providers

        Returns:
            Dictionary mapping provider name to health status
        """
        registry = get_registry()
        return await registry.health_check_all()


def initialize_providers() -> ProviderRegistry:
    """
    Convenience function to initialize providers

    This should be called during Django startup (in apps.py ready() method).

    Returns:
        Initialized ProviderRegistry
    """
    return ProviderFactory.initialize_registry()


def get_provider_status() -> Dict[str, Any]:
    """
    Convenience function to get provider status

    Returns:
        Dictionary with provider status information
    """
    return ProviderFactory.get_provider_status_summary()
