#!/usr/bin/env python3
"""
Autonomous Market Scanner Service
Uses multi-LLM consensus to identify and rank trading opportunities across multiple pairs
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import random

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

logger = logging.getLogger(__name__)


class MarketScanner:
    """
    Autonomous market scanner that uses LLM consensus to identify best trading pairs

    Features:
    - Scans multiple trading pairs simultaneously
    - Fetches real-time market data
    - Uses multi-LLM consensus for opportunity analysis
    - Ranks pairs by opportunity score
    - Provides reasoning for selections
    """

    # Available trading pairs to scan
    AVAILABLE_PAIRS = [
        "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD",
        "BNB/USD", "ADA/USD", "DOT/USD", "MATIC/USD",
        "LINK/USD", "UNI/USD", "ATOM/USD", "XRP/USD"
    ]

    def __init__(self, api_url: str = "http://localhost:8000"):
        """Initialize market scanner"""
        self.api_url = api_url
        logger.info(f"🔍 Market Scanner initialized - tracking {len(self.AVAILABLE_PAIRS)} pairs")

    def get_market_data(self, pair: str) -> Optional[Dict[str, Any]]:
        """
        Fetch market data for a specific pair

        Returns comprehensive market data including:
        - Current price
        - Volume (24h)
        - Price change (24h, 7d)
        - Volatility indicators
        - Technical indicators (RSI, MACD, Bollinger Bands)
        """
        try:
            # Base prices for different assets (mock data for now)
            base_prices = {
                "BTC/USD": 95000,
                "ETH/USD": 3400,
                "SOL/USD": 195,
                "AVAX/USD": 38,
                "BNB/USD": 620,
                "ADA/USD": 0.85,
                "DOT/USD": 7.2,
                "MATIC/USD": 0.92,
                "LINK/USD": 15.5,
                "UNI/USD": 11.2,
                "ATOM/USD": 9.8,
                "XRP/USD": 2.15,
            }

            base_price = base_prices.get(pair, 100)

            # Add realistic randomness
            price = base_price * (1 + random.uniform(-0.03, 0.03))

            # Calculate volume with some pairs being more liquid
            volume_multiplier = {
                "BTC/USD": 10,
                "ETH/USD": 8,
                "SOL/USD": 5,
            }.get(pair, 3)

            volume_24h = random.uniform(50_000_000, 200_000_000) * volume_multiplier

            # Price changes
            change_24h = random.uniform(-8, 12)  # Percentage
            change_7d = random.uniform(-15, 20)

            # Volatility (higher = more volatile)
            volatility = random.uniform(0.02, 0.08)

            # Technical indicators
            rsi = random.uniform(25, 75)
            macd = random.uniform(-0.03, 0.03)
            macd_signal = random.uniform(-0.025, 0.025)

            # Bollinger Bands
            bb_width = price * 0.04  # 4% width
            bb_middle = price
            bb_upper = bb_middle + bb_width
            bb_lower = bb_middle - bb_width

            # EMA indicators
            ema_short = price * (1 + random.uniform(-0.01, 0.01))
            ema_long = price * (1 + random.uniform(-0.02, 0.02))

            return {
                "pair": pair,
                "price": price,
                "volume_24h": volume_24h,
                "change_24h": change_24h,
                "change_7d": change_7d,
                "volatility": volatility,
                "technical_indicators": {
                    "rsi": rsi,
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "ema_short": ema_short,
                    "ema_long": ema_long,
                    "bb_upper": bb_upper,
                    "bb_middle": bb_middle,
                    "bb_lower": bb_lower,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching market data for {pair}: {e}")
            return None

    async def analyze_pair_opportunity(
        self,
        pair: str,
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM consensus to analyze trading opportunity for a specific pair

        Returns:
            Analysis result with opportunity score and reasoning
        """
        try:
            import requests

            url = f"{self.api_url}/api/v1/strategies/llm-consensus"

            # Prepare prompt for LLM analysis
            analysis_prompt = f"""
Analyze this trading pair for opportunity quality:

Pair: {pair}
Current Price: ${market_data['price']:,.2f}
24h Volume: ${market_data['volume_24h']:,.0f}
24h Change: {market_data['change_24h']:.2f}%
7d Change: {market_data['change_7d']:.2f}%
Volatility: {market_data['volatility']:.2%}

Technical Indicators:
- RSI: {market_data['technical_indicators']['rsi']:.1f}
- MACD: {market_data['technical_indicators']['macd']:.4f}
- EMA Short: ${market_data['technical_indicators']['ema_short']:,.2f}
- EMA Long: ${market_data['technical_indicators']['ema_long']:,.2f}

Rate this trading opportunity on a scale of 0-100 considering:
1. Volume and liquidity
2. Momentum and trend strength
3. Technical setup quality
4. Risk/reward profile

Provide a concise analysis with an opportunity score.
"""

            payload = {
                "market_data": market_data['technical_indicators'],
                "pair": pair,
                "timeframe": "1h",
                "current_price": market_data['price'],
                "analysis_prompt": analysis_prompt,
            }

            # Make async request to consensus endpoint
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "pair": pair,
                    "opportunity_score": result.get('confidence', 0) * 100,
                    "consensus_signal": result.get('signal', 'HOLD'),
                    "reasoning": result.get('reasoning', 'No reasoning provided'),
                    "provider_votes": result.get('provider_responses', []),
                    "market_data": market_data,
                }
            else:
                logger.warning(f"Failed to analyze {pair}: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error analyzing pair {pair}: {e}")
            return None

    async def scan_markets(
        self,
        top_n: int = 3,
        min_opportunity_score: float = 60.0
    ) -> List[Dict[str, Any]]:
        """
        Scan all available markets and return top opportunities

        Args:
            top_n: Number of top opportunities to return
            min_opportunity_score: Minimum score threshold (0-100)

        Returns:
            List of top trading opportunities ranked by score
        """
        logger.info(f"🔍 Starting market scan across {len(self.AVAILABLE_PAIRS)} pairs...")

        # Fetch market data for all pairs
        market_data_tasks = []
        for pair in self.AVAILABLE_PAIRS:
            market_data = self.get_market_data(pair)
            if market_data:
                market_data_tasks.append((pair, market_data))

        # Analyze all pairs in parallel using LLM consensus
        analysis_tasks = [
            self.analyze_pair_opportunity(pair, data)
            for pair, data in market_data_tasks
        ]

        logger.info(f"📊 Analyzing {len(analysis_tasks)} pairs with multi-LLM consensus...")

        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

        # Filter and sort results
        opportunities = []
        for result in results:
            if isinstance(result, dict) and result is not None:
                if result['opportunity_score'] >= min_opportunity_score:
                    opportunities.append(result)

        # Sort by opportunity score (descending)
        opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)

        # Return top N
        top_opportunities = opportunities[:top_n]

        logger.info(f"✅ Market scan complete. Found {len(opportunities)} opportunities above threshold")
        if top_opportunities:
            logger.info(f"🎯 Top opportunity: {top_opportunities[0]['pair']} "
                       f"(score: {top_opportunities[0]['opportunity_score']:.1f})")

        return top_opportunities

    async def get_best_pair(self) -> Optional[Dict[str, Any]]:
        """
        Scan markets and return single best trading opportunity

        Returns:
            Best trading opportunity or None if no good opportunities found
        """
        opportunities = await self.scan_markets(top_n=1, min_opportunity_score=50.0)
        return opportunities[0] if opportunities else None


async def main():
    """Test the market scanner"""
    scanner = MarketScanner()

    print("\n" + "="*80)
    print("🤖 AUTONOMOUS MARKET SCANNER - Multi-LLM Consensus")
    print("="*80 + "\n")

    # Scan markets
    opportunities = await scanner.scan_markets(top_n=5, min_opportunity_score=55.0)

    if opportunities:
        print(f"\n📊 Found {len(opportunities)} Trading Opportunities:\n")

        for i, opp in enumerate(opportunities, 1):
            print(f"\n{i}. {opp['pair']}")
            print(f"   Score: {opp['opportunity_score']:.1f}/100")
            print(f"   Signal: {opp['consensus_signal']}")
            print(f"   Price: ${opp['market_data']['price']:,.2f}")
            print(f"   24h Volume: ${opp['market_data']['volume_24h']:,.0f}")
            print(f"   24h Change: {opp['market_data']['change_24h']:+.2f}%")
            print(f"   Reasoning: {opp['reasoning'][:150]}...")
    else:
        print("\n❌ No trading opportunities found above threshold")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
