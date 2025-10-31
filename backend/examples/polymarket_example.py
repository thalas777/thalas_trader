#!/usr/bin/env python3
"""
Polymarket Client Usage Examples

This script demonstrates how to use the Polymarket client for:
- Fetching markets
- Placing orders
- Tracking positions
- Integrating with LLM signals
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polymarket_client import (
    PolymarketClient,
    MockPolymarketClient,
    OrderSide,
    OrderType,
    MarketStatus,
)


async def example_basic_usage():
    """Example 1: Basic client usage."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Client Usage")
    print("=" * 60)

    # Use mock client for demo (replace with PolymarketClient for production)
    async with MockPolymarketClient(initial_balance=10000.0) as client:
        # Check health
        print("\n1. Health Check...")
        healthy = await client.health_check()
        print(f"   ✓ API is {'healthy' if healthy else 'unhealthy'}")

        # Fetch markets
        print("\n2. Fetching active markets...")
        markets = await client.get_markets(status=MarketStatus.ACTIVE, limit=3)
        print(f"   ✓ Found {len(markets)} markets")

        for i, market in enumerate(markets, 1):
            print(f"\n   Market {i}:")
            print(f"   - ID: {market.id}")
            print(f"   - Question: {market.question}")
            print(f"   - YES price: ${market.yes_price:.2f}")
            print(f"   - NO price: ${market.no_price:.2f}")
            print(f"   - Volume: ${market.volume:,.0f}")

        # Get market prices
        if markets:
            market = markets[0]
            print(f"\n3. Fetching prices for: {market.question}")
            prices = await client.get_market_prices(market.id)
            for outcome, price in prices.items():
                print(f"   - {outcome}: ${price:.2f}")

        # Check balance
        print("\n4. Checking account balance...")
        balance = await client.get_balance()
        print(f"   - Total: ${balance['total']:,.2f}")
        print(f"   - Available: ${balance['available']:,.2f}")
        print(f"   - Reserved: ${balance['reserved']:,.2f}")


async def example_place_orders():
    """Example 2: Placing and managing orders."""
    print("\n" + "=" * 60)
    print("Example 2: Placing and Managing Orders")
    print("=" * 60)

    async with MockPolymarketClient(initial_balance=10000.0) as client:
        markets = await client.get_markets(limit=1)
        market = markets[0]

        print(f"\nMarket: {market.question}")

        # Place a limit order
        print("\n1. Placing limit order...")
        limit_order = await client.place_order(
            market_id=market.id,
            side=OrderSide.BUY,
            outcome="YES",
            price=0.65,
            size=100.0,
            order_type=OrderType.LIMIT,
        )
        print(f"   ✓ Order placed: {limit_order.id}")
        print(f"   - Status: {limit_order.status.value}")
        print(f"   - Price: ${limit_order.price:.2f}")
        print(f"   - Size: {limit_order.size}")

        # Place a market order
        print("\n2. Placing market order...")
        market_order = await client.place_order(
            market_id=market.id,
            side=OrderSide.BUY,
            outcome="YES",
            price=0.70,  # Market orders use current price
            size=50.0,
            order_type=OrderType.MARKET,
        )
        print(f"   ✓ Order placed: {market_order.id}")
        print(f"   - Status: {market_order.status.value}")
        print(f"   - Filled: {market_order.filled_size}/{market_order.size}")
        print(f"   - Fill %: {market_order.fill_percentage * 100:.1f}%")

        # Fetch all orders
        print("\n3. Fetching all orders...")
        orders = await client.get_orders(market_id=market.id)
        print(f"   ✓ Found {len(orders)} orders")
        for order in orders:
            print(f"   - {order.id}: {order.status.value} "
                  f"({order.filled_size}/{order.size} filled)")

        # Cancel an open order
        if limit_order.status.value in ["OPEN", "PARTIALLY_FILLED"]:
            print(f"\n4. Cancelling order {limit_order.id}...")
            cancelled = await client.cancel_order(limit_order.id)
            if cancelled:
                print("   ✓ Order cancelled successfully")


async def example_position_tracking():
    """Example 3: Position tracking and PnL."""
    print("\n" + "=" * 60)
    print("Example 3: Position Tracking and PnL")
    print("=" * 60)

    async with MockPolymarketClient(initial_balance=10000.0) as client:
        markets = await client.get_markets(limit=1)
        market = markets[0]

        # Place and fill an order to create position
        print("\n1. Creating position...")
        order = await client.place_order(
            market_id=market.id,
            side=OrderSide.BUY,
            outcome="YES",
            price=0.65,
            size=100.0,
            order_type=OrderType.MARKET,
        )
        print(f"   ✓ Bought {order.filled_size} shares @ ${order.price:.2f}")

        # Fetch positions
        print("\n2. Fetching positions...")
        positions = await client.get_positions(market_id=market.id)

        if positions:
            for position in positions:
                print(f"\n   Position: {position.outcome}")
                print(f"   - Size: {position.size} shares")
                print(f"   - Entry Price: ${position.average_entry_price:.2f}")
                print(f"   - Current Price: ${position.current_price:.2f}")
                print(f"   - Cost Basis: ${position.cost_basis:.2f}")
                print(f"   - Market Value: ${position.market_value:.2f}")
                print(f"   - Unrealized PnL: ${position.unrealized_pnl:+.2f}")
                print(f"   - PnL %: {position.pnl_percentage:+.1f}%")
                print(f"   - Profitable: {'✓' if position.is_profitable else '✗'}")

        # Get specific position
        print("\n3. Fetching specific position...")
        position = await client.get_position(market.id, "YES")
        if position:
            print(f"   ✓ Found position in {position.outcome}")
        else:
            print("   No position found")


