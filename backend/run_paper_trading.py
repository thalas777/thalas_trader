#!/usr/bin/env python3
"""Run extended paper trading session"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from paper_trader import PaperTrader

if __name__ == "__main__":
    print("\n🎯 Multi-LLM Consensus Paper Trading Session")
    print("=" * 80)

    trader = PaperTrader(
        initial_balance=10000.0,
        api_url="http://localhost:8000",
        trading_pairs=["BTC/USD", "ETH/USD"],
        position_size=0.15,  # 15% per trade
    )

    # Run 6 iterations with 8 second delay = ~48 seconds total
    trader.run(iterations=6, delay=8)
