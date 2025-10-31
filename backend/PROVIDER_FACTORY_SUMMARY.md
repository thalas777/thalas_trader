# Provider Factory and Auto-Registration System

## Overview

The Provider Factory system enables automatic registration and initialization of LLM providers based on environment variables. This eliminates the need for manual provider configuration in code and allows dynamic provider management through environment configuration.

## Components

### 1. Provider Factory (`llm_service/provider_factory.py`)

The `ProviderFactory` class provides static methods for:
- Loading provider configurations from environment variables
- Creating provider instances automatically
- Registering providers in the global registry
- Managing provider status and health checks

#### Key Features

- **Environment-Based Configuration**: All provider settings come from environment variables
- **Automatic Registration**: Providers are registered on Django startup
- **Graceful Degradation**: Missing API keys result in warnings, not failures
- **Type Conversion**: Automatic conversion of string env vars to appropriate types (bool, int, float)
- **Default Values**: Sensible defaults for all optional configuration

### 2. Django Integration (`llm_service/apps.py`)

The `LlmServiceConfig.ready()` method automatically initializes all providers when Django starts. This happens after all apps are loaded but before the application serves requests.

#### Initialization Flow

1. Django loads and initializes all apps
2. `LlmServiceConfig.ready()` is called
3. Provider factory reads environment variables
4. Provider instances are created and registered
5. Global registry is populated and ready for use

### 3. Management Command (`management/commands/llm_providers.py`)

A comprehensive Django management command for provider control and monitoring.

#### Available Commands

```bash
# Show status of all providers
python manage.py llm_providers --status

# List available provider types and configuration options
python manage.py llm_providers --list

# Enable a specific provider
python manage.py llm_providers --enable anthropic

# Disable a specific provider
python manage.py llm_providers --disable grok

# Test a specific provider with health check
python manage.py llm_providers --test anthropic

# Run health checks on all providers
python manage.py llm_providers --health-check

# Reinitialize all providers from environment
python manage.py llm_providers --reinit
```

## Environment Variable Structure

Each provider can be configured using the following environment variables:

```
{PROVIDER}_API_KEY        - API key (required to enable provider)
{PROVIDER}_ENABLED        - Enable/disable provider (default: true)
{PROVIDER}_MODEL          - Model name (provider-specific default)
{PROVIDER}_WEIGHT         - Consensus voting weight 0.0-1.0 (default: 1.0)
{PROVIDER}_MAX_TOKENS     - Maximum tokens per request (default: 1024)
{PROVIDER}_TEMPERATURE    - Temperature 0.0-2.0 (default: 0.7)
{PROVIDER}_TIMEOUT        - Request timeout in seconds (default: 30)
{PROVIDER}_MAX_RETRIES    - Maximum retry attempts (default: 3)
{PROVIDER}_BASE_URL       - Custom API endpoint (optional)
```

### Supported Providers

| Provider   | Default Model               | Class              |
|------------|-----------------------------|--------------------|
| anthropic  | claude-3-5-sonnet-20241022  | AnthropicProvider  |
| openai     | gpt-4-turbo                 | OpenAIProvider     |
| gemini     | gemini-1.5-pro              | GeminiProvider     |
| grok       | grok-beta                   | GrokProvider       |

## Configuration Examples

### Example 1: Enable All Providers

```bash
# Anthropic
export ANTHROPIC_API_KEY=sk-ant-xxx
export ANTHROPIC_ENABLED=true
export ANTHROPIC_WEIGHT=1.0

# OpenAI
export OPENAI_API_KEY=sk-xxx
export OPENAI_ENABLED=true
export OPENAI_WEIGHT=0.9

# Gemini
export GEMINI_API_KEY=xxx
export GEMINI_ENABLED=true
export GEMINI_WEIGHT=0.8

# Grok
export GROK_API_KEY=xxx
export GROK_ENABLED=true
export GROK_WEIGHT=0.7
```

### Example 2: Minimal Configuration (API Key Only)

```bash
# Only Anthropic and OpenAI with minimal config
export ANTHROPIC_API_KEY=sk-ant-xxx
export OPENAI_API_KEY=sk-xxx

# All other settings use defaults:
# - enabled=true
# - weight=1.0
# - max_tokens=1024
# - temperature=0.7
# - timeout=30
# - max_retries=3
```

### Example 3: Custom Configuration

```bash
# Anthropic with custom settings
export ANTHROPIC_API_KEY=sk-ant-xxx
export ANTHROPIC_MODEL=claude-3-opus-20240229
export ANTHROPIC_WEIGHT=1.0
export ANTHROPIC_MAX_TOKENS=2048
export ANTHROPIC_TEMPERATURE=0.5
export ANTHROPIC_TIMEOUT=60
export ANTHROPIC_MAX_RETRIES=5

# OpenAI disabled
export OPENAI_API_KEY=sk-xxx
export OPENAI_ENABLED=false
```

## Usage Examples

