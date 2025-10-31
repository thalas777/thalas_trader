"""
Provider Registry for Multi-LLM System
Manages registration, discovery, and lifecycle of LLM providers
"""
from typing import Dict, List, Optional, Type
import logging
from .base import BaseLLMProvider, ProviderConfig, ProviderStatus

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry for managing LLM providers

    Implements a plugin-style architecture where providers can be registered
    dynamically. Supports provider discovery, health monitoring, and
    automatic failover.
    """

    def __init__(self):
        """Initialize the provider registry"""
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._provider_classes: Dict[str, Type[BaseLLMProvider]] = {}
        logger.info("Provider registry initialized")

    def register_provider_class(
        self,
        name: str,
        provider_class: Type[BaseLLMProvider]
    ) -> None:
        """
        Register a provider class for later instantiation

        Args:
            name: Provider identifier (e.g., "anthropic", "openai")
            provider_class: Provider class type

        Raises:
            ValueError: If provider name already registered
        """
        if name in self._provider_classes:
            logger.warning(f"Provider class {name} already registered, overwriting")

        self._provider_classes[name] = provider_class
        logger.info(f"Registered provider class: {name}")

    def register_provider(
        self,
        name: str,
        provider: BaseLLMProvider
    ) -> None:
        """
        Register an instantiated provider

        Args:
            name: Provider identifier
            provider: Provider instance

        Raises:
            ValueError: If provider name already registered
        """
        if name in self._providers:
            logger.warning(f"Provider {name} already registered, overwriting")

        self._providers[name] = provider
        logger.info(f"Registered provider instance: {name}")

    def create_provider(
        self,
        name: str,
        config: ProviderConfig
    ) -> BaseLLMProvider:
        """
        Create a provider instance from registered class

        Args:
            name: Provider type name
            config: Provider configuration

        Returns:
            Instantiated provider

        Raises:
            ValueError: If provider class not registered
        """
        if name not in self._provider_classes:
            raise ValueError(f"Provider class {name} not registered")

        provider_class = self._provider_classes[name]
        provider = provider_class(config)

        # Auto-register the instance
        self.register_provider(config.name, provider)

        return provider

    def get_provider(self, name: str) -> Optional[BaseLLMProvider]:
        """
        Get a provider by name

        Args:
            name: Provider identifier

        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(name)

    def get_all_providers(self) -> Dict[str, BaseLLMProvider]:
        """
        Get all registered providers

        Returns:
            Dictionary of provider name to provider instance
        """
        return self._providers.copy()

    def get_available_providers(self) -> List[BaseLLMProvider]:
        """
        Get all available (enabled and healthy) providers

        Returns:
            List of available provider instances
        """
        return [
            provider
            for provider in self._providers.values()
            if provider.is_available()
        ]

    def get_providers_by_status(
        self,
        status: ProviderStatus
    ) -> List[BaseLLMProvider]:
        """
        Get providers by status

        Args:
            status: Provider status to filter by

        Returns:
            List of providers with the specified status
        """
        return [
            provider
            for provider in self._providers.values()
            if provider.status == status
        ]

    def remove_provider(self, name: str) -> bool:
        """
        Remove a provider from the registry

        Args:
            name: Provider identifier

        Returns:
            True if provider was removed, False if not found
        """
        if name in self._providers:
            del self._providers[name]
            logger.info(f"Removed provider: {name}")
            return True
        return False

    def enable_provider(self, name: str) -> bool:
        """
        Enable a provider

        Args:
            name: Provider identifier

        Returns:
            True if provider was enabled, False if not found
        """
        provider = self.get_provider(name)
        if provider:
            provider.config.enabled = True
            logger.info(f"Enabled provider: {name}")
            return True
        return False

    def disable_provider(self, name: str) -> bool:
        """
        Disable a provider

        Args:
            name: Provider identifier

        Returns:
            True if provider was disabled, False if not found
        """
        provider = self.get_provider(name)
        if provider:
            provider.config.enabled = False
            logger.info(f"Disabled provider: {name}")
            return True
        return False

    def get_registry_status(self) -> Dict[str, any]:
        """
        Get overall registry status

        Returns:
            Dictionary with registry statistics
        """
        total = len(self._providers)
        available = len(self.get_available_providers())
        by_status = {}

        for status in ProviderStatus:
            count = len(self.get_providers_by_status(status))
            if count > 0:
                by_status[status.value] = count

        return {
            "total_providers": total,
            "available_providers": available,
            "providers_by_status": by_status,
            "provider_names": list(self._providers.keys()),
            "registered_classes": list(self._provider_classes.keys()),
        }

    async def health_check_all(self) -> Dict[str, bool]:
        """
        Perform health check on all providers

        Returns:
            Dictionary mapping provider name to health status
        """
        results = {}

        for name, provider in self._providers.items():
            try:
                is_healthy = await provider.health_check()
                results[name] = is_healthy

                # Update provider status based on health check
                if is_healthy:
                    if provider.status == ProviderStatus.UNAVAILABLE:
                        provider.set_status(ProviderStatus.ACTIVE)
                else:
                    provider.set_status(ProviderStatus.DEGRADED)

            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
                provider.set_status(ProviderStatus.UNAVAILABLE)

        return results

    def get_weighted_providers(self) -> List[tuple[BaseLLMProvider, float]]:
        """
        Get available providers with their weights

        Returns:
            List of tuples (provider, weight) sorted by weight descending
        """
        weighted = [
            (provider, provider.config.weight)
            for provider in self.get_available_providers()
        ]

        # Sort by weight descending
        weighted.sort(key=lambda x: x[1], reverse=True)

        return weighted

    def clear(self) -> None:
        """Clear all registered providers"""
        self._providers.clear()
        logger.info("Provider registry cleared")

    def __len__(self) -> int:
        """Get number of registered providers"""
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        """Check if provider is registered"""
        return name in self._providers

    def __repr__(self) -> str:
        """String representation of registry"""
        return f"ProviderRegistry(providers={len(self._providers)})"


# Global registry instance
_global_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """
    Get the global provider registry instance

    Returns:
        Global ProviderRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ProviderRegistry()
    return _global_registry


def reset_registry() -> None:
    """Reset the global registry (mainly for testing)"""
    global _global_registry
    if _global_registry:
        _global_registry.clear()
    _global_registry = None
