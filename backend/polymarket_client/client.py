"""
Polymarket API Client

This module provides a client for interacting with the Polymarket CLOB (Central Limit Order Book) API.
It implements authentication, market data fetching, order placement, and position monitoring.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx

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

logger = logging.getLogger(__name__)


class PolymarketClient:
    """
    Client for interacting with Polymarket API.

    This client provides methods for:
    - Authentication with API keys
    - Fetching market data
    - Placing and managing orders
    - Monitoring positions
    - Rate limiting and error handling
    """

    # Polymarket API endpoints (based on CLOB API documentation)
    BASE_URL = "https://clob.polymarket.com"
    API_VERSION = "v1"

    # Rate limiting defaults
    DEFAULT_RATE_LIMIT = 100  # requests per minute
    DEFAULT_TIMEOUT = 30  # seconds
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limit: int = DEFAULT_RATE_LIMIT,
    ):
        """
        Initialize Polymarket client.

        Args:
            api_key: API key for authentication
            api_secret: API secret for signing requests
            base_url: Base URL for API (default: production URL)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            rate_limit: Maximum requests per minute
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit = rate_limit

        # Rate limiting state
        self._request_times: List[float] = []
        self._rate_limit_lock = asyncio.Lock()

        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            f"Initialized PolymarketClient (base_url={self.base_url}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries})"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ThalasTrader-PolymarketClient/1.0",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _rate_limit_check(self):
        """Check and enforce rate limiting."""
        async with self._rate_limit_lock:
            current_time = time.time()
            # Remove requests older than 1 minute
            self._request_times = [
                t for t in self._request_times if current_time - t < 60
            ]

            # Check if we've hit the rate limit
            if len(self._request_times) >= self.rate_limit:
                # Calculate wait time
                oldest_request = self._request_times[0]
                wait_time = 60 - (current_time - oldest_request)
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached ({self.rate_limit} req/min). "
                        f"Waiting {wait_time:.2f}s..."
                    )
                    await asyncio.sleep(wait_time)
                    # Remove old requests after waiting
                    current_time = time.time()
                    self._request_times = [
                        t for t in self._request_times if current_time - t < 60
                    ]

            # Add current request time
            self._request_times.append(current_time)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Polymarket API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON request body
            retry_count: Current retry attempt

        Returns:
            Response data as dictionary

        Raises:
            PolymarketError: Various errors based on response
        """
        await self._ensure_client()
        await self._rate_limit_check()

        url = f"/{self.API_VERSION}/{endpoint.lstrip('/')}"
        logger.debug(f"{method} {url} (attempt {retry_count + 1}/{self.max_retries + 1})")

        try:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )

            # Handle different status codes
            if response.status_code == 200:
                return response.json()

            elif response.status_code == 401:
                raise PolymarketAuthenticationError(
                    "Authentication failed. Check API key and secret.",
                    status_code=response.status_code,
                    response_data=response.json() if response.text else None,
                )

            elif response.status_code == 404:
                raise PolymarketMarketNotFoundError(
                    "Resource not found.",
                    status_code=response.status_code,
                    response_data=response.json() if response.text else None,
                )

            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise PolymarketRateLimitError(
                    "Rate limit exceeded.",
                    status_code=response.status_code,
                    response_data=response.json() if response.text else None,
                    retry_after=retry_after,
                )

            elif 400 <= response.status_code < 500:
                error_data = response.json() if response.text else {}
                raise PolymarketValidationError(
                    f"Client error: {error_data.get('message', response.text)}",
                    status_code=response.status_code,
                    response_data=error_data,
                )

            elif 500 <= response.status_code < 600:
                error_data = response.json() if response.text else {}
                raise PolymarketAPIError(
                    f"Server error: {error_data.get('message', response.text)}",
                    status_code=response.status_code,
                    response_data=error_data,
                )

            else:
                raise PolymarketAPIError(
                    f"Unexpected status code: {response.status_code}",
                    status_code=response.status_code,
                )

        except httpx.TimeoutException as e:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(f"Request timeout. Retrying in {wait_time}s... ({e})")
                await asyncio.sleep(wait_time)
                return await self._make_request(method, endpoint, params, json_data, retry_count + 1)
            raise PolymarketTimeoutError(f"Request timeout after {self.max_retries} retries: {e}")

        except PolymarketRateLimitError as e:
            if retry_count < self.max_retries and e.retry_after:
                logger.warning(f"Rate limited. Retrying in {e.retry_after}s...")
                await asyncio.sleep(e.retry_after)
                return await self._make_request(method, endpoint, params, json_data, retry_count + 1)
            raise

        except (PolymarketAuthenticationError, PolymarketValidationError):
            # Don't retry auth or validation errors
            raise

        except PolymarketAPIError as e:
            if retry_count < self.max_retries and 500 <= e.status_code < 600:
                wait_time = 2 ** retry_count
                logger.warning(f"Server error. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._make_request(method, endpoint, params, json_data, retry_count + 1)
            raise

        except Exception as e:
            raise PolymarketError(f"Unexpected error: {e}")

    # ============================================================================
    # Authentication & Health Check
    # ============================================================================

    async def health_check(self) -> bool:
        """
        Check API health and authentication.

        Returns:
            True if API is healthy and authenticated

        Raises:
            PolymarketError: If health check fails
        """
        try:
            # Try to fetch markets as a health check
            await self.get_markets(limit=1)
            logger.info("Health check passed")
            return True
        except PolymarketAuthenticationError:
            logger.error("Health check failed: Authentication error")
            raise
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise PolymarketError(f"Health check failed: {e}")

    # ============================================================================
    # Market Data Methods
    # ============================================================================

    async def get_markets(
        self,
        status: Optional[MarketStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Market]:
        """
        Fetch available prediction markets.

        Args:
            status: Filter by market status (ACTIVE, CLOSED, etc.)
            limit: Maximum number of markets to return
            offset: Pagination offset

        Returns:
            List of Market objects

        Raises:
            PolymarketError: If request fails
        """
        params = {
            "limit": limit,
            "offset": offset,
        }
        if status:
            params["status"] = status.value

        try:
            data = await self._make_request("GET", "/markets", params=params)
            markets = []

            # Handle different response formats
            market_list = data if isinstance(data, list) else data.get("markets", [])

            for market_data in market_list:
                try:
                    market = Market.from_dict(market_data)
                    markets.append(market)
                except Exception as e:
                    logger.warning(f"Failed to parse market: {e}")
                    continue

            logger.info(f"Fetched {len(markets)} markets")
            return markets

        except PolymarketError:
            raise
        except Exception as e:
            raise PolymarketAPIError(f"Failed to fetch markets: {e}")

    async def get_market(self, market_id: str) -> Market:
        """
        Fetch details for a specific market.

        Args:
            market_id: Market identifier

        Returns:
            Market object

        Raises:
            PolymarketMarketNotFoundError: If market doesn't exist
            PolymarketError: If request fails
        """
        try:
            data = await self._make_request("GET", f"/markets/{market_id}")
            return Market.from_dict(data)

        except PolymarketMarketNotFoundError:
            raise
        except PolymarketError:
            raise
        except Exception as e:
            raise PolymarketAPIError(f"Failed to fetch market {market_id}: {e}")

    async def get_market_prices(self, market_id: str) -> Dict[str, float]:
        """
        Fetch current prices for a market.

        Args:
            market_id: Market identifier

        Returns:
            Dictionary mapping outcomes to prices

        Raises:
            PolymarketError: If request fails
        """
        try:
            data = await self._make_request("GET", f"/markets/{market_id}/prices")
            return {
                outcome: float(price)
                for outcome, price in data.get("prices", {}).items()
            }

        except PolymarketError:
            raise
        except Exception as e:
            raise PolymarketAPIError(f"Failed to fetch prices for market {market_id}: {e}")

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
        """
        Place an order on Polymarket.

        Args:
            market_id: Market identifier
            side: Order side (BUY/SELL)
            outcome: Outcome to trade (e.g., "YES", "NO")
            price: Limit price (0.0-1.0)
            size: Order size
            order_type: Order type (MARKET, LIMIT, etc.)

        Returns:
            Order object

        Raises:
            PolymarketValidationError: If order parameters are invalid
            PolymarketInsufficientFundsError: If insufficient funds
            PolymarketOrderError: If order placement fails
        """
        # Validate parameters
        if not (0.0 <= price <= 1.0):
            raise PolymarketValidationError(f"Price must be between 0.0 and 1.0, got {price}")
        if size <= 0:
            raise PolymarketValidationError(f"Size must be positive, got {size}")

        order_data = {
            "market_id": market_id,
            "side": side.value,
            "outcome": outcome,
            "price": price,
            "size": size,
            "order_type": order_type.value,
        }

        try:
            data = await self._make_request("POST", "/orders", json_data=order_data)
            order = Order.from_dict(data)
            logger.info(f"Placed order: {order.id} ({side.value} {size} @ {price})")
            return order

        except PolymarketValidationError:
            raise
        except PolymarketError as e:
            if e.response_data and "insufficient" in str(e.response_data).lower():
                raise PolymarketInsufficientFundsError(
                    "Insufficient funds for order",
                    status_code=e.status_code,
                    response_data=e.response_data,
                )
            raise PolymarketOrderError(f"Failed to place order: {e}")
        except Exception as e:
            raise PolymarketOrderError(f"Failed to place order: {e}")

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Order identifier

        Returns:
            True if order was cancelled successfully

        Raises:
            PolymarketOrderError: If cancellation fails
        """
        try:
            await self._make_request("DELETE", f"/orders/{order_id}")
            logger.info(f"Cancelled order: {order_id}")
            return True

        except PolymarketError as e:
            raise PolymarketOrderError(f"Failed to cancel order {order_id}: {e}")
        except Exception as e:
            raise PolymarketOrderError(f"Failed to cancel order {order_id}: {e}")

    async def get_order(self, order_id: str) -> Order:
        """
        Fetch details for a specific order.

        Args:
            order_id: Order identifier

        Returns:
            Order object

        Raises:
            PolymarketError: If request fails
        """
        try:
            data = await self._make_request("GET", f"/orders/{order_id}")
            return Order.from_dict(data)

        except PolymarketError:
            raise
        except Exception as e:
            raise PolymarketAPIError(f"Failed to fetch order {order_id}: {e}")

    async def get_orders(
        self,
        market_id: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> List[Order]:
        """
        Fetch orders.

        Args:
            market_id: Filter by market ID
            status: Filter by order status
            limit: Maximum number of orders to return

        Returns:
            List of Order objects

        Raises:
            PolymarketError: If request fails
        """
        params = {"limit": limit}
        if market_id:
            params["market_id"] = market_id
        if status:
            params["status"] = status.value

        try:
            data = await self._make_request("GET", "/orders", params=params)
            orders = []

            # Handle different response formats
            order_list = data if isinstance(data, list) else data.get("orders", [])

            for order_data in order_list:
                try:
                    order = Order.from_dict(order_data)
                    orders.append(order)
                except Exception as e:
                    logger.warning(f"Failed to parse order: {e}")
                    continue

            logger.info(f"Fetched {len(orders)} orders")
            return orders

        except PolymarketError:
            raise
        except Exception as e:
            raise PolymarketAPIError(f"Failed to fetch orders: {e}")

    # ============================================================================
    # Position Monitoring Methods
    # ============================================================================

    async def get_positions(self, market_id: Optional[str] = None) -> List[Position]:
        """
        Fetch current positions.

        Args:
            market_id: Filter by market ID (optional)

        Returns:
            List of Position objects

        Raises:
            PolymarketError: If request fails
        """
        params = {}
        if market_id:
            params["market_id"] = market_id

        try:
            data = await self._make_request("GET", "/positions", params=params)
            positions = []

            # Handle different response formats
            position_list = data if isinstance(data, list) else data.get("positions", [])

            for position_data in position_list:
                try:
                    position = Position.from_dict(position_data)
                    positions.append(position)
                except Exception as e:
                    logger.warning(f"Failed to parse position: {e}")
                    continue

            logger.info(f"Fetched {len(positions)} positions")
            return positions

        except PolymarketError:
            raise
        except Exception as e:
            raise PolymarketAPIError(f"Failed to fetch positions: {e}")

    async def get_position(self, market_id: str, outcome: str) -> Optional[Position]:
        """
        Fetch position for a specific market and outcome.

        Args:
            market_id: Market identifier
            outcome: Outcome (e.g., "YES", "NO")

        Returns:
            Position object or None if no position exists

        Raises:
            PolymarketError: If request fails
        """
        positions = await self.get_positions(market_id=market_id)
        for position in positions:
            if position.market_id == market_id and position.outcome == outcome:
                return position
        return None

    async def get_balance(self) -> Dict[str, float]:
        """
        Fetch account balance.

        Returns:
            Dictionary with balance information

        Raises:
            PolymarketError: If request fails
        """
        try:
            data = await self._make_request("GET", "/balance")
            return {
                "total": float(data.get("total", 0.0)),
                "available": float(data.get("available", 0.0)),
                "reserved": float(data.get("reserved", 0.0)),
            }

        except PolymarketError:
            raise
        except Exception as e:
            raise PolymarketAPIError(f"Failed to fetch balance: {e}")
