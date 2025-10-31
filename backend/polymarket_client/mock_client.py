"""
Mock Polymarket API Client for Testing

This module provides a mock implementation of the Polymarket client
that simulates API responses without making actual HTTP requests.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random
import uuid

from .models import (
    Market,
    Order,
    Position,
    OrderSide,
    OrderStatus,
    OrderType,
    MarketStatus,
)
from .exceptions import (
    PolymarketError,
    PolymarketAuthenticationError,
    PolymarketAPIError,
    PolymarketMarketNotFoundError,
    PolymarketOrderError,
    PolymarketInsufficientFundsError,
    PolymarketValidationError,
)

logger = logging.getLogger(__name__)


class MockPolymarketClient:
    """
    Mock Polymarket client for testing.

    This client simulates Polymarket API behavior without making real API calls.
    It maintains in-memory state for markets, orders, and positions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        initial_balance: float = 10000.0,
        simulate_errors: bool = False,
        error_probability: float = 0.0,
    ):
        """
        Initialize mock Polymarket client.

        Args:
            api_key: API key (optional for mock)
            api_secret: API secret (optional for mock)
            initial_balance: Initial account balance
            simulate_errors: Whether to randomly simulate errors
            error_probability: Probability of simulating an error (0.0-1.0)
        """
        self.api_key = api_key or "mock_api_key"
        self.api_secret = api_secret or "mock_api_secret"
        self.simulate_errors = simulate_errors
        self.error_probability = error_probability

        # In-memory state
        self._markets: Dict[str, Market] = {}
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
        self._balance = {
            "total": initial_balance,
            "available": initial_balance,
            "reserved": 0.0,
        }

        # Generate some sample markets
        self._generate_sample_markets()

        logger.info(f"Initialized MockPolymarketClient (balance=${initial_balance})")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close client (no-op for mock)."""
        pass

    def _maybe_simulate_error(self):
        """Randomly simulate an error based on error_probability."""
        if self.simulate_errors and random.random() < self.error_probability:
            error_types = [
                PolymarketAPIError("Simulated API error"),
                PolymarketError("Simulated generic error"),
            ]
            raise random.choice(error_types)

    def _generate_sample_markets(self):
        """Generate sample markets for testing."""
        sample_markets = [
            {
                "id": "market_btc_50k",
                "question": "Will Bitcoin reach $50,000 by end of 2025?",
                "description": "Resolves YES if BTC/USD reaches $50,000 or higher.",
                "yes_price": 0.65,
                "no_price": 0.35,
                "volume": 150000.0,
                "liquidity": 50000.0,
                "status": MarketStatus.ACTIVE,
            },
            {
                "id": "market_eth_3k",
                "question": "Will Ethereum reach $3,000 by end of Q1 2025?",
                "description": "Resolves YES if ETH/USD reaches $3,000 or higher.",
                "yes_price": 0.52,
                "no_price": 0.48,
                "volume": 200000.0,
                "liquidity": 75000.0,
                "status": MarketStatus.ACTIVE,
            },
            {
                "id": "market_ai_regulation",
                "question": "Will the US pass major AI regulation in 2025?",
                "description": "Resolves YES if significant federal AI legislation is enacted.",
                "yes_price": 0.38,
                "no_price": 0.62,
                "volume": 80000.0,
                "liquidity": 25000.0,
                "status": MarketStatus.ACTIVE,
            },
        ]

        for market_data in sample_markets:
            market = Market(
                id=market_data["id"],
                question=market_data["question"],
                description=market_data["description"],
                end_date=datetime.now() + timedelta(days=365),
                status=market_data["status"],
                yes_price=market_data["yes_price"],
                no_price=market_data["no_price"],
                volume=market_data["volume"],
                liquidity=market_data["liquidity"],
                created_at=datetime.now() - timedelta(days=30),
            )
            self._markets[market.id] = market

    # ============================================================================
    # Authentication & Health Check
    # ============================================================================

    async def health_check(self) -> bool:
        """Check API health (always returns True for mock)."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.01)  # Simulate network delay
        return True

    # ============================================================================
    # Market Data Methods
    # ============================================================================

    async def get_markets(
        self,
        status: Optional[MarketStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Market]:
        """Fetch available markets."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.01)  # Simulate network delay

        markets = list(self._markets.values())

        # Filter by status if provided
        if status:
            markets = [m for m in markets if m.status == status]

        # Apply pagination
        markets = markets[offset : offset + limit]

        # Simulate price changes
        for market in markets:
            if random.random() < 0.3:  # 30% chance of price change
                delta = random.uniform(-0.05, 0.05)
                market.yes_price = max(0.01, min(0.99, market.yes_price + delta))
                market.no_price = 1.0 - market.yes_price

        return markets

    async def get_market(self, market_id: str) -> Market:
        """Fetch specific market."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.01)

        if market_id not in self._markets:
            raise PolymarketMarketNotFoundError(f"Market not found: {market_id}")

        return self._markets[market_id]

    async def get_market_prices(self, market_id: str) -> Dict[str, float]:
        """Fetch market prices."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.01)

        if market_id not in self._markets:
            raise PolymarketMarketNotFoundError(f"Market not found: {market_id}")

        market = self._markets[market_id]
        return {
            "YES": market.yes_price,
            "NO": market.no_price,
        }

    # ============================================================================
    # Order Management Methods
    # ============================================================================

    async def place_order(
        self,
        market_id: str,
        side: OrderSide,
        outcome: str,
        price: float,
        size: float,
        order_type: OrderType = OrderType.LIMIT,
    ) -> Order:
        """Place an order."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.02)

        # Validate market exists
        if market_id not in self._markets:
            raise PolymarketMarketNotFoundError(f"Market not found: {market_id}")

        # Validate parameters
        if not (0.0 <= price <= 1.0):
            raise PolymarketValidationError(f"Price must be between 0.0 and 1.0, got {price}")
        if size <= 0:
            raise PolymarketValidationError(f"Size must be positive, got {size}")

        # Calculate required funds
        required_funds = size * price if side == OrderSide.BUY else 0
        if required_funds > self._balance["available"]:
            raise PolymarketInsufficientFundsError(
                f"Insufficient funds: need ${required_funds:.2f}, "
                f"available ${self._balance['available']:.2f}"
            )

        # Create order
        order_id = f"order_{uuid.uuid4().hex[:8]}"
        order = Order(
            id=order_id,
            market_id=market_id,
            side=side,
            outcome=outcome,
            order_type=order_type,
            status=OrderStatus.OPEN,
            price=price,
            size=size,
            filled_size=0.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Update balance
        if required_funds > 0:
            self._balance["available"] -= required_funds
            self._balance["reserved"] += required_funds

        # Store order
        self._orders[order_id] = order

        # Simulate partial or full fill for market orders
        if order_type == OrderType.MARKET:
            fill_percentage = random.uniform(0.8, 1.0)
            filled_size = size * fill_percentage
            order.filled_size = filled_size
            order.remaining_size = size - filled_size
            order.status = OrderStatus.FILLED if filled_size >= size else OrderStatus.PARTIALLY_FILLED
            order.updated_at = datetime.now()

            # Update position
            await self._update_position(market_id, outcome, side, filled_size, price)

        logger.info(f"Placed {order.status.value} order: {order_id}")
        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.01)

        if order_id not in self._orders:
            raise PolymarketOrderError(f"Order not found: {order_id}")

        order = self._orders[order_id]

        if order.status not in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]:
            raise PolymarketOrderError(f"Cannot cancel order with status: {order.status.value}")

        # Update order status
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()

        # Release reserved funds
        if order.side == OrderSide.BUY:
            reserved = order.remaining_size * order.price
            self._balance["reserved"] -= reserved
            self._balance["available"] += reserved

        logger.info(f"Cancelled order: {order_id}")
        return True

    async def get_order(self, order_id: str) -> Order:
        """Fetch specific order."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.01)

        if order_id not in self._orders:
            raise PolymarketOrderError(f"Order not found: {order_id}")

        return self._orders[order_id]

    async def get_orders(
        self,
        market_id: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> List[Order]:
        """Fetch orders."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.01)

        orders = list(self._orders.values())

        # Filter by market_id
        if market_id:
            orders = [o for o in orders if o.market_id == market_id]

        # Filter by status
        if status:
            orders = [o for o in orders if o.status == status]

        # Apply limit
        orders = orders[:limit]

        return orders

    # ============================================================================
    # Position Monitoring Methods
    # ============================================================================

    async def _update_position(
        self,
        market_id: str,
        outcome: str,
        side: OrderSide,
        size: float,
        price: float,
    ):
        """Update position after trade execution."""
        position_key = f"{market_id}_{outcome}"

        if position_key not in self._positions:
            # Create new position
            self._positions[position_key] = Position(
                market_id=market_id,
                outcome=outcome,
                size=0.0,
                average_entry_price=0.0,
                current_price=price,
            )

        position = self._positions[position_key]

        if side == OrderSide.BUY:
            # Add to position
            total_cost = (position.size * position.average_entry_price) + (size * price)
            position.size += size
            position.average_entry_price = total_cost / position.size if position.size > 0 else price
        else:
            # Reduce position
            position.size = max(0, position.size - size)
            if position.size == 0:
                position.average_entry_price = 0.0

        # Update current price
        market = self._markets.get(market_id)
        if market:
            position.current_price = market.yes_price if outcome == "YES" else market.no_price

        # Recalculate PnL
        position.cost_basis = position.size * position.average_entry_price
        position.market_value = position.size * position.current_price
        position.unrealized_pnl = position.market_value - position.cost_basis

    async def get_positions(self, market_id: Optional[str] = None) -> List[Position]:
        """Fetch positions."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.01)

        positions = list(self._positions.values())

        # Filter by market_id
        if market_id:
            positions = [p for p in positions if p.market_id == market_id]

        # Update current prices
        for position in positions:
            market = self._markets.get(position.market_id)
            if market:
                position.current_price = (
                    market.yes_price if position.outcome == "YES" else market.no_price
                )
                position.market_value = position.size * position.current_price
                position.unrealized_pnl = position.market_value - position.cost_basis

        # Filter out zero positions
        positions = [p for p in positions if p.size > 0]

        return positions

    async def get_position(self, market_id: str, outcome: str) -> Optional[Position]:
        """Fetch specific position."""
        positions = await self.get_positions(market_id=market_id)
        for position in positions:
            if position.market_id == market_id and position.outcome == outcome:
                return position
        return None

    async def get_balance(self) -> Dict[str, float]:
        """Fetch account balance."""
        self._maybe_simulate_error()
        await asyncio.sleep(0.01)
        return self._balance.copy()

    # ============================================================================
    # Test Utilities
    # ============================================================================

    def reset(self):
        """Reset mock client state (for testing)."""
        self._orders.clear()
        self._positions.clear()
        self._balance = {
            "total": 10000.0,
            "available": 10000.0,
            "reserved": 0.0,
        }
        self._generate_sample_markets()
        logger.info("Reset MockPolymarketClient state")

    def set_market_price(self, market_id: str, yes_price: float):
        """Set market price (for testing)."""
        if market_id in self._markets:
            self._markets[market_id].yes_price = yes_price
            self._markets[market_id].no_price = 1.0 - yes_price

    def add_market(self, market: Market):
        """Add a custom market (for testing)."""
        self._markets[market.id] = market
