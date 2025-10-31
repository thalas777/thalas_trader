#!/usr/bin/env python3
"""Quick test of paper trading system"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from paper_trader import PaperTrader

if __name__ == "__main__":
    print("🧪 Running quick paper trading test...")

    trader = PaperTrader(
        initial_balance=10000.0,
        api_url="http://localhost:8000",
        trading_pairs=["BTC/USD"],
        position_size=0.2,
    )

    # Run just 2 iterations with 5 second delay
    trader.run(iterations=2, delay=5)
