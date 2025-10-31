"""
Test cases for API endpoints
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class SummaryEndpointTests(TestCase):
    """Tests for /api/v1/summary endpoint"""

    def setUp(self):
        self.client = APIClient()

    def test_summary_returns_200(self):
        """Test that summary endpoint returns 200 OK"""
        response = self.client.get('/api/v1/summary')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_summary_has_required_fields(self):
        """Test that summary response contains required fields"""
        response = self.client.get('/api/v1/summary')
        data = response.json()

        required_fields = [
            'total_profit',
            'profit_24h',
            'active_bots',
            'total_trades',
            'win_rate'
        ]

        for field in required_fields:
            self.assertIn(field, data, f"Missing required field: {field}")

    def test_summary_data_types(self):
        """Test that summary fields have correct data types"""
        response = self.client.get('/api/v1/summary')
        data = response.json()

        self.assertIsInstance(data['total_profit'], (int, float))
        self.assertIsInstance(data['profit_24h'], (int, float))
        self.assertIsInstance(data['active_bots'], int)
        self.assertIsInstance(data['total_trades'], int)
        self.assertIsInstance(data['win_rate'], (int, float))


class BotEndpointTests(TestCase):
    """Tests for bot-related endpoints"""

    def setUp(self):
        self.client = APIClient()

    def test_bot_list_returns_200(self):
        """Test that bot list endpoint returns 200 OK"""
        response = self.client.get('/api/v1/bots')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bot_list_returns_array(self):
        """Test that bot list returns an array"""
        response = self.client.get('/api/v1/bots')
        data = response.json()
        self.assertIsInstance(data, list)

    def test_bot_detail_valid_id(self):
        """Test bot detail with valid ID"""
        response = self.client.get('/api/v1/bots/1')
        # Should return 200 if mock data includes bot_id 1
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_bot_detail_invalid_id(self):
        """Test bot detail with invalid ID"""
        response = self.client.get('/api/v1/bots/9999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bot_start_endpoint(self):
        """Test bot start endpoint"""
        response = self.client.post('/api/v1/bots/1/start')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bot_stop_endpoint(self):
        """Test bot stop endpoint"""
        response = self.client.post('/api/v1/bots/1/stop')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TradeEndpointTests(TestCase):
    """Tests for trade-related endpoints"""

    def setUp(self):
        self.client = APIClient()

    def test_trade_list_returns_200(self):
        """Test that trade list endpoint returns 200 OK"""
        response = self.client.get('/api/v1/trades')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_trade_list_response_structure(self):
        """Test trade list response structure"""
        response = self.client.get('/api/v1/trades')
        data = response.json()

        self.assertIn('trades', data)
        self.assertIn('limit', data)
        self.assertIn('offset', data)
        self.assertIn('count', data)

    def test_trade_list_pagination(self):
        """Test trade list pagination parameters"""
        response = self.client.get('/api/v1/trades?limit=5&offset=0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['limit'], 5)
        self.assertEqual(data['offset'], 0)

    def test_trade_detail_valid_id(self):
        """Test trade detail with valid ID"""
        response = self.client.get('/api/v1/trades/1')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_trade_detail_invalid_id(self):
        """Test trade detail with invalid ID"""
        response = self.client.get('/api/v1/trades/9999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PerformanceEndpointTests(TestCase):
    """Tests for performance endpoint"""

    def setUp(self):
        self.client = APIClient()

    def test_performance_returns_200(self):
        """Test that performance endpoint returns 200 OK"""
        response = self.client.get('/api/v1/performance')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_performance_returns_array(self):
        """Test that performance endpoint returns an array"""
        response = self.client.get('/api/v1/performance')
        data = response.json()
        self.assertIsInstance(data, list)


class LLMStrategyEndpointTests(TestCase):
    """Tests for LLM strategy endpoint"""

    def setUp(self):
        self.client = APIClient()

    def test_llm_health_check(self):
        """Test LLM health check endpoint"""
        response = self.client.get('/api/v1/strategies/llm')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_llm_signal_missing_data(self):
        """Test LLM signal with missing required data"""
        response = self.client.post('/api/v1/strategies/llm', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_llm_signal_missing_pair(self):
        """Test LLM signal with missing pair"""
        data = {
            "market_data": {"rsi": 45}
        }
        response = self.client.post('/api/v1/strategies/llm', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_llm_signal_with_valid_data(self):
        """Test LLM signal with valid data (may fail if LLM not configured)"""
        data = {
            "market_data": {
                "rsi": 45.2,
                "ema_short": 42500.0,
                "ema_long": 42300.0,
                "volume": 1250000,
            },
            "pair": "BTC/USDT",
            "timeframe": "5m",
            "current_price": 42500.0
        }
        response = self.client.post('/api/v1/strategies/llm', data, format='json')
        # Will be 503 if LLM not configured, 200 if configured
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
        )
