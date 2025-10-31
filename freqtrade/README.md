# Freqtrade LLM Integration

This directory contains the groundbreaking LLM Signal Provider adapter and example strategies for integrating Large Language Models into Freqtrade trading bots.

## Overview

The LLM integration allows Freqtrade strategies to leverage AI models (Claude, GPT) for trading signal generation. The architecture decouples the trading bot from LLM APIs by routing requests through the Django backend.

```
Freqtrade Strategy
      ↓
LLM Signal Provider (this adapter)
      ↓
Django Backend API
      ↓
LLM Orchestrator
      ↓
Claude API / OpenAI API
```

## Components

### 1. LLM Signal Provider (`adapters/llm_signal_provider.py`)

The core adapter that Freqtrade strategies use to get AI-powered trading signals.

**Features:**
- Communicates with Django backend API
- Extracts relevant market data from Freqtrade dataframes
- Handles errors gracefully with fallback to neutral signals
- Supports configurable LLM providers (Claude/GPT)
- Automatic indicator extraction and formatting

**Key Methods:**
- `get_signal()` - Get trading signal based on market data
- `health_check()` - Verify LLM service availability

### 2. LLM Momentum Strategy (`strategies/LLM_Momentum_Strategy.py`)

Example Freqtrade strategy demonstrating LLM integration.

**Features:**
- Hybrid approach: Technical indicators + LLM analysis
- Uses RSI, EMA, MACD, Bollinger Bands
- Consults LLM only when technical pre-conditions are met
- Configurable confidence thresholds
- Graceful fallback to technical-only signals if LLM unavailable

## Installation

### 1. Install Dependencies

```bash
cd /path/to/thalas_trader/freqtrade
pip install -r requirements.txt
```

### 2. Copy Files to Freqtrade

Copy the adapter and strategy to your Freqtrade installation:

```bash
# Copy LLM Signal Provider
cp adapters/llm_signal_provider.py /path/to/your/freqtrade/user_data/strategies/

# Copy example strategy
cp strategies/LLM_Momentum_Strategy.py /path/to/your/freqtrade/user_data/strategies/
```

### 3. Configure Environment

Create a `.env` file in your Freqtrade directory or set environment variables:

```bash
export DJANGO_API_URL=http://localhost:8000
```

Or add to your Freqtrade config:

```json
{
  "strategy": "LLM_Momentum_Strategy",
  // ... other config
}
```

## Usage

### Basic Strategy Implementation

```python
from freqtrade.strategy import IStrategy
from llm_signal_provider import LLMSignalProvider

class MyLLMStrategy(IStrategy):
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.llm_provider = LLMSignalProvider()

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Get LLM signal
        signal = self.llm_provider.get_signal(
            dataframe=dataframe,
            pair=metadata['pair'],
            timeframe=self.timeframe
        )

        # Apply signal
        if signal['decision'] == 'BUY' and signal['confidence'] > 0.7:
            dataframe.loc[dataframe.index[-1], 'enter_long'] = 1

        return dataframe
```

### Advanced: Custom Indicators

You can specify which indicators to send to the LLM:

```python
signal = self.llm_provider.get_signal(
    dataframe=dataframe,
    pair=metadata['pair'],
    timeframe=self.timeframe,
    indicators={
        "rsi": "rsi",
        "ema_short": "ema_20",
        "ema_long": "ema_50",
        "volume": "volume",
        "custom_indicator": "my_custom_column",
    }
)
```

### Understanding LLM Responses

The LLM returns a structured signal:

```python
{
    "decision": "BUY",  # or "SELL" or "HOLD"
    "confidence": 0.85,  # 0.0 to 1.0
    "reasoning": "Strong bullish momentum with RSI recovery from oversold...",
    "risk_level": "medium",  # "low", "medium", or "high"
    "suggested_stop_loss": 42000.0,  # Optional
    "suggested_take_profit": 45000.0,  # Optional
    "pair": "BTC/USDT",
    "timeframe": "5m",
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022"
}
```

## Configuration Options

### LLMSignalProvider Parameters

```python
provider = LLMSignalProvider(
    api_url="http://localhost:8000",  # Django backend URL
    provider="anthropic",  # or "openai"
    timeout=30  # Request timeout in seconds
)
```

### Strategy Parameters

In `LLM_Momentum_Strategy`, you can optimize these parameters:

- `buy_rsi_threshold` - RSI level for buy pre-condition (default: 30)
- `sell_rsi_threshold` - RSI level for sell pre-condition (default: 70)
- `llm_confidence_threshold` - Minimum LLM confidence required (default: 0.7)

Use Freqtrade's hyperopt to optimize:

```bash
freqtrade hyperopt --strategy LLM_Momentum_Strategy --hyperopt-loss SharpeHyperOptLoss
```

## Best Practices

### 1. Use Technical Pre-Conditions

Don't query the LLM for every candle. Use technical indicators to filter:

```python
# Only ask LLM when technically favorable
if rsi < 30 and volume > volume_mean:
    signal = self.llm_provider.get_signal(...)
```

### 2. Set Confidence Thresholds

Only act on high-confidence LLM signals:

```python
if signal['confidence'] >= 0.75:
    dataframe.loc[dataframe.index[-1], 'enter_long'] = 1
```

### 3. Implement Fallbacks

Always handle LLM unavailability:

```python
try:
    signal = self.llm_provider.get_signal(...)
except Exception:
    # Fall back to technical indicators only
    dataframe['enter_long'] = technical_conditions
```

### 4. Monitor LLM Costs

LLM API calls cost money. Track usage:

```python
# Check health before making many requests
health = self.llm_provider.health_check()
if not health.get('configured'):
    # Use technical-only mode
    pass
```

### 5. Backtest Thoroughly

LLM behavior can be non-deterministic. Backtest extensively:

```bash
freqtrade backtesting --strategy LLM_Momentum_Strategy --timerange 20240101-20240301
```

## Troubleshooting

### LLM Signal Provider Not Working

1. **Check Django backend is running:**
   ```bash
   curl http://localhost:8000/api/v1/strategies/llm
   ```

2. **Verify environment variables:**
   ```bash
   echo $DJANGO_API_URL
   ```

3. **Check backend logs** for LLM API errors

4. **Test health endpoint:**
   ```python
   provider = LLMSignalProvider()
   print(provider.health_check())
   ```

### Low Confidence Signals

If LLM consistently returns low confidence:

- Review the market data being sent
- Ensure indicators are calculated correctly
- Check LLM prompts in `backend/llm_service/orchestrator.py`
- Consider using a different LLM model

### High API Costs

To reduce LLM API usage:

- Increase `llm_confidence_threshold`
- Add more restrictive technical pre-conditions
- Use longer timeframes (less frequent calls)
- Consider caching signals for same market conditions

## Performance Notes

- **Latency**: LLM calls add 2-10s latency per signal
- **Cost**: Anthropic Claude ~$0.003 per signal, GPT ~$0.001-0.005
- **Reliability**: Fall back to technical indicators if LLM unavailable
- **Frequency**: Recommended max 1 call per minute per pair

## Examples

See `strategies/LLM_Momentum_Strategy.py` for a complete working example.

## Support

For issues or questions:
- Check logs: `tail -f logs/freqtrade.log`
- Review Django backend logs
- Open an issue in the main repository

## License

MIT
