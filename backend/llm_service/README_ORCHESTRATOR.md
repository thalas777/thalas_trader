# Multi-Provider Orchestrator

## Overview

The Multi-Provider Orchestrator is the core component of the Thalas Trader multi-LLM consensus system. It coordinates multiple LLM providers (Anthropic Claude, OpenAI GPT, Google Gemini, xAI Grok) and aggregates their trading signal recommendations using a weighted consensus mechanism.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   MultiProviderOrchestrator                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Provider Registry (ProviderRegistry)        │   │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐   │   │
│  │  │Anthropic│ │ OpenAI │  │ Gemini │  │  Grok  │   │   │
│  │  └────────┘  └────────┘  └────────┘  └────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│         Parallel Execution (asyncio.gather)                 │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │       Signal Aggregator (SignalAggregator)          │   │
│  │              - Weighted Voting                      │   │
│  │              - Confidence Calculation               │   │
│  │              - Agreement Score                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│                   ConsensusResult                           │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Parallel Provider Execution
- Uses `asyncio.gather()` to call all providers simultaneously
- Reduces total latency compared to sequential execution
- Each provider runs independently

### 2. Graceful Failure Handling
- Continues with successful providers if some fail
- Configurable minimum provider threshold
- Detailed error logging and reporting
- Different error types handled appropriately:
  - `ProviderAuthenticationError`: API key issues (no retry)
  - `ProviderRateLimitError`: Rate limit exceeded (logged, no retry)
  - `ProviderTimeoutError`: Request timeout (logged)
  - `ProviderError`: Generic provider errors

### 3. Consensus Mechanism
- Weighted voting based on provider weights
- Confidence calculation considers:
  - Individual provider confidence scores
  - Provider weights
  - Agreement level among providers
- Agreement score shows how unified the decision is

### 4. Performance Metrics
- Total orchestration latency tracking
- Per-provider cost calculation
- Token usage monitoring
- Success/failure rate tracking

### 5. Provider Weighting
- Default weights from provider configuration
- Override with custom weights per request
- Weights affect consensus calculation

## Usage

### Basic Setup

```python
from llm_service.providers.registry import get_registry
from llm_service.multi_provider_orchestrator import MultiProviderOrchestrator

# Get registry and register providers
registry = get_registry()

# Create orchestrator
orchestrator = MultiProviderOrchestrator(
    registry=registry,
    min_providers=2,        # Minimum successful providers required
    min_confidence=0.5,     # Minimum confidence threshold
    timeout_seconds=30.0,   # Overall timeout for all providers
)
```

### Generate Consensus Signal

```python
# Prepare market data
market_data = {
    "rsi": 65.5,
    "macd": 150.0,
    "volume": 1000000,
    "price_change_24h": 2.5,
    # ... other indicators
}

# Generate consensus
result = await orchestrator.generate_consensus_signal(
    market_data=market_data,
    pair="BTC/USDT",
    timeframe="5m",
    current_price=50000.0,
    provider_weights={          # Optional custom weights
        "anthropic": 1.0,
        "openai": 0.9,
        "gemini": 0.8,
    }
)

# Access results
print(f"Decision: {result.decision}")              # BUY, SELL, or HOLD
print(f"Confidence: {result.confidence:.2f}")      # 0.0 to 1.0
print(f"Agreement: {result.agreement_score:.2f}")  # How unified providers are
print(f"Reasoning: {result.reasoning}")
print(f"Risk Level: {result.risk_level}")          # low, medium, high
print(f"Providers: {result.participating_providers}/{result.total_providers}")
print(f"Latency: {result.total_latency_ms:.0f}ms")
print(f"Cost: ${result.total_cost_usd:.6f}")
```

### ConsensusResult Structure

```python
@dataclass
class ConsensusResult:
    # Primary decision
    decision: str                # BUY, SELL, HOLD
    confidence: float            # 0.0 to 1.0
    reasoning: str
    risk_level: str              # low, medium, high
    suggested_stop_loss: float   # Optional
    suggested_take_profit: float # Optional

    # Consensus metadata
    total_providers: int
    participating_providers: int
    agreement_score: float       # How well providers agreed
    weighted_confidence: float

    # Provider breakdown
    provider_responses: List[ProviderResponse]
    vote_breakdown: Dict[str, int]      # {"BUY": 2, "HOLD": 1}
    weighted_votes: Dict[str, float]    # {"BUY": 1.8, "HOLD": 0.8}

    # Performance metrics
    total_latency_ms: float
    total_cost_usd: float
    total_tokens: int
    timestamp: datetime
```

### Health Check

```python
# Check provider health
health = await orchestrator.health_check()

print(f"Status: {health['status']}")              # healthy or degraded
print(f"Available: {health['available_providers']}")
print(f"Required: {health['required_providers']}")
print(f"Health: {health['provider_health']}")     # Per-provider status
```

### Metrics

```python
# Get orchestrator metrics
metrics = orchestrator.get_metrics()

print(f"Total requests: {metrics['total_requests']}")
print(f"Successful: {metrics['successful_requests']}")
print(f"Failed: {metrics['failed_requests']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Registry status: {metrics['registry_status']}")
```

## Configuration

### Environment Variables

