"""
Example demonstrating Multi-Provider Orchestrator usage
Shows how to set up and use the consensus-based multi-LLM system
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_service.providers.registry import get_registry, ProviderRegistry
from llm_service.providers.base import ProviderConfig
from llm_service.providers.anthropic_provider import AnthropicProvider
from llm_service.providers.openai_provider import OpenAIProvider
from llm_service.providers.gemini_provider import GeminiProvider
from llm_service.providers.grok_provider import GrokProvider
from llm_service.multi_provider_orchestrator import MultiProviderOrchestrator


async def main():
    """Demonstrate multi-provider orchestrator"""
    print("=" * 80)
    print("Multi-Provider Orchestrator Example")
    print("=" * 80)
    print()

    # Get registry
    registry = get_registry()

    # Register provider classes
    print("Registering provider classes...")
    registry.register_provider_class("anthropic", AnthropicProvider)
    registry.register_provider_class("openai", OpenAIProvider)
    registry.register_provider_class("gemini", GeminiProvider)
    registry.register_provider_class("grok", GrokProvider)
    print(f"Registered {len(registry._provider_classes)} provider classes")
    print()

    # Create provider configurations (with mock keys for demo)
    print("Creating provider instances...")
    providers_config = [
        {
            "name": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "api_key": "demo-key",
            "weight": 1.0,
            "enabled": True,
        },
        {
            "name": "openai",
            "model": "gpt-4",
            "api_key": "demo-key",
            "weight": 0.9,
            "enabled": True,
        },
        {
            "name": "gemini",
            "model": "gemini-1.5-pro",
            "api_key": "demo-key",
            "weight": 0.8,
            "enabled": True,
        },
    ]

    for config_dict in providers_config:
        config = ProviderConfig(**config_dict)
        try:
            registry.create_provider(config_dict["name"], config)
            print(f"  ✓ Created provider: {config.name} (weight: {config.weight})")
        except Exception as e:
            print(f"  ✗ Failed to create {config.name}: {e}")

    print()

    # Check registry status
    status = registry.get_registry_status()
    print("Registry Status:")
    print(f"  Total providers: {status['total_providers']}")
    print(f"  Available providers: {status['available_providers']}")
    print(f"  Provider names: {', '.join(status['provider_names'])}")
    print()

    # Create orchestrator
    print("Creating multi-provider orchestrator...")
    orchestrator = MultiProviderOrchestrator(
        registry=registry,
        min_providers=2,  # Need at least 2 providers for consensus
        min_confidence=0.5,
        timeout_seconds=30.0,
    )
    print("  ✓ Orchestrator initialized")
    print()

    # Prepare sample market data
    market_data = {
        "rsi": 65.5,
        "macd": 150.0,
        "macd_signal": 140.0,
        "volume": 1000000,
        "price_change_24h": 2.5,
        "ema_20": 49800.0,
        "ema_50": 49500.0,
        "bollinger_upper": 51000.0,
        "bollinger_lower": 48000.0,
    }

    print("Sample Market Data:")
    for key, value in market_data.items():
        print(f"  {key}: {value}")
    print()

    # Note: This would require valid API keys to work
    print("NOTE: To actually generate signals, you need valid API keys.")
    print("Set environment variables:")
    print("  - ANTHROPIC_API_KEY")
    print("  - OPENAI_API_KEY")
    print("  - GEMINI_API_KEY")
    print()

    print("Example consensus generation call:")
    print("""
    result = await orchestrator.generate_consensus_signal(
        market_data=market_data,
        pair="BTC/USDT",
        timeframe="5m",
        current_price=50000.0,
        provider_weights={"anthropic": 1.0, "openai": 0.9, "gemini": 0.8}
    )

    print(f"Consensus Decision: {result.decision}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Agreement Score: {result.agreement_score:.2f}")
    print(f"Providers: {result.participating_providers}/{result.total_providers}")
    print(f"Total Latency: {result.total_latency_ms:.0f}ms")
    print(f"Total Cost: ${result.total_cost_usd:.6f}")
    """)

    # Show orchestrator metrics
    print("\nOrchestrator Metrics:")
    metrics = orchestrator.get_metrics()
    print(f"  Total requests: {metrics['total_requests']}")
    print(f"  Successful: {metrics['successful_requests']}")
    print(f"  Failed: {metrics['failed_requests']}")
    print(f"  Success rate: {metrics['success_rate']:.2%}")
    print()

    print("=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
