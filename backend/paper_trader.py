#!/usr/bin/env python3
"""
Simple Paper Trading System for Multi-LLM Consensus Testing
Fetches live market data and executes paper trades based on consensus signals
"""
import os
import sys
import time
import json
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))


class PaperTrader:
    """Paper trading system using LLM consensus signals"""

    def __init__(
        self,
        initial_balance: float = 10000.0,
        api_url: str = "http://localhost:8000",
        trading_pairs: List[str] = None,
        position_size: float = 0.1,  # 10% per trade
    ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.api_url = api_url
        self.trading_pairs = trading_pairs or ["BTC/USD", "ETH/USD"]
        self.position_size = position_size

        self.positions = {}  # {pair: {amount, entry_price, entry_time, signal}}
        self.trade_history = []
        self.signal_history = []

        print(f"🤖 Paper Trader Initialized")
        print(f"💰 Initial Balance: ${self.balance:,.2f}")
        print(f"📊 Trading Pairs: {', '.join(self.trading_pairs)}")
        print(f"🎯 Position Size: {self.position_size*100}%")
        print(f"=" * 80)

    def get_market_data(self, pair: str) -> Optional[Dict[str, Any]]:
        """
        Fetch live market data from CoinGecko API

        Returns mock technical indicators for now
        """
        try:
            # For demo purposes, using mock data with some randomness
            # In production, you'd fetch from a real exchange API
            import random

            base_price = {
                "BTC/USD": 50000,
                "ETH/USD": 3000,
            }.get(pair, 1000)

            # Add some randomness
            price = base_price * (1 + random.uniform(-0.02, 0.02))

            # Mock technical indicators
            market_data = {
                "rsi": random.uniform(30, 70),
                "macd": random.uniform(-0.02, 0.02),
                "macd_signal": random.uniform(-0.015, 0.015),
                "ema_short": price * 0.99,
                "ema_long": price * 0.98,
                "volume_24h": random.uniform(1000000, 2000000),
                "bb_upper": price * 1.02,
                "bb_middle": price,
                "bb_lower": price * 0.98,
            }

            return {
                "price": price,
                "market_data": market_data,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"❌ Error fetching market data for {pair}: {e}")
            return None

    def get_consensus_signal(
        self, pair: str, market_data: Dict[str, Any], current_price: float
    ) -> Optional[Dict[str, Any]]:
        """Get trading signal from LLM consensus endpoint"""
        try:
            url = f"{self.api_url}/api/v1/strategies/llm-consensus"

            payload = {
                "market_data": market_data,
                "pair": pair,
                "timeframe": "1h",
                "current_price": current_price,
            }

            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()

            signal = response.json()
            return signal

        except Exception as e:
            print(f"❌ Error getting consensus signal for {pair}: {e}")
            return None

    def execute_trade(self, pair: str, signal: Dict[str, Any], price: float):
        """Execute paper trade based on signal"""
        decision = signal["decision"]
        confidence = signal["confidence"]

        # Only trade on high confidence signals
        if confidence < 0.6:
            print(f"⚠️  {pair}: Low confidence ({confidence:.2f}), skipping trade")
            return

        if decision == "BUY" and pair not in self.positions:
            # Open BUY position
            trade_amount = self.balance * self.position_size
            amount = trade_amount / price

            self.positions[pair] = {
                "amount": amount,
                "entry_price": price,
                "entry_time": datetime.now(),
                "signal": signal,
                "type": "LONG",
            }

            self.balance -= trade_amount

            print(f"🟢 BUY  {pair} @ ${price:,.2f}")
            print(f"   Amount: {amount:.6f} | Value: ${trade_amount:,.2f}")
            print(f"   Confidence: {confidence:.2f} | Providers: {signal['consensus_metadata']['participating_providers']}")
            print(f"   Reasoning: {signal['reasoning'][:100]}...")

            self.trade_history.append({
                "timestamp": datetime.now().isoformat(),
                "pair": pair,
                "action": "BUY",
                "price": price,
                "amount": amount,
                "value": trade_amount,
                "signal": signal,
            })

        elif decision == "SELL" and pair in self.positions:
            # Close position
            position = self.positions[pair]
            trade_value = position["amount"] * price
            pnl = trade_value - (position["amount"] * position["entry_price"])
            pnl_pct = (pnl / (position["amount"] * position["entry_price"])) * 100

            self.balance += trade_value

            print(f"🔴 SELL {pair} @ ${price:,.2f}")
            print(f"   Entry: ${position['entry_price']:,.2f} | Exit: ${price:,.2f}")
            print(f"   P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
            print(f"   Confidence: {confidence:.2f}")

            self.trade_history.append({
                "timestamp": datetime.now().isoformat(),
                "pair": pair,
                "action": "SELL",
                "price": price,
                "amount": position["amount"],
                "value": trade_value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "signal": signal,
            })

            del self.positions[pair]

        elif decision == "HOLD":
            status = "in position" if pair in self.positions else "no position"
            print(f"⚪ HOLD {pair} @ ${price:,.2f} ({status}, confidence: {confidence:.2f})")

    def print_status(self):
        """Print current portfolio status"""
        print(f"\n{'=' * 80}")
        print(f"💼 Portfolio Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 80}")

        # Calculate total value
        total_value = self.balance
        for pair, pos in self.positions.items():
            market_info = self.get_market_data(pair)
            if market_info:
                position_value = pos["amount"] * market_info["price"]
                total_value += position_value

        # Print summary
        print(f"💰 Cash Balance: ${self.balance:,.2f}")
        print(f"📈 Total Value: ${total_value:,.2f}")
        print(f"📊 P&L: ${total_value - self.initial_balance:,.2f} ({((total_value/self.initial_balance - 1) * 100):+.2f}%)")
        print(f"📋 Open Positions: {len(self.positions)}")
        print(f"📝 Total Trades: {len(self.trade_history)}")

        # Print open positions
        if self.positions:
            print(f"\n🎯 Open Positions:")
            for pair, pos in self.positions.items():
                market_info = self.get_market_data(pair)
                if market_info:
                    current_price = market_info["price"]
                    position_value = pos["amount"] * current_price
                    unrealized_pnl = position_value - (pos["amount"] * pos["entry_price"])
                    unrealized_pnl_pct = (unrealized_pnl / (pos["amount"] * pos["entry_price"])) * 100

                    print(f"   {pair}: {pos['amount']:.6f} @ ${pos['entry_price']:,.2f}")
                    print(f"      Current: ${current_price:,.2f} | Value: ${position_value:,.2f}")
                    print(f"      Unrealized P&L: ${unrealized_pnl:,.2f} ({unrealized_pnl_pct:+.2f}%)")

        print(f"{'=' * 80}\n")

    def run(self, iterations: int = 10, delay: int = 10):
        """Run paper trading loop"""
        print(f"\n🚀 Starting Paper Trading...")
        print(f"⏱️  Running {iterations} iterations with {delay}s delay\n")

        try:
            for i in range(iterations):
                print(f"\n📍 Iteration {i+1}/{iterations} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'-' * 80}")

                for pair in self.trading_pairs:
                    # Get market data
                    market_info = self.get_market_data(pair)
                    if not market_info:
                        continue

                    # Get consensus signal
                    signal = self.get_consensus_signal(
                        pair,
                        market_info["market_data"],
                        market_info["price"]
                    )

                    if signal:
                        self.signal_history.append({
                            "timestamp": datetime.now().isoformat(),
                            "pair": pair,
                            "signal": signal,
                        })

                        # Execute trade
                        self.execute_trade(pair, signal, market_info["price"])

                    print()

                # Print status every iteration
                if (i + 1) % 3 == 0 or i == iterations - 1:
                    self.print_status()

                # Wait before next iteration
                if i < iterations - 1:
                    print(f"⏳ Waiting {delay} seconds...")
                    time.sleep(delay)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Trading interrupted by user")

        finally:
            print(f"\n🏁 Paper Trading Completed!")
            self.print_status()
            self.save_results()

    def save_results(self):
        """Save trading results to file"""
        results = {
            "initial_balance": self.initial_balance,
            "final_balance": self.balance,
            "positions": self.positions,
            "trade_history": self.trade_history,
            "signal_history": self.signal_history,
            "timestamp": datetime.now().isoformat(),
        }

        filename = f"paper_trading_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"💾 Results saved to: {filepath}")


def main():
    """Main entry point"""
    print(f"\n{'=' * 80}")
    print(f"🤖 Thalas Trader - Multi-LLM Consensus Paper Trading System")
    print(f"{'=' * 80}\n")

    # Initialize paper trader
    trader = PaperTrader(
        initial_balance=10000.0,
        api_url="http://localhost:8000",
        trading_pairs=["BTC/USD", "ETH/USD"],
        position_size=0.2,  # 20% per trade
    )

    # Run paper trading
    trader.run(iterations=10, delay=15)


if __name__ == "__main__":
    main()
