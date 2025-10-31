"""
LLM Momentum Strategy for Freqtrade
Combines traditional technical indicators with LLM-based analysis
for trading signal generation

This is an example strategy demonstrating how to integrate the
LLM Signal Provider into a Freqtrade trading strategy.
"""
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta
import logging

# Import the LLM Signal Provider
# Note: Adjust the import path based on where you place the adapter
import sys
from pathlib import Path

# Add the adapters directory to the path
adapter_path = Path(__file__).parent.parent / "adapters"
sys.path.insert(0, str(adapter_path))

from llm_signal_provider import LLMSignalProvider

logger = logging.getLogger(__name__)


class LLM_Momentum_Strategy(IStrategy):
    """
    Hybrid strategy that combines:
    1. Technical indicators (RSI, EMA, MACD, Bollinger Bands)
    2. LLM-based market analysis and decision making

    The strategy uses traditional indicators to populate the dataframe,
    then consults an LLM for final buy/sell decisions based on current
    market conditions and indicator values.

    Configuration:
    - Set DJANGO_API_URL environment variable to your backend API
    - Ensure backend is running with LLM service configured
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # Minimal ROI designed for momentum trades
    minimal_roi = {
        "0": 0.15,   # 15% profit
        "30": 0.08,  # 8% after 30 minutes
        "60": 0.04,  # 4% after 1 hour
        "120": 0.02, # 2% after 2 hours
    }

    # Optimal stoploss
    stoploss = -0.05  # -5% stop loss

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02

    # Timeframe
    timeframe = "5m"

    # Run "populate_indicators()" only for new candles
    process_only_new_candles = True

    # Strategy parameters
    buy_rsi_threshold = IntParameter(20, 40, default=30, space="buy")
    sell_rsi_threshold = IntParameter(60, 80, default=70, space="sell")
    llm_confidence_threshold = DecimalParameter(
        0.5, 0.9, default=0.7, space="buy", decimals=2
    )

    def __init__(self, config: dict) -> None:
        """Initialize strategy and LLM provider"""
        super().__init__(config)

        # Initialize LLM Signal Provider
        try:
            self.llm_provider = LLMSignalProvider()
            llm_health = self.llm_provider.health_check()
            if llm_health.get("configured"):
                logger.info(
                    f"LLM Provider initialized: {llm_health.get('provider')} - "
                    f"{llm_health.get('model')}"
                )
            else:
                logger.warning(
                    "LLM Provider not fully configured. "
                    "Strategy will fall back to technical-only signals."
                )
                self.llm_provider = None
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            self.llm_provider = None

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add technical indicators to dataframe

        These indicators will be used both for the strategy logic
        and sent to the LLM for analysis.
        """
        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # EMAs
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)

        # MACD
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        # Bollinger Bands
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2, nbdevdn=2)
        dataframe["bb_lowerband"] = bollinger["lowerband"]
        dataframe["bb_middleband"] = bollinger["middleband"]
        dataframe["bb_upperband"] = bollinger["upperband"]

        # Volume
        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate buy signal using hybrid approach:
        1. Check technical indicators for favorable conditions
        2. Consult LLM for final decision
        """
        # Start with no entry signals
        dataframe["enter_long"] = 0

        # Only generate signal for the most recent candle
        if len(dataframe) < 200:  # Need enough data for indicators
            return dataframe

        # Technical pre-conditions (must be met before asking LLM)
        technical_conditions = (
            (dataframe["rsi"] < self.buy_rsi_threshold.value) &  # Oversold
            (dataframe["close"] > dataframe["ema_200"]) &  # Above long-term trend
            (dataframe["volume"] > dataframe["volume_mean"])  # Above average volume
        )

        # Get the most recent index where conditions are met
        if not technical_conditions.iloc[-1]:
            return dataframe

        # If technical conditions met, consult LLM
        if self.llm_provider:
            try:
                signal = self.llm_provider.get_signal(
                    dataframe=dataframe,
                    pair=metadata["pair"],
                    timeframe=self.timeframe,
                )

                # Enter long if LLM recommends BUY with sufficient confidence
                if (
                    signal["decision"] == "BUY"
                    and signal["confidence"] >= self.llm_confidence_threshold.value
                ):
                    dataframe.loc[dataframe.index[-1], "enter_long"] = 1
                    logger.info(
                        f"LLM BUY signal for {metadata['pair']}: "
                        f"Confidence {signal['confidence']:.2f} - "
                        f"{signal['reasoning']}"
                    )

            except Exception as e:
                logger.error(f"Error getting LLM signal for entry: {e}")
                # Fall back to technical-only signal
                dataframe.loc[
                    dataframe.index[-1], "enter_long"
                ] = 1 if technical_conditions.iloc[-1] else 0

        else:
            # No LLM available - use technical indicators only
            dataframe["enter_long"] = technical_conditions.astype(int)

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate sell signal using hybrid approach
        """
        # Start with no exit signals
        dataframe["exit_long"] = 0

        if len(dataframe) < 200:
            return dataframe

        # Technical exit conditions
        technical_exit = (
            (dataframe["rsi"] > self.sell_rsi_threshold.value) |  # Overbought
            (dataframe["close"] < dataframe["ema_20"])  # Below short-term trend
        )

        if not technical_exit.iloc[-1]:
            return dataframe

        # Consult LLM for exit decision
        if self.llm_provider:
            try:
                signal = self.llm_provider.get_signal(
                    dataframe=dataframe,
                    pair=metadata["pair"],
                    timeframe=self.timeframe,
                )

                # Exit if LLM recommends SELL with sufficient confidence
                if (
                    signal["decision"] == "SELL"
                    and signal["confidence"] >= self.llm_confidence_threshold.value
                ):
                    dataframe.loc[dataframe.index[-1], "exit_long"] = 1
                    logger.info(
                        f"LLM SELL signal for {metadata['pair']}: "
                        f"Confidence {signal['confidence']:.2f} - "
                        f"{signal['reasoning']}"
                    )

            except Exception as e:
                logger.error(f"Error getting LLM signal for exit: {e}")
                # Fall back to technical-only signal
                dataframe.loc[
                    dataframe.index[-1], "exit_long"
                ] = 1 if technical_exit.iloc[-1] else 0

        else:
            # No LLM available - use technical indicators only
            dataframe["exit_long"] = technical_exit.astype(int)

        return dataframe
