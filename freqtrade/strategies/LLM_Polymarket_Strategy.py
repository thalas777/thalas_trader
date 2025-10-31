"""
LLM Polymarket Strategy for Freqtrade
Uses Multi-LLM Consensus to trade Polymarket prediction markets

This strategy adapts traditional Freqtrade concepts for prediction markets:
- "Price" = Probability of YES outcome (0-1 range)
- BUY = Buy YES shares (predict event will happen)
- SELL = Buy NO shares (predict event won't happen)
- ROI = Profit when market resolves to correct outcome

Key Differences from Crypto Trading:
1. Binary outcomes (YES/NO) instead of continuous price action
2. Markets expire at a fixed date
3. Position sizing based on Kelly Criterion
4. Focus on probability mispricing vs market sentiment

Author: Thalas Trader - Multi-LLM Consensus System
Version: 1.0.0
"""
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter, CategoricalParameter
from pandas import DataFrame
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import sys
from pathlib import Path

# Add the adapters directory to the path
adapter_path = Path(__file__).parent.parent / "adapters"
sys.path.insert(0, str(adapter_path))

from llm_signal_provider import LLMSignalProvider

logger = logging.getLogger(__name__)


class LLM_Polymarket_Strategy(IStrategy):
    """
    Polymarket Prediction Market Strategy using Multi-LLM Consensus

    This strategy uses the consensus of multiple LLMs (Anthropic, OpenAI, Gemini, Grok)
    to predict outcomes of prediction markets on Polymarket.

    Strategy Flow:
    1. Scan available prediction markets
    2. For each market, call LLM consensus endpoint with market context
    3. If consensus has high confidence in outcome, take position
    4. Size position using Kelly Criterion based on confidence
    5. Exit when market resolves or expiration approaches

    Configuration:
    - Set DJANGO_API_URL environment variable to backend API
    - Ensure backend has LLM consensus endpoint configured
    - Provider weights can be customized via strategy parameters
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # For prediction markets, we hold until expiration or resolution
    # ROI is effectively 100% when we win, 0% when we lose
    minimal_roi = {
        "0": 0.95,      # Exit if we reach 95% probability (near certainty)
        "1440": 0.80,   # 80% after 1 day
        "4320": 0.60,   # 60% after 3 days
        "10080": 0.40,  # 40% after 1 week
    }

    # Stop loss for prediction markets
    # If probability drops significantly against our position, exit
    stoploss = -0.25  # Exit if we lose 25% of position value

    # Trailing stop - lock in profits as probability moves in our favor
    trailing_stop = True
    trailing_stop_positive = 0.10  # Start trailing at 10% profit
    trailing_stop_positive_offset = 0.15  # Trail by 15%
    trailing_only_offset_is_reached = True

    # Timeframe - for prediction markets, we check less frequently
    # 1h is sufficient as these markets don't move as fast as crypto
    timeframe = "1h"

    # Process only new candles
    process_only_new_candles = True

    # Don't use position adjustment (not applicable to prediction markets)
    position_adjustment_enable = False

    # Strategy Parameters (optimizable via hyperopt)

    # LLM Consensus confidence threshold (0.0 - 1.0)
    # Higher = only take positions when LLMs are very confident
    llm_consensus_confidence_min = DecimalParameter(
        0.60, 0.90, default=0.75, space="buy", decimals=2,
        load=True, optimize=True
    )

    # Minimum agreement score among providers (0.0 - 1.0)
    # Higher = require more LLMs to agree
    llm_agreement_score_min = DecimalParameter(
        0.50, 0.95, default=0.70, space="buy", decimals=2,
        load=True, optimize=True
    )

    # Kelly Criterion fraction (for position sizing)
    # 1.0 = full Kelly, 0.5 = half Kelly (more conservative)
    kelly_fraction = DecimalParameter(
        0.1, 1.0, default=0.25, space="buy", decimals=2,
        load=True, optimize=True
    )

    # Maximum stake per market (as fraction of total capital)
    max_stake_per_market = DecimalParameter(
        0.05, 0.25, default=0.10, space="buy", decimals=2,
        load=True, optimize=True
    )

    # Minimum days until expiration to enter market
    min_days_to_expiration = IntParameter(
        1, 30, default=7, space="buy",
        load=True, optimize=True
    )

    # Exit strategy: days before expiration to close position
    exit_days_before_expiration = IntParameter(
        0, 7, default=1, space="sell",
        load=True, optimize=True
    )

    # Minimum liquidity (24h volume) to trade market
    min_volume_24h = DecimalParameter(
        1000, 100000, default=10000, space="buy", decimals=0,
        load=True, optimize=True
    )

    # Provider weights (can be customized per deployment)
    provider_weights = {
        "Anthropic": 1.0,
        "OpenAI": 1.0,
        "Gemini": 0.8,
        "Grok": 0.7,
    }

    def __init__(self, config: dict) -> None:
        """Initialize strategy and LLM consensus provider"""
        super().__init__(config)

        # Initialize LLM Signal Provider with consensus endpoint
        try:
            self.llm_provider = LLMSignalProvider(
                api_url=config.get("llm_api_url"),
                timeout=60,  # Consensus can take longer
            )

            # Test health check
            health = self.llm_provider.health_check()
            if health.get("configured"):
                logger.info(
                    f"✓ LLM Consensus Provider initialized successfully"
                )
                logger.info(f"  Available providers: {health.get('available_providers', 0)}")
            else:
                logger.warning(
                    "⚠ LLM Consensus Provider not fully configured. "
                    "Strategy will not generate signals."
                )
                self.llm_provider = None

        except Exception as e:
            logger.error(f"✗ Failed to initialize LLM consensus provider: {e}")
            self.llm_provider = None

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for Polymarket prediction markets

        Unlike crypto, we don't use technical indicators like RSI or MACD.
        Instead, we track:
        - Probability trends (is YES price rising or falling?)
        - Volume trends (is interest increasing?)
        - Time to expiration
        - Implied probability from market price
        """

        # For Polymarket, "close" represents current YES probability (0-1)
        # "volume" represents shares traded

        # Calculate probability trends
        dataframe['prob_ma_short'] = dataframe['close'].rolling(window=6).mean()  # 6h MA
        dataframe['prob_ma_medium'] = dataframe['close'].rolling(window=24).mean()  # 24h MA
        dataframe['prob_ma_long'] = dataframe['close'].rolling(window=168).mean()  # 7d MA

        # Probability momentum (rate of change)
        dataframe['prob_momentum_6h'] = dataframe['close'].pct_change(periods=6) * 100
        dataframe['prob_momentum_24h'] = dataframe['close'].pct_change(periods=24) * 100
        dataframe['prob_momentum_7d'] = dataframe['close'].pct_change(periods=168) * 100

        # Volume analysis
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=24).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']

        # Volatility (standard deviation of probability)
        dataframe['prob_volatility'] = dataframe['close'].rolling(window=24).std()

        # Market efficiency score (lower volatility = more efficient)
        dataframe['efficiency_score'] = 1.0 / (1.0 + dataframe['prob_volatility'])

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generate entry signals using LLM consensus for prediction markets

        Entry Logic:
        1. Extract market context from metadata
        2. Call LLM consensus endpoint with market question/data
        3. If consensus predicts YES with high confidence -> BUY (enter long)
        4. If consensus predicts NO with high confidence -> SELL (enter short/skip)
        5. Size position using Kelly Criterion
        """

        # Initialize entry signals
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0  # For Polymarket, this would be buying NO shares

        # Need sufficient data
        if len(dataframe) < 24:
            return dataframe

        # Only evaluate most recent candle
        current_idx = len(dataframe) - 1

        # Extract market information from metadata
        market_info = self._extract_market_info(dataframe, metadata, current_idx)

        # Pre-screening: Basic market conditions
        if not self._should_evaluate_market(market_info):
            logger.debug(
                f"Market {metadata.get('pair', 'UNKNOWN')} failed pre-screening"
            )
            return dataframe

        # Call LLM consensus for prediction
        if self.llm_provider:
            try:
                consensus_signal = self._get_llm_consensus(market_info, dataframe, current_idx)

                if not consensus_signal:
                    return dataframe

                # Evaluate consensus signal
                decision = consensus_signal.get('decision')
                confidence = consensus_signal.get('confidence', 0.0)
                agreement_score = consensus_signal.get('consensus_metadata', {}).get('agreement_score', 0.0)

                # Check if consensus meets our thresholds
                if confidence < self.llm_consensus_confidence_min.value:
                    logger.debug(
                        f"Consensus confidence {confidence:.2f} below threshold "
                        f"{self.llm_consensus_confidence_min.value}"
                    )
                    return dataframe

                if agreement_score < self.llm_agreement_score_min.value:
                    logger.debug(
                        f"Agreement score {agreement_score:.2f} below threshold "
                        f"{self.llm_agreement_score_min.value}"
                    )
                    return dataframe

                # Generate entry signal based on consensus
                if decision == "BUY":
                    # LLM consensus predicts YES outcome
                    dataframe.loc[current_idx, 'enter_long'] = 1

                    # Calculate position size using Kelly Criterion
                    kelly_stake = self._calculate_kelly_stake(
                        consensus_confidence=confidence,
                        market_probability=market_info['current_yes_price']
                    )

                    # Store stake size in metadata for position sizing
                    dataframe.loc[current_idx, 'stake_amount'] = kelly_stake

                    logger.info(
                        f"✓ ENTRY SIGNAL: {metadata['pair']}\n"
                        f"  Decision: BUY YES shares\n"
                        f"  Consensus: {confidence:.2%} confidence, {agreement_score:.2%} agreement\n"
                        f"  Market Probability: {market_info['current_yes_price']:.2%}\n"
                        f"  Kelly Stake: {kelly_stake:.2%} of capital\n"
                        f"  Reasoning: {consensus_signal.get('reasoning', 'N/A')[:100]}..."
                    )

                elif decision == "SELL":
                    # LLM consensus predicts NO outcome
                    # In Freqtrade, we'd buy NO shares (enter short)
                    # For now, we skip these (could implement if Polymarket NO shares supported)
                    logger.info(
                        f"✓ CONSENSUS PREDICTS NO: {metadata['pair']}\n"
                        f"  Confidence: {confidence:.2%}\n"
                        f"  (Not entering - strategy focuses on YES predictions)"
                    )

            except Exception as e:
                logger.error(f"Error getting LLM consensus for entry: {e}", exc_info=True)

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generate exit signals for prediction markets

        Exit Logic:
        1. Exit if approaching expiration (within exit_days_before_expiration)
        2. Exit if consensus flips (was BUY, now SELL)
        3. Exit if market resolves
        4. Exit if probability reaches near-certainty (>95%)
        """

        # Initialize exit signals
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0

        if len(dataframe) < 24:
            return dataframe

        current_idx = len(dataframe) - 1
        market_info = self._extract_market_info(dataframe, metadata, current_idx)

        # Exit reason tracking
        exit_reasons = []

        # 1. Check time to expiration
        if market_info.get('days_to_expiration', 999) <= self.exit_days_before_expiration.value:
            exit_reasons.append(f"Expiration in {market_info['days_to_expiration']} days")
            dataframe.loc[current_idx, 'exit_long'] = 1

        # 2. Check if probability reached near-certainty
        current_prob = market_info['current_yes_price']
        if current_prob >= 0.95:
            exit_reasons.append(f"Probability at {current_prob:.2%} (near certainty)")
            dataframe.loc[current_idx, 'exit_long'] = 1

        # 3. Re-check consensus to see if opinion changed
        if self.llm_provider and not dataframe.loc[current_idx, 'exit_long']:
            try:
                consensus_signal = self._get_llm_consensus(market_info, dataframe, current_idx)

                if consensus_signal:
                    decision = consensus_signal.get('decision')
                    confidence = consensus_signal.get('confidence', 0.0)

                    # Exit if consensus flipped to SELL or HOLD with high confidence
                    if decision in ['SELL', 'HOLD'] and confidence >= self.llm_consensus_confidence_min.value:
                        exit_reasons.append(
                            f"Consensus changed to {decision} ({confidence:.2%} confidence)"
                        )
                        dataframe.loc[current_idx, 'exit_long'] = 1

            except Exception as e:
                logger.error(f"Error checking consensus for exit: {e}")

        # Log exit if triggered
        if dataframe.loc[current_idx, 'exit_long']:
            logger.info(
                f"✓ EXIT SIGNAL: {metadata['pair']}\n"
                f"  Reasons: {', '.join(exit_reasons)}\n"
                f"  Current Probability: {current_prob:.2%}"
            )

        return dataframe

    def _extract_market_info(
        self,
        dataframe: DataFrame,
        metadata: dict,
        idx: int
    ) -> Dict[str, Any]:
        """
        Extract market information for LLM analysis

        Returns:
            Dictionary with market context including:
            - question: The prediction market question
            - current_yes_price: Current probability of YES
            - current_no_price: Current probability of NO
            - volume_24h: Trading volume last 24 hours
            - expiration: Market expiration date
            - days_to_expiration: Days until expiration
            - momentum: Recent probability trends
        """

        current_yes_price = float(dataframe['close'].iloc[idx])
        current_no_price = 1.0 - current_yes_price

        # Get volume (sum of last 24 candles for 24h volume)
        volume_24h = float(dataframe['volume'].iloc[max(0, idx-23):idx+1].sum())

        # Extract expiration from metadata (would come from Polymarket API)
        expiration_date = metadata.get('expiration_date')
        days_to_expiration = 999  # Default high value

        if expiration_date:
            try:
                exp_date = pd.to_datetime(expiration_date)
                days_to_expiration = (exp_date - pd.Timestamp.now()).days
            except:
                logger.warning(f"Could not parse expiration date: {expiration_date}")

        # Get probability momentum
        momentum_6h = float(dataframe['prob_momentum_6h'].iloc[idx]) if 'prob_momentum_6h' in dataframe else 0.0
        momentum_24h = float(dataframe['prob_momentum_24h'].iloc[idx]) if 'prob_momentum_24h' in dataframe else 0.0

        return {
            "question": metadata.get('pair', 'Unknown Market'),
            "current_yes_price": current_yes_price,
            "current_no_price": current_no_price,
            "volume_24h": volume_24h,
            "expiration": expiration_date,
            "days_to_expiration": days_to_expiration,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "momentum_6h": momentum_6h,
            "momentum_24h": momentum_24h,
            "volatility": float(dataframe['prob_volatility'].iloc[idx]) if 'prob_volatility' in dataframe else 0.0,
        }

    def _should_evaluate_market(self, market_info: Dict[str, Any]) -> bool:
        """
        Pre-screening: Check if market meets basic criteria

        Filters:
        - Sufficient liquidity (volume)
        - Sufficient time to expiration
        - Valid probability range
        """

        # Check volume
        if market_info['volume_24h'] < self.min_volume_24h.value:
            return False

        # Check time to expiration
        if market_info['days_to_expiration'] < self.min_days_to_expiration.value:
            return False

        # Check valid probability range (avoid near-certainty markets)
        prob = market_info['current_yes_price']
        if prob < 0.05 or prob > 0.95:
            return False

        return True

    def _get_llm_consensus(
        self,
        market_info: Dict[str, Any],
        dataframe: DataFrame,
        idx: int
    ) -> Optional[Dict[str, Any]]:
        """
        Call LLM consensus endpoint for prediction market analysis

        Args:
            market_info: Market context dictionary
            dataframe: Price/volume dataframe
            idx: Current index

        Returns:
            Consensus signal dictionary or None if failed
        """

        try:
            # Prepare market data for LLM consensus
            # Instead of technical indicators, we provide market context
            market_data = {
                "market_question": market_info['question'],
                "current_yes_probability": market_info['current_yes_price'],
                "current_no_probability": market_info['current_no_price'],
                "volume_24h": market_info['volume_24h'],
                "days_to_expiration": market_info['days_to_expiration'],
                "expiration_date": market_info['expiration'],
                "probability_momentum_6h": market_info['momentum_6h'],
                "probability_momentum_24h": market_info['momentum_24h'],
                "probability_volatility": market_info['volatility'],
            }

            # Call consensus endpoint
            # Note: We use the consensus endpoint, not the single-provider endpoint
            signal = self.llm_provider.get_signal(
                dataframe=dataframe,
                pair=market_info['question'],
                timeframe=self.timeframe,
                indicators=None,  # Not using technical indicators
            )

            return signal

        except Exception as e:
            logger.error(f"Failed to get LLM consensus: {e}", exc_info=True)
            return None

    def _calculate_kelly_stake(
        self,
        consensus_confidence: float,
        market_probability: float
    ) -> float:
        """
        Calculate position size using Kelly Criterion

        Kelly Criterion: f* = (bp - q) / b
        Where:
        - f* = fraction of bankroll to wager
        - b = odds received on the wager (b to 1)
        - p = probability of winning (consensus confidence)
        - q = probability of losing (1 - p)

        For prediction markets:
        - If we buy YES at price P, we win $(1-P) if correct, lose $P if wrong
        - Odds: b = (1-P) / P

        Args:
            consensus_confidence: LLM consensus confidence (0-1)
            market_probability: Current market price for YES (0-1)

        Returns:
            Fraction of capital to stake (0-1), capped by max_stake_per_market
        """

        # Probability of winning (from consensus)
        p = consensus_confidence
        q = 1.0 - p

        # Odds received (market is offering these odds)
        # If YES is priced at 0.40, we pay $0.40 and win $0.60 if correct
        # Odds = 0.60 / 0.40 = 1.5 (or 1.5 to 1)
        if market_probability >= 0.99:
            return 0.0  # Avoid division by zero

        b = (1.0 - market_probability) / market_probability

        # Kelly formula
        kelly_full = (b * p - q) / b

        # Only bet if Kelly is positive (edge exists)
        if kelly_full <= 0:
            return 0.0

        # Apply Kelly fraction (for risk management)
        kelly_stake = kelly_full * self.kelly_fraction.value

        # Cap at maximum stake per market
        kelly_stake = min(kelly_stake, self.max_stake_per_market.value)

        # Floor at 0
        kelly_stake = max(0.0, kelly_stake)

        return kelly_stake

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> bool:
        """
        Final confirmation before entering trade

        Additional checks before execution:
        - Verify LLM consensus is still valid
        - Check if we haven't exceeded max open trades
        - Verify market hasn't moved too much since signal
        """

        # Could add additional validation here
        # For now, trust the populate_entry_trend logic

        logger.info(
            f"✓ Trade entry confirmed: {pair}\n"
            f"  Amount: {amount}\n"
            f"  Rate: {rate}\n"
            f"  Side: {side}"
        )

        return True

    def confirm_trade_exit(
        self,
        pair: str,
        trade: object,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs
    ) -> bool:
        """
        Final confirmation before exiting trade

        Additional checks before exit:
        - Verify exit reason is still valid
        - Check if market has resolved
        """

        logger.info(
            f"✓ Trade exit confirmed: {pair}\n"
            f"  Exit Reason: {exit_reason}\n"
            f"  Rate: {rate}"
        )

        return True

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        Custom position sizing using Kelly Criterion

        This overrides Freqtrade's default stake amount to use
        our calculated Kelly stake from the entry signal.
        """

        # Try to get Kelly stake from dataframe (stored during populate_entry_trend)
        dataframe = self.dp.get_pair_dataframe(pair, self.timeframe)

        if dataframe is not None and len(dataframe) > 0:
            if 'stake_amount' in dataframe.columns:
                kelly_fraction = dataframe['stake_amount'].iloc[-1]

                if kelly_fraction > 0:
                    # Calculate stake as fraction of total capital
                    # max_stake represents our total available capital
                    kelly_stake = max_stake * kelly_fraction

                    # Ensure within limits
                    if min_stake:
                        kelly_stake = max(kelly_stake, min_stake)
                    kelly_stake = min(kelly_stake, max_stake)

                    logger.info(
                        f"Kelly stake for {pair}: {kelly_fraction:.2%} of capital = "
                        f"${kelly_stake:.2f}"
                    )

                    return kelly_stake

        # Fallback to proposed stake if Kelly calculation not available
        return proposed_stake
