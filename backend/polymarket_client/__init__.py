"""
Polymarket API Client Module

This module provides a client for interacting with the Polymarket API,
including authentication, market data fetching, order placement, and position monitoring.
"""

from .client import PolymarketClient
from .mock_client import MockPolymarketClient
from .models import Market, Order, Position, OrderSide, OrderStatus, OrderType, MarketStatus
from .exceptions import (
    PolymarketError,
    PolymarketAuthenticationError,
    PolymarketAPIError,
    PolymarketRateLimitError,
    PolymarketTimeoutError,
    PolymarketValidationError,
    PolymarketMarketNotFoundError,
    PolymarketOrderError,
    PolymarketInsufficientFundsError,
)

__all__ = [
    "PolymarketClient",
    "MockPolymarketClient",
    "Market",
    "Order",
    "Position",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "MarketStatus",
    "PolymarketError",
    "PolymarketAuthenticationError",
    "PolymarketAPIError",
    "PolymarketRateLimitError",
    "PolymarketTimeoutError",
    "PolymarketValidationError",
    "PolymarketMarketNotFoundError",
    "PolymarketOrderError",
    "PolymarketInsufficientFundsError",
]

__version__ = "1.0.0"