### Programmatic Usage

```python
from llm_service.provider_factory import ProviderFactory, initialize_providers
from llm_service.providers import get_registry

# Initialize all providers from environment
registry = initialize_providers()

# Get status summary
status = ProviderFactory.get_provider_status_summary()
print(f"Total providers: {status['registry']['total_providers']}")
print(f"Available providers: {status['registry']['available_providers']}")

# Get specific provider
anthropic = registry.get_provider('anthropic')
if anthropic:
    print(f"Anthropic model: {anthropic.config.model}")

# Get available providers for consensus
available = registry.get_available_providers()
print(f"Providers ready for consensus: {len(available)}")

# Health check
results = await ProviderFactory.health_check_all_providers()
for name, is_healthy in results.items():
    print(f"{name}: {'healthy' if is_healthy else 'unhealthy'}")
```

### Integration with MultiProviderOrchestrator

```python
from llm_service.multi_provider_orchestrator import MultiProviderOrchestrator
from llm_service.providers import get_registry

# Get registry (already initialized on Django startup)
registry = get_registry()

# Create orchestrator with all registered providers
orchestrator = MultiProviderOrchestrator(registry=registry)

# Generate consensus signal
market_data = {...}
result = await orchestrator.generate_consensus_signal(
    market_data=market_data,
    pair="BTC/USDT",
    timeframe="5m"
)

print(f"Decision: {result.decision}")
print(f"Confidence: {result.confidence}")
print(f"Providers: {len(result.provider_responses)}")
```

## Testing

### Running Tests

```bash
# Run all provider factory tests
cd backend
python -m pytest tests/test_provider_factory.py -v

# Run with coverage
python -m pytest tests/test_provider_factory.py --cov=llm_service/provider_factory -v
```

### Test Coverage

The test suite includes 24 tests covering:
- Environment variable parsing and type conversion
- Provider configuration loading
- Provider creation and registration
- Registry initialization
- Health checks
- Enable/disable functionality
- Full integration workflows

**All 24 tests passing** ✅

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Environment Variables                    │
│  ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, etc.   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    ProviderFactory                           │
│  • load_provider_config()                                    │
│  • create_providers_from_env()                               │
│  • initialize_registry()                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Django Startup                             │
│  LlmServiceConfig.ready()                                    │
│  • Calls initialize_providers()                              │
│  • Populates global registry                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  ProviderRegistry                            │
│  Global registry with all configured providers               │
│  • AnthropicProvider                                         │
│  • OpenAIProvider                                            │
│  • GeminiProvider                                            │
│  • GrokProvider                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           MultiProviderOrchestrator                          │
│  Uses registry to generate consensus signals                 │
└─────────────────────────────────────────────────────────────┘
```

## Key Benefits

1. **Zero-Configuration Code**: No hardcoded provider configurations
2. **Environment-Driven**: Easy to configure for different environments (dev, staging, prod)
3. **Dynamic Management**: Enable/disable providers without code changes
4. **Graceful Degradation**: Missing providers don't break the system
5. **Comprehensive Monitoring**: Built-in status and health check commands
6. **Type Safety**: Automatic type conversion with validation
7. **Default Values**: Works with minimal configuration
8. **Extensible**: Easy to add new providers

## Integration Status

✅ **COMPLETE** - Provider Registry Init Agent (Task 2.3)

### Deliverables
- [x] `provider_factory.py` created
- [x] Auto-registration from environment variables
- [x] Django startup integration via `apps.py`
- [x] Management command `llm_providers` with full functionality
- [x] Comprehensive test suite (24 tests passing)
- [x] Documentation and examples
- [x] Updated `.env.example` with all provider configurations

### Integration Points
- **Phase 1 Providers**: All 4 providers supported (Anthropic, OpenAI, Gemini, Grok)
- **Task 2.1**: Ready for use by MultiProviderOrchestrator
- **Task 2.2**: Can be used by consensus API endpoint

## Next Steps

1. **Task 2.2**: Integrate with consensus API endpoint
2. **Task 2.4**: Add E2E consensus testing
3. **QC Gate 1**: Validate full Wave 1 system

## Troubleshooting

### No providers registered
- Check that API keys are set in environment variables
- Run `python manage.py llm_providers --list` to see configuration options
- Check Django logs for initialization errors

### Provider not available
- Verify API key is correct
- Check that `{PROVIDER}_ENABLED` is not set to `false`
- Run health check: `python manage.py llm_providers --test {provider}`

### Configuration not loading
- Ensure environment variables are set before Django starts
- Check `.env` file is in the correct location
- Verify `python-dotenv` is loading the `.env` file

## References

- Provider Base Classes: `backend/llm_service/providers/base.py`
- Registry Implementation: `backend/llm_service/providers/registry.py`
- MultiProviderOrchestrator: `backend/llm_service/multi_provider_orchestrator.py`
- Integration Plan: `.claude/INTEGRATION_PLAN.md`