async def example_llm_signal_integration():
    """Example 4: Integrating with LLM consensus signals."""
    print("\n" + "=" * 60)
    print("Example 4: LLM Signal Integration")
    print("=" * 60)

    # Simulated LLM consensus signal
    llm_signal = {
        "decision": "BUY",  # Maps to YES outcome
        "confidence": 0.75,
        "reasoning": "Multiple LLM consensus indicates positive outcome",
        "risk_level": "medium",
        "suggested_stop_loss": 0.55,
        "suggested_take_profit": 0.85,
    }

    print("\n1. LLM Consensus Signal:")
    print(f"   - Decision: {llm_signal['decision']}")
    print(f"   - Confidence: {llm_signal['confidence']:.0%}")
    print(f"   - Risk Level: {llm_signal['risk_level']}")

    async with MockPolymarketClient(initial_balance=10000.0) as client:
        markets = await client.get_markets(limit=1)
        market = markets[0]

        print(f"\n2. Target Market: {market.question}")

        # Map LLM signal to Polymarket order
        outcome = "YES" if llm_signal["decision"] == "BUY" else "NO"

        # Use confidence as price target
        price = llm_signal["confidence"]

        # Calculate position size based on confidence and risk
        risk_multipliers = {"low": 0.05, "medium": 0.03, "high": 0.02}
        risk_multiplier = risk_multipliers.get(llm_signal["risk_level"], 0.03)
        balance = await client.get_balance()
        size = (balance["available"] * risk_multiplier) / price

        print(f"\n3. Order Calculation:")
        print(f"   - Outcome: {outcome}")
        print(f"   - Target Price: ${price:.2f}")
        print(f"   - Position Size: {size:.0f} shares")
        print(f"   - Risk: {risk_multiplier * 100:.1f}% of balance")

        # Place order
        print("\n4. Placing order...")
        order = await client.place_order(
            market_id=market.id,
            side=OrderSide.BUY,
            outcome=outcome,
            price=price,
            size=size,
            order_type=OrderType.LIMIT,
        )

        print(f"   ✓ Order placed: {order.id}")
        print(f"   - Status: {order.status.value}")
        print(f"   - Expected cost: ${size * price:.2f}")

        # Check positions after order
        positions = await client.get_positions(market_id=market.id)
        if positions:
            position = positions[0]
            print(f"\n5. Position Created:")
            print(f"   - Size: {position.size} shares")
            print(f"   - Entry: ${position.average_entry_price:.2f}")
            print(f"   - Stop Loss: ${llm_signal['suggested_stop_loss']:.2f}")
            print(f"   - Take Profit: ${llm_signal['suggested_take_profit']:.2f}")


async def example_error_handling():
    """Example 5: Error handling."""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)

    from polymarket_client.exceptions import (
        PolymarketMarketNotFoundError,
        PolymarketInsufficientFundsError,
        PolymarketValidationError,
    )

    async with MockPolymarketClient(initial_balance=100.0) as client:
        # Test market not found
        print("\n1. Testing market not found...")
        try:
            await client.get_market("nonexistent_market")
        except PolymarketMarketNotFoundError as e:
            print(f"   ✓ Caught expected error: {e}")

        # Test insufficient funds
        print("\n2. Testing insufficient funds...")
        try:
            markets = await client.get_markets(limit=1)
            await client.place_order(
                market_id=markets[0].id,
                side=OrderSide.BUY,
                outcome="YES",
                price=0.65,
                size=10000.0,  # Too large
            )
        except PolymarketInsufficientFundsError as e:
            print(f"   ✓ Caught expected error: {e}")

        # Test validation error
        print("\n3. Testing validation error...")
        try:
            markets = await client.get_markets(limit=1)
            await client.place_order(
                market_id=markets[0].id,
                side=OrderSide.BUY,
                outcome="YES",
                price=1.5,  # Invalid price
                size=100.0,
            )
        except PolymarketValidationError as e:
            print(f"   ✓ Caught expected error: {e}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Polymarket Client Examples")
    print("=" * 60)

    await example_basic_usage()
    await example_place_orders()
    await example_position_tracking()
    await example_llm_signal_integration()
    await example_error_handling()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nNote: These examples use MockPolymarketClient for demonstration.")
    print("For production use, replace with PolymarketClient and provide API keys:")
    print("  client = PolymarketClient(")
    print("      api_key=os.getenv('POLYMARKET_API_KEY'),")
    print("      api_secret=os.getenv('POLYMARKET_API_SECRET')")
    print("  )")
    print()


if __name__ == "__main__":
    asyncio.run(main())
