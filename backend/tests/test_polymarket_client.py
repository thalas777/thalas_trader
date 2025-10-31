"""
Comprehensive tests for Polymarket API client.

This test suite covers:
- Model validation and serialization
- Mock client functionality
- Error handling
- Order placement and management
- Position tracking
- Market data fetching
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from polymarket_client import (
    PolymarketClient,
    MockPolymarketClient,
    Market,
    Order,
    Position,
    OrderSide,
    OrderStatus,
    OrderType,
    MarketStatus,
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


# ============================================================================
# Model Tests
# ============================================================================


class TestMarketModel:
    """Test Market data model."""

    def test_market_creation(self):
        """Test creating a Market instance."""
        market = Market(
            id="test_market",
            question="Will BTC reach $50k?",
            description="BTC price market",
            end_date=datetime.now() + timedelta(days=30),
            status=MarketStatus.ACTIVE,
            yes_price=0.65,
            no_price=0.35,
            volume=100000.0,
            liquidity=50000.0,
        )

        assert market.id == "test_market"
        assert market.yes_price == 0.65
        assert market.no_price == 0.35
        assert market.implied_probability_yes == 0.65
        assert market.implied_probability_no == 0.35

    def test_market_price_validation(self):
        """Test Market price validation."""
        with pytest.raises(ValueError, match="yes_price must be between"):
            Market(
                id="test",
                question="Test?",
                description="Test",
                end_date=datetime.now(),
                status=MarketStatus.ACTIVE,
                yes_price=1.5,  # Invalid
                no_price=0.5,
            )

    def test_market_volume_validation(self):
        """Test Market volume validation."""
        with pytest.raises(ValueError, match="volume must be non-negative"):
            Market(
                id="test",
                question="Test?",
                description="Test",
                end_date=datetime.now(),
                status=MarketStatus.ACTIVE,
                yes_price=0.5,
                no_price=0.5,
                volume=-100,  # Invalid
            )

    def test_market_serialization(self):
        """Test Market to_dict and from_dict."""
        original = Market(
            id="test_market",
            question="Test?",
            description="Test market",
            end_date=datetime.now(),
            status=MarketStatus.ACTIVE,
            yes_price=0.6,
            no_price=0.4,
        )

        data = original.to_dict()
        restored = Market.from_dict(data)

        assert restored.id == original.id
        assert restored.question == original.question
        assert restored.yes_price == original.yes_price
        assert restored.status == original.status


class TestOrderModel:
    """Test Order data model."""

    def test_order_creation(self):
        """Test creating an Order instance."""
        order = Order(
            id="order_123",
            market_id="market_456",
            side=OrderSide.BUY,
            outcome="YES",
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
            price=0.65,
            size=100.0,
        )

        assert order.id == "order_123"
        assert order.side == OrderSide.BUY
        assert order.price == 0.65
        assert order.size == 100.0
        assert order.filled_size == 0.0
        assert order.remaining_size == 100.0

    def test_order_fill_percentage(self):
        """Test Order fill percentage calculation."""
        order = Order(
            id="order_123",
            market_id="market_456",
            side=OrderSide.BUY,
            outcome="YES",
            order_type=OrderType.LIMIT,
            status=OrderStatus.PARTIALLY_FILLED,
            price=0.65,
            size=100.0,
            filled_size=75.0,
        )

        assert order.fill_percentage == 0.75
        assert not order.is_filled

        order.filled_size = 100.0
        assert order.fill_percentage == 1.0

    def test_order_price_validation(self):
        """Test Order price validation."""
        with pytest.raises(ValueError, match="price must be between"):
            Order(
                id="order_123",
                market_id="market_456",
                side=OrderSide.BUY,
                outcome="YES",
                order_type=OrderType.LIMIT,
                status=OrderStatus.OPEN,
                price=1.5,  # Invalid
                size=100.0,
            )

    def test_order_size_validation(self):
        """Test Order size validation."""
        with pytest.raises(ValueError, match="size must be positive"):
            Order(
                id="order_123",
                market_id="market_456",
                side=OrderSide.BUY,
                outcome="YES",
                order_type=OrderType.LIMIT,
                status=OrderStatus.OPEN,
                price=0.65,
                size=-100.0,  # Invalid
            )

    def test_order_serialization(self):
        """Test Order to_dict and from_dict."""
        original = Order(
            id="order_123",
            market_id="market_456",
            side=OrderSide.BUY,
            outcome="YES",
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
            price=0.65,
            size=100.0,
            filled_size=25.0,
        )

        data = original.to_dict()
        restored = Order.from_dict(data)

        assert restored.id == original.id
        assert restored.side == original.side
        assert restored.price == original.price
        assert restored.filled_size == original.filled_size


class TestPositionModel:
    """Test Position data model."""

    def test_position_creation(self):
        """Test creating a Position instance."""
        position = Position(
            market_id="market_123",
            outcome="YES",
            size=100.0,
            average_entry_price=0.65,
            current_price=0.70,
        )

        assert position.market_id == "market_123"
        assert position.size == 100.0
        assert position.cost_basis == 65.0  # 100 * 0.65
        assert position.market_value == 70.0  # 100 * 0.70
        assert position.unrealized_pnl == 5.0  # 70 - 65
        assert position.is_profitable

    def test_position_pnl_calculation(self):
        """Test Position PnL calculations."""
        position = Position(
            market_id="market_123",
            outcome="YES",
            size=100.0,
            average_entry_price=0.70,
            current_price=0.60,  # Price went down
            realized_pnl=5.0,
        )

        assert position.unrealized_pnl == -10.0  # (60 - 70)
        assert position.total_pnl == -5.0  # -10 + 5
        assert not position.is_profitable

    def test_position_pnl_percentage(self):
        """Test Position PnL percentage."""
        position = Position(
            market_id="market_123",
            outcome="YES",
            size=100.0,
            average_entry_price=0.50,
            current_price=0.75,
        )

        # Cost basis = 50, Market value = 75, PnL = 25
        # PnL % = (25 / 50) * 100 = 50%
        assert position.pnl_percentage == 50.0

    def test_position_serialization(self):
        """Test Position to_dict and from_dict."""
        original = Position(
            market_id="market_123",
            outcome="YES",
            size=100.0,
            average_entry_price=0.65,
            current_price=0.70,
        )

        data = original.to_dict()
        restored = Position.from_dict(data)

        assert restored.market_id == original.market_id
        assert restored.size == original.size
        assert restored.average_entry_price == original.average_entry_price


# ============================================================================
# Mock Client Tests
# ============================================================================


@pytest.mark.asyncio
class TestMockPolymarketClient:
    """Test MockPolymarketClient functionality."""

    async def test_mock_client_initialization(self):
        """Test mock client initialization."""
        async with MockPolymarketClient(initial_balance=5000.0) as client:
            balance = await client.get_balance()
            assert balance["total"] == 5000.0
            assert balance["available"] == 5000.0

    async def test_mock_get_markets(self):
        """Test fetching markets from mock client."""
        async with MockPolymarketClient() as client:
            markets = await client.get_markets()
            assert len(markets) >= 3  # Should have sample markets
            assert all(isinstance(m, Market) for m in markets)

    async def test_mock_get_market(self):
        """Test fetching specific market."""
        async with MockPolymarketClient() as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            market = await client.get_market(market_id)
            assert market.id == market_id

    async def test_mock_market_not_found(self):
        """Test market not found error."""
        async with MockPolymarketClient() as client:
            with pytest.raises(PolymarketMarketNotFoundError):
                await client.get_market("nonexistent_market")

    async def test_mock_get_market_prices(self):
        """Test fetching market prices."""
        async with MockPolymarketClient() as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            prices = await client.get_market_prices(market_id)
            assert "YES" in prices
            assert "NO" in prices
            assert 0.0 <= prices["YES"] <= 1.0
            assert 0.0 <= prices["NO"] <= 1.0

    async def test_mock_place_order(self):
        """Test placing an order."""
        async with MockPolymarketClient(initial_balance=10000.0) as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            order = await client.place_order(
                market_id=market_id,
                side=OrderSide.BUY,
                outcome="YES",
                price=0.65,
                size=100.0,
                order_type=OrderType.LIMIT,
            )

            assert order.id is not None
            assert order.market_id == market_id
            assert order.side == OrderSide.BUY
            assert order.price == 0.65
            assert order.size == 100.0
            assert order.status in [OrderStatus.OPEN, OrderStatus.FILLED]

    async def test_mock_place_market_order(self):
        """Test placing a market order (should fill immediately)."""
        async with MockPolymarketClient(initial_balance=10000.0) as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            order = await client.place_order(
                market_id=market_id,
                side=OrderSide.BUY,
                outcome="YES",
                price=0.65,
                size=100.0,
                order_type=OrderType.MARKET,
            )

            # Market orders should be filled or partially filled
            assert order.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]
            assert order.filled_size > 0

    async def test_mock_insufficient_funds(self):
        """Test insufficient funds error."""
        async with MockPolymarketClient(initial_balance=10.0) as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            with pytest.raises(PolymarketInsufficientFundsError):
                await client.place_order(
                    market_id=market_id,
                    side=OrderSide.BUY,
                    outcome="YES",
                    price=0.65,
                    size=1000.0,  # Too large
                )

    async def test_mock_invalid_order_price(self):
        """Test invalid order price."""
        async with MockPolymarketClient() as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            with pytest.raises(PolymarketValidationError):
                await client.place_order(
                    market_id=market_id,
                    side=OrderSide.BUY,
                    outcome="YES",
                    price=1.5,  # Invalid price
                    size=100.0,
                )

    async def test_mock_cancel_order(self):
        """Test cancelling an order."""
        async with MockPolymarketClient() as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            # Place order
            order = await client.place_order(
                market_id=market_id,
                side=OrderSide.BUY,
                outcome="YES",
                price=0.65,
                size=100.0,
                order_type=OrderType.LIMIT,
            )

            # Cancel order
            result = await client.cancel_order(order.id)
            assert result is True

            # Check order status
            cancelled_order = await client.get_order(order.id)
            assert cancelled_order.status == OrderStatus.CANCELLED

    async def test_mock_get_orders(self):
        """Test fetching orders."""
        async with MockPolymarketClient() as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            # Place some orders
            for i in range(3):
                await client.place_order(
                    market_id=market_id,
                    side=OrderSide.BUY,
                    outcome="YES",
                    price=0.65,
                    size=10.0,
                    order_type=OrderType.LIMIT,
                )

            # Fetch all orders
            orders = await client.get_orders()
            assert len(orders) >= 3

            # Fetch orders for specific market
            market_orders = await client.get_orders(market_id=market_id)
            assert len(market_orders) >= 3
            assert all(o.market_id == market_id for o in market_orders)

    async def test_mock_get_positions(self):
        """Test fetching positions."""
        async with MockPolymarketClient() as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            # Place and fill an order to create position
            order = await client.place_order(
                market_id=market_id,
                side=OrderSide.BUY,
                outcome="YES",
                price=0.65,
                size=100.0,
                order_type=OrderType.MARKET,  # Market orders fill immediately
            )

            # Get positions
            positions = await client.get_positions()

            # Check if position was created (depends on fill)
            if order.filled_size > 0:
                assert len(positions) > 0
                position = positions[0]
                assert position.market_id == market_id
                assert position.size > 0

    async def test_mock_get_position(self):
        """Test fetching specific position."""
        async with MockPolymarketClient() as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            # Place and fill an order
            await client.place_order(
                market_id=market_id,
                side=OrderSide.BUY,
                outcome="YES",
                price=0.65,
                size=100.0,
                order_type=OrderType.MARKET,
            )

            # Get specific position
            position = await client.get_position(market_id, "YES")
            if position:  # Position exists if order was filled
                assert position.market_id == market_id
                assert position.outcome == "YES"

    async def test_mock_get_balance(self):
        """Test fetching balance."""
        async with MockPolymarketClient(initial_balance=10000.0) as client:
            balance = await client.get_balance()
            assert balance["total"] == 10000.0
            assert balance["available"] <= 10000.0
            assert "reserved" in balance

    async def test_mock_health_check(self):
        """Test health check."""
        async with MockPolymarketClient() as client:
            result = await client.health_check()
            assert result is True

    async def test_mock_error_simulation(self):
        """Test error simulation."""
        async with MockPolymarketClient(
            simulate_errors=True,
            error_probability=1.0  # Always simulate errors
        ) as client:
            with pytest.raises(PolymarketError):
                await client.get_markets()

    async def test_mock_reset(self):
        """Test resetting mock client state."""
        async with MockPolymarketClient() as client:
            # Place an order
            markets = await client.get_markets()
            await client.place_order(
                market_id=markets[0].id,
                side=OrderSide.BUY,
                outcome="YES",
                price=0.65,
                size=100.0,
            )

            # Reset
            client.reset()

            # Check state is reset
            orders = await client.get_orders()
            assert len(orders) == 0
            balance = await client.get_balance()
            assert balance["available"] == 10000.0


# ============================================================================
# Real Client Tests (with mocked HTTP)
# ============================================================================


@pytest.mark.asyncio
class TestPolymarketClient:
    """Test PolymarketClient with mocked HTTP requests."""

    async def test_client_initialization(self):
        """Test client initialization."""
        client = PolymarketClient(
            api_key="test_key",
            api_secret="test_secret",
        )
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"

    @patch("httpx.AsyncClient.request")
    async def test_get_markets_success(self, mock_request):
        """Test successful markets fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "market_1",
                "question": "Test?",
                "description": "Test market",
                "end_date": datetime.now().isoformat(),
                "status": "ACTIVE",
                "yes_price": 0.65,
                "no_price": 0.35,
            }
        ]
        mock_request.return_value = mock_response

        async with PolymarketClient(api_key="test") as client:
            markets = await client.get_markets()
            assert len(markets) == 1
            assert markets[0].id == "market_1"

    @patch("httpx.AsyncClient.request")
    async def test_authentication_error(self, mock_request):
        """Test authentication error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_request.return_value = mock_response

        async with PolymarketClient(api_key="invalid") as client:
            with pytest.raises(PolymarketAuthenticationError):
                await client.get_markets()

    @patch("httpx.AsyncClient.request")
    async def test_rate_limit_error(self, mock_request):
        """Test rate limit error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = "Rate limited"
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_request.return_value = mock_response

        async with PolymarketClient(api_key="test", max_retries=0) as client:
            with pytest.raises(PolymarketRateLimitError) as exc_info:
                await client.get_markets()
            assert exc_info.value.retry_after == 60

    @patch("httpx.AsyncClient.request")
    async def test_timeout_error(self, mock_request):
        """Test timeout error handling."""
        mock_request.side_effect = httpx.TimeoutException("Timeout")

        async with PolymarketClient(api_key="test", max_retries=0) as client:
            with pytest.raises(PolymarketTimeoutError):
                await client.get_markets()

    @patch("httpx.AsyncClient.request")
    async def test_validation_error(self, mock_request):
        """Test validation error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.json.return_value = {"message": "Invalid parameters"}
        mock_request.return_value = mock_response

        async with PolymarketClient(api_key="test") as client:
            with pytest.raises(PolymarketValidationError):
                await client.get_markets()

    @patch("httpx.AsyncClient.request")
    async def test_server_error(self, mock_request):
        """Test server error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.json.return_value = {"error": "Server error"}
        mock_request.return_value = mock_response

        async with PolymarketClient(api_key="test", max_retries=0) as client:
            with pytest.raises(PolymarketAPIError):
                await client.get_markets()

    @patch("httpx.AsyncClient.request")
    async def test_retry_logic(self, mock_request):
        """Test retry logic for transient errors."""
        # First two calls fail, third succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Error"
        mock_response_fail.json.return_value = {}

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = []

        mock_request.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success,
        ]

        async with PolymarketClient(api_key="test", max_retries=3) as client:
            markets = await client.get_markets()
            assert isinstance(markets, list)
            assert mock_request.call_count == 3


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
class TestPolymarketIntegration:
    """Integration tests using mock client."""

    async def test_full_trading_workflow(self):
        """Test complete trading workflow."""
        async with MockPolymarketClient(initial_balance=10000.0) as client:
            # 1. Fetch markets
            markets = await client.get_markets()
            assert len(markets) > 0
            market = markets[0]

            # 2. Check prices
            prices = await client.get_market_prices(market.id)
            assert "YES" in prices

            # 3. Check balance
            initial_balance = await client.get_balance()
            assert initial_balance["available"] == 10000.0

            # 4. Place order
            order = await client.place_order(
                market_id=market.id,
                side=OrderSide.BUY,
                outcome="YES",
                price=0.65,
                size=100.0,
                order_type=OrderType.MARKET,
            )
            assert order.id is not None

            # 5. Check balance after order
            new_balance = await client.get_balance()
            assert new_balance["available"] < initial_balance["available"]

            # 6. Get orders
            orders = await client.get_orders(market_id=market.id)
            assert len(orders) > 0

            # 7. Get positions
            positions = await client.get_positions(market_id=market.id)
            if order.filled_size > 0:
                assert len(positions) > 0

    async def test_multiple_orders_same_market(self):
        """Test placing multiple orders in the same market."""
        async with MockPolymarketClient(initial_balance=10000.0) as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            # Place 3 orders
            orders = []
            for i in range(3):
                order = await client.place_order(
                    market_id=market_id,
                    side=OrderSide.BUY,
                    outcome="YES",
                    price=0.60 + (i * 0.01),
                    size=50.0,
                    order_type=OrderType.LIMIT,
                )
                orders.append(order)

            # Verify all orders created
            assert len(orders) == 3
            assert all(o.market_id == market_id for o in orders)

            # Fetch orders
            fetched_orders = await client.get_orders(market_id=market_id)
            assert len(fetched_orders) >= 3

    async def test_order_lifecycle(self):
        """Test complete order lifecycle."""
        async with MockPolymarketClient() as client:
            markets = await client.get_markets()
            market_id = markets[0].id

            # Place order
            order = await client.place_order(
                market_id=market_id,
                side=OrderSide.BUY,
                outcome="YES",
                price=0.65,
                size=100.0,
                order_type=OrderType.LIMIT,
            )

            # Verify order is open
            assert order.status in [OrderStatus.OPEN, OrderStatus.FILLED]

            # Get order details
            fetched_order = await client.get_order(order.id)
            assert fetched_order.id == order.id

            # Cancel order (if still open)
            if order.status == OrderStatus.OPEN:
                cancelled = await client.cancel_order(order.id)
                assert cancelled is True

                # Verify cancellation
                updated_order = await client.get_order(order.id)
                assert updated_order.status == OrderStatus.CANCELLED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