```bash
# Provider API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
GROK_API_KEY=xai-...

# Provider Configuration (optional)
ANTHROPIC_ENABLED=true
ANTHROPIC_WEIGHT=1.0
OPENAI_ENABLED=true
OPENAI_WEIGHT=0.9
GEMINI_ENABLED=true
GEMINI_WEIGHT=0.8
GROK_ENABLED=false
GROK_WEIGHT=0.7
```

### Orchestrator Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `registry` | ProviderRegistry | Required | Provider registry instance |
| `min_providers` | int | 1 | Minimum successful providers required |
| `min_confidence` | float | 0.5 | Minimum confidence threshold |
| `timeout_seconds` | float | 30.0 | Timeout for all providers |

### Provider Weights

Weights affect consensus calculation:
- Higher weight = more influence in consensus
- Range: 0.0 to 1.0
- Can be set in provider config or per-request
- Default: 1.0 (equal weight)

## Error Handling

### Common Errors

1. **No Available Providers**
   ```python
   ValueError: No available providers in registry
   ```
   - Cause: No providers registered or all disabled
   - Solution: Register and enable at least one provider

2. **Insufficient Providers**
   ```python
   ValueError: Insufficient available providers: 1 < 2
   ```
   - Cause: Not enough providers meet minimum threshold
   - Solution: Lower `min_providers` or add more providers

3. **All Providers Failed**
   ```python
   ValueError: Insufficient successful provider responses: 0 < 2
   ```
   - Cause: All providers returned errors
   - Solution: Check API keys, rate limits, network connectivity

4. **Consensus Aggregation Failed**
   ```python
   RuntimeError: Failed to aggregate consensus
   ```
   - Cause: Error in consensus algorithm
   - Solution: Check logs for details

### Partial Failures

The orchestrator handles partial failures gracefully:
- Continues with successful providers
- Logs failures with details
- Includes failure info in response

Example with 3 providers (2 success, 1 failure):
```python
# Result includes 2 successful responses
# Failure logged but doesn't stop consensus
result.participating_providers == 2
result.total_providers == 3
```

## Performance Considerations

### Latency
- Parallel execution: ~max(provider_latencies)
- Sequential would be: ~sum(provider_latencies)
- Typical: 1-3 seconds for 3 providers

### Cost
- Total cost = sum of all provider costs
- Anthropic: $0.003-0.015 per call
- OpenAI: $0.01-0.06 per call
- Gemini: $0.001-0.01 per call
- Grok: $0.005-0.015 per call

### Optimization Tips
1. Use fewer providers for faster responses
2. Adjust `max_tokens` to reduce cost
3. Cache results when appropriate
4. Monitor provider health to exclude slow/failing providers

## Testing

Run tests:
```bash
cd backend
pytest tests/test_multi_orchestrator.py -v
```

Test coverage:
```bash
pytest tests/test_multi_orchestrator.py --cov=llm_service/multi_provider_orchestrator
```

## Integration Points

### With Provider Registry
```python
from llm_service.providers.registry import get_registry

registry = get_registry()
# Registry manages provider lifecycle
```

### With Signal Aggregator
```python
from llm_service.consensus.aggregator import SignalAggregator

# Orchestrator uses aggregator internally
# You don't need to instantiate it directly
```

### With API Endpoints
```python
# In Django views
from llm_service.multi_provider_orchestrator import MultiProviderOrchestrator

async def generate_signal(request):
    orchestrator = get_orchestrator()  # From dependency injection
    result = await orchestrator.generate_consensus_signal(...)
    return JsonResponse(result.to_dict())
```

## Logging

The orchestrator provides detailed logging:

### Log Levels
- **DEBUG**: Provider calls, weights, detailed flow
- **INFO**: Consensus reached, metrics, provider count
- **WARNING**: Provider failures, retries, degraded status
- **ERROR**: Critical errors, all provider failures

### Example Logs
```
INFO: Generating consensus signal for BTC/USDT (5m) at price 50000.0
INFO: Querying 3 providers: ['anthropic', 'openai', 'gemini']
DEBUG: Provider weights: {'anthropic': 1.0, 'openai': 0.9, 'gemini': 0.8}
DEBUG: Calling provider: anthropic
DEBUG: Calling provider: openai
DEBUG: Calling provider: gemini
DEBUG: Provider anthropic responded: BUY (confidence: 0.85)
DEBUG: Provider openai responded: BUY (confidence: 0.80)
DEBUG: Provider gemini responded: HOLD (confidence: 0.75)
INFO: Received 3 successful responses from providers: ['anthropic', 'openai', 'gemini']
INFO: Consensus reached: BUY (confidence: 0.82, agreement: 0.67, providers: 3/3, latency: 1250ms, cost: $0.008500)
```

## Next Steps

After implementing the orchestrator:
1. **Task 2.2**: Create consensus API endpoint
2. **Task 2.3**: Implement provider factory and auto-initialization
3. **Task 2.4**: Add end-to-end consensus testing
4. **QC Gate 1**: Validate entire Wave 1 system

## Related Documentation

- [Provider Registry](providers/registry.py)
- [Signal Aggregator](consensus/aggregator.py)
- [Base Provider Interface](providers/base.py)
- [Integration Plan](../../.claude/INTEGRATION_PLAN.md)
