"""
LLM Signal Provider for Freqtrade
Allows Freqtrade strategies to leverage LLM-generated trading signals

This adapter communicates with the Django backend API which orchestrates
LLM calls to Claude or GPT for trading analysis.
"""
import os
import requests
import pandas as pd
import logging
from typing import Dict, Any, Optional, Literal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class LLMSignalProvider:
    """
    Provider class that enables Freqtrade strategies to get trading signals from LLMs

    Usage in Freqtrade strategy:
        from llm_signal_provider import LLMSignalProvider

        class MyStrategy(IStrategy):
            def __init__(self, config: dict) -> None:
                super().__init__(config)
                self.llm_provider = LLMSignalProvider()

            def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                signal = self.llm_provider.get_signal(
                    dataframe=dataframe,
                    pair=metadata['pair'],
                    timeframe=self.timeframe
                )
                if signal['decision'] == 'BUY' and signal['confidence'] > 0.7:
                    dataframe.loc[dataframe.index[-1], 'enter_long'] = 1
                return dataframe
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        provider: Optional[Literal["anthropic", "openai"]] = None,
        timeout: int = 30,
    ):
        """
        Initialize LLM Signal Provider

        Args:
            api_url: URL of the Django backend API (defaults to env var)
            provider: LLM provider to use ('anthropic' or 'openai')
            timeout: Request timeout in seconds
        """
        self.api_url = (api_url or os.getenv("DJANGO_API_URL", "http://localhost:8000")).rstrip("/")
        self.provider = provider
        self.timeout = timeout
        self.endpoint = f"{self.api_url}/api/v1/strategies/llm"

        logger.info(f"LLM Signal Provider initialized with API: {self.api_url}")

    def get_signal(
        self,
        dataframe: pd.DataFrame,
        pair: str,
        timeframe: str = "5m",
        indicators: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Get trading signal from LLM based on market data

        Args:
            dataframe: Pandas DataFrame with OHLCV and indicator data
            pair: Trading pair (e.g., "BTC/USDT")
            timeframe: Timeframe of the data (e.g., "5m", "1h")
            indicators: Dict mapping indicator names to dataframe column names
                       e.g., {"rsi": "rsi", "ema_short": "ema_20"}

        Returns:
            Dictionary with signal data:
            {
                "decision": "BUY" | "SELL" | "HOLD",
                "confidence": 0.0 to 1.0,
                "reasoning": str,
                "risk_level": "low" | "medium" | "high",
                "suggested_stop_loss": float (optional),
                "suggested_take_profit": float (optional),
                "pair": str,
                "timeframe": str,
                "provider": str,
                "model": str
            }
        """
        try:
            # Extract market data from dataframe
            market_data = self._extract_market_data(dataframe, indicators)

            # Get current price
            current_price = float(dataframe["close"].iloc[-1])

            # Prepare request payload
            payload = {
                "market_data": market_data,
                "pair": pair,
                "timeframe": timeframe,
                "current_price": current_price,
            }

            if self.provider:
                payload["provider"] = self.provider

            # Make API request
            logger.info(f"Requesting LLM signal for {pair} on {timeframe}")
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            signal = response.json()
            logger.info(
                f"Received signal for {pair}: {signal['decision']} "
                f"(confidence: {signal['confidence']:.2f})"
            )

            return signal

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get LLM signal: {e}")
            # Return neutral signal on error
            return self._get_neutral_signal(pair, timeframe, str(e))

        except Exception as e:
            logger.error(f"Unexpected error in get_signal: {e}")
            return self._get_neutral_signal(pair, timeframe, str(e))

    def _extract_market_data(
        self,
        dataframe: pd.DataFrame,
        indicators: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract relevant market data from dataframe

        Args:
            dataframe: OHLCV dataframe with indicators
            indicators: Mapping of indicator names to column names

        Returns:
            Dictionary of market data suitable for LLM analysis
        """
        data = {}

        # Default indicators to extract if not specified
        default_indicators = {
            "rsi": "rsi",
            "ema_short": "ema_20",
            "ema_long": "ema_50",
            "macd": "macd",
            "macd_signal": "macdsignal",
            "bb_upper": "bb_upperband",
            "bb_middle": "bb_middleband",
            "bb_lower": "bb_lowerband",
            "volume": "volume",
        }

        indicators = indicators or default_indicators

        # Extract indicator values (most recent)
        for indicator_name, column_name in indicators.items():
            if column_name in dataframe.columns:
                value = dataframe[column_name].iloc[-1]
                if pd.notna(value):
                    data[indicator_name] = float(value)

        # Add recent OHLCV data (last 10 candles)
        recent_candles = []
        for i in range(min(10, len(dataframe))):
            idx = -(10 - i)
            candle = {
                "open": float(dataframe["open"].iloc[idx]),
                "high": float(dataframe["high"].iloc[idx]),
                "low": float(dataframe["low"].iloc[idx]),
                "close": float(dataframe["close"].iloc[idx]),
                "volume": float(dataframe["volume"].iloc[idx]),
            }
            recent_candles.append(candle)

        data["recent_candles"] = recent_candles

        # Add price change metrics
        if len(dataframe) >= 24:
            price_24h_ago = dataframe["close"].iloc[-24]
            current_price = dataframe["close"].iloc[-1]
            data["price_change_24h"] = float(
                ((current_price - price_24h_ago) / price_24h_ago) * 100
            )

        return data

    def _get_neutral_signal(
        self,
        pair: str,
        timeframe: str,
        error: str = "",
    ) -> Dict[str, Any]:
        """
        Return a neutral (HOLD) signal when LLM is unavailable

        Args:
            pair: Trading pair
            timeframe: Timeframe
            error: Error message

        Returns:
            Neutral signal dictionary
        """
        return {
            "decision": "HOLD",
            "confidence": 0.0,
            "reasoning": f"LLM signal unavailable: {error}",
            "risk_level": "high",
            "pair": pair,
            "timeframe": timeframe,
            "provider": "none",
            "model": "none",
            "error": error,
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Check if LLM service is available

        Returns:
            Health status dictionary
        """
        try:
            response = requests.get(
                self.endpoint,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "configured": False,
                "error": str(e),
            }
