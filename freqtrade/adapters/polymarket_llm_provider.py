"""
Polymarket LLM Consensus Provider
Specialized adapter for prediction markets using multi-LLM consensus

This adapter extends the base LLM Signal Provider to work specifically
with Polymarket prediction markets, calling the consensus endpoint with
market-specific context.

Key Differences from Crypto Signal Provider:
1. Uses market question/context instead of technical indicators
2. Calls /api/v1/strategies/llm-consensus for multi-provider consensus
3. Interprets probability-based market data
4. Returns predictions about binary outcomes (YES/NO)

Author: Thalas Trader - Multi-LLM Consensus System
Version: 1.0.0
"""
import os
import requests
import pandas as pd
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class PolymarketLLMProvider:
    """
    Polymarket-specific LLM Consensus Provider

    Connects Freqtrade strategies to the Django backend's multi-LLM
    consensus system for prediction market analysis.

    Usage in Freqtrade strategy:
        from polymarket_llm_provider import PolymarketLLMProvider

        class MyPolymarketStrategy(IStrategy):
            def __init__(self, config: dict) -> None:
                super().__init__(config)
                self.llm_provider = PolymarketLLMProvider()

            def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                market_context = {
                    "question": "Will Bitcoin reach $100k by end of 2025?",
                    "current_yes_price": 0.45,
                    "expiration_date": "2025-12-31"
                }

                consensus = self.llm_provider.get_market_prediction(
                    market_context=market_context
                )

                if consensus['decision'] == 'BUY' and consensus['confidence'] > 0.75:
                    # High confidence prediction of YES outcome
                    dataframe.loc[dataframe.index[-1], 'enter_long'] = 1

                return dataframe
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        provider_weights: Optional[Dict[str, float]] = None,
        timeout: int = 60,
    ):
        """
        Initialize Polymarket LLM Consensus Provider

        Args:
            api_url: URL of the Django backend API (defaults to env var)
            provider_weights: Optional custom weights for LLM providers
                             e.g., {"Anthropic": 1.0, "OpenAI": 0.9, "Gemini": 0.8}
            timeout: Request timeout in seconds (consensus can take longer)
        """
        self.api_url = (api_url or os.getenv("DJANGO_API_URL", "http://localhost:8000")).rstrip("/")
        self.provider_weights = provider_weights or {
            "Anthropic": 1.0,
            "OpenAI": 1.0,
            "Gemini": 0.8,
            "Grok": 0.7,
        }
        self.timeout = timeout

        # Use consensus endpoint
        self.endpoint = f"{self.api_url}/api/v1/strategies/llm-consensus"

        logger.info(f"Polymarket LLM Consensus Provider initialized")
        logger.info(f"  API: {self.api_url}")
        logger.info(f"  Provider weights: {self.provider_weights}")

    def get_market_prediction(
        self,
        market_context: Dict[str, Any],
        include_provider_breakdown: bool = False,
    ) -> Dict[str, Any]:
        """
        Get LLM consensus prediction for a prediction market

        Args:
            market_context: Dictionary with market information:
                {
                    "question": "Will Bitcoin reach $100k by end of 2025?",
                    "current_yes_price": 0.45,  # Current probability of YES
                    "current_no_price": 0.55,   # Current probability of NO
                    "volume_24h": 50000,        # 24h trading volume
                    "expiration_date": "2025-12-31",
                    "days_to_expiration": 60,
                    "current_date": "2025-10-30",
                    "momentum_6h": 2.5,         # % change in 6h
                    "momentum_24h": 5.0,        # % change in 24h
                    "volatility": 0.05          # Probability volatility
                }
            include_provider_breakdown: Include individual provider responses

        Returns:
            Dictionary with consensus prediction:
            {
                "decision": "BUY" | "SELL" | "HOLD",  # BUY=predict YES, SELL=predict NO
                "confidence": 0.82,
                "reasoning": "Consensus analysis: ...",
                "risk_level": "medium",
                "suggested_stop_loss": float (optional),
                "suggested_take_profit": float (optional),

                # Consensus metadata
                "consensus_metadata": {
                    "total_providers": 4,
                    "participating_providers": 3,
                    "agreement_score": 0.75,
                    "weighted_confidence": 0.82,
                    "vote_breakdown": {"BUY": 3, "HOLD": 1},
                    "weighted_votes": {"BUY": 2.4, "HOLD": 0.6, "SELL": 0.0},
                    "total_latency_ms": 1850.5,
                    "total_cost_usd": 0.0234,
                    "total_tokens": 2450,
                },

                # Individual provider responses (if requested)
                "provider_responses": [...]
            }
        """
        try:
            # Extract market question (used as "pair" for API)
            question = market_context.get("question", "Unknown Market")

            # Current YES probability (used as "current_price")
            current_yes_price = market_context.get("current_yes_price", 0.5)

            # Prepare market data payload for LLM consensus
            # This differs from crypto - we send market context, not technical indicators
            market_data = {
                "market_type": "prediction_market",
                "question": question,
                "current_yes_probability": current_yes_price,
                "current_no_probability": market_context.get("current_no_price", 1.0 - current_yes_price),
                "volume_24h": market_context.get("volume_24h", 0),
                "expiration_date": market_context.get("expiration_date"),
                "days_to_expiration": market_context.get("days_to_expiration"),
                "current_date": market_context.get("current_date", datetime.now().strftime("%Y-%m-%d")),
            }

            # Add optional momentum/volatility data if available
            if "momentum_6h" in market_context:
                market_data["probability_momentum_6h"] = market_context["momentum_6h"]
            if "momentum_24h" in market_context:
                market_data["probability_momentum_24h"] = market_context["momentum_24h"]
            if "volatility" in market_context:
                market_data["probability_volatility"] = market_context["volatility"]

            # Prepare request payload
            payload = {
                "market_data": market_data,
                "pair": question,  # Market question as "pair"
                "timeframe": "1h",  # Prediction markets checked hourly
                "current_price": current_yes_price,  # YES probability as "price"
                "provider_weights": self.provider_weights,
            }

            # Make API request to consensus endpoint
            logger.info(f"Requesting LLM consensus for: {question[:60]}...")
            logger.debug(f"Market data: {market_data}")

            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            consensus = response.json()

            # Log consensus result
            decision = consensus.get("decision", "UNKNOWN")
            confidence = consensus.get("confidence", 0.0)
            metadata = consensus.get("consensus_metadata", {})
            agreement = metadata.get("agreement_score", 0.0)
            participating = metadata.get("participating_providers", 0)
            total = metadata.get("total_providers", 0)

            logger.info(
                f"✓ Consensus received for '{question[:40]}...'\n"
                f"  Decision: {decision} (confidence: {confidence:.2%})\n"
                f"  Agreement: {agreement:.2%} ({participating}/{total} providers)\n"
                f"  Latency: {metadata.get('total_latency_ms', 0):.0f}ms\n"
                f"  Cost: ${metadata.get('total_cost_usd', 0):.6f}"
            )

            # Remove provider responses if not requested (reduce data size)
            if not include_provider_breakdown and "provider_responses" in consensus:
                consensus["provider_responses"] = []

            return consensus

        except requests.exceptions.Timeout:
            logger.error(f"Consensus request timed out after {self.timeout}s")
            return self._get_neutral_prediction(question, "Request timeout")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get LLM consensus: {e}")
            return self._get_neutral_prediction(question, str(e))

        except Exception as e:
            logger.error(f"Unexpected error in get_market_prediction: {e}", exc_info=True)
            return self._get_neutral_prediction(question, str(e))

    def get_batch_predictions(
        self,
        markets: list[Dict[str, Any]],
        max_concurrent: int = 3,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get predictions for multiple markets (batch processing)

        Args:
            markets: List of market context dictionaries
            max_concurrent: Maximum concurrent API requests (rate limiting)

        Returns:
            Dictionary mapping market questions to consensus predictions
            {
                "Will Bitcoin reach $100k?": {...consensus...},
                "Will ETH reach $5k?": {...consensus...},
            }
        """
        import concurrent.futures
        import time

        results = {}

        # Process markets in batches to respect rate limits
        for i in range(0, len(markets), max_concurrent):
            batch = markets[i:i + max_concurrent]

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                future_to_market = {
                    executor.submit(self.get_market_prediction, market): market
                    for market in batch
                }

                for future in concurrent.futures.as_completed(future_to_market):
                    market = future_to_market[future]
                    question = market.get("question", "Unknown")

                    try:
                        prediction = future.result()
                        results[question] = prediction
                    except Exception as e:
                        logger.error(f"Batch prediction failed for '{question}': {e}")
                        results[question] = self._get_neutral_prediction(question, str(e))

            # Rate limiting between batches
            if i + max_concurrent < len(markets):
                time.sleep(1)  # 1 second between batches

        logger.info(f"Batch predictions completed: {len(results)}/{len(markets)} markets")
        return results

    def _get_neutral_prediction(
        self,
        question: str,
        error: str = "",
    ) -> Dict[str, Any]:
        """
        Return a neutral (HOLD) prediction when consensus is unavailable

        Args:
            question: Market question
            error: Error message

        Returns:
            Neutral prediction dictionary
        """
        return {
            "decision": "HOLD",
            "confidence": 0.0,
            "reasoning": f"Consensus unavailable: {error}",
            "risk_level": "high",
            "consensus_metadata": {
                "total_providers": 0,
                "participating_providers": 0,
                "agreement_score": 0.0,
                "weighted_confidence": 0.0,
                "vote_breakdown": {},
                "weighted_votes": {},
                "total_latency_ms": 0.0,
                "total_cost_usd": 0.0,
                "total_tokens": 0,
            },
            "provider_responses": [],
            "error": error,
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Check if LLM consensus service is available

        Returns:
            Health status dictionary:
            {
                "status": "healthy" | "degraded" | "unavailable",
                "available_providers": 3,
                "required_providers": 1,
                "provider_health": {...}
            }
        """
        try:
            response = requests.get(
                self.endpoint,
                timeout=10,
            )
            response.raise_for_status()
            health = response.json()

            # Add configured status
            health["configured"] = health.get("available_providers", 0) > 0

            return health

        except requests.exceptions.RequestException as e:
            logger.warning(f"Health check failed: {e}")
            return {
                "configured": False,
                "status": "unavailable",
                "error": str(e),
                "available_providers": 0,
                "required_providers": 1,
            }

    def get_provider_metrics(self) -> Dict[str, Any]:
        """
        Get metrics from the consensus service

        Returns:
            Metrics dictionary with request counts, latencies, costs
        """
        try:
            health = self.health_check()
            return health.get("metrics", {})
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {}

    def estimate_cost(
        self,
        num_markets: int = 1,
        avg_providers: int = 3,
    ) -> float:
        """
        Estimate cost for prediction requests

        Args:
            num_markets: Number of markets to predict
            avg_providers: Average number of providers participating

        Returns:
            Estimated cost in USD
        """
        # Rough estimate: ~$0.02 per consensus (3-4 providers)
        # This will vary based on actual provider participation and token usage
        cost_per_consensus = 0.02
        return num_markets * cost_per_consensus


# Backward compatibility: Allow import as LLMSignalProvider for drop-in replacement
class LLMSignalProvider(PolymarketLLMProvider):
    """
    Backward-compatible alias for PolymarketLLMProvider

    This allows the Polymarket strategy to use the same import pattern
    as the crypto strategy while using the specialized Polymarket provider.
    """

    def get_signal(
        self,
        dataframe: pd.DataFrame,
        pair: str,
        timeframe: str = "1h",
        indicators: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Backward-compatible get_signal method

        Extracts market context from dataframe and calls get_market_prediction.
        This allows drop-in replacement of the standard LLMSignalProvider.

        Args:
            dataframe: DataFrame with market data (probability, volume)
            pair: Market question
            timeframe: Timeframe (usually "1h" for prediction markets)
            indicators: Not used for prediction markets

        Returns:
            Consensus prediction dictionary
        """

        # Extract market context from dataframe
        current_idx = len(dataframe) - 1

        market_context = {
            "question": pair,
            "current_yes_price": float(dataframe["close"].iloc[current_idx]),
            "volume_24h": float(dataframe["volume"].iloc[max(0, current_idx-23):current_idx+1].sum()),
        }

        # Add optional fields if available in dataframe
        if "prob_momentum_6h" in dataframe:
            market_context["momentum_6h"] = float(dataframe["prob_momentum_6h"].iloc[current_idx])
        if "prob_momentum_24h" in dataframe:
            market_context["momentum_24h"] = float(dataframe["prob_momentum_24h"].iloc[current_idx])
        if "prob_volatility" in dataframe:
            market_context["volatility"] = float(dataframe["prob_volatility"].iloc[current_idx])

        # Call consensus prediction
        return self.get_market_prediction(market_context)
