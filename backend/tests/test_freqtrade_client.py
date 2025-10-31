"""
Unit tests for Freqtrade Client
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from freqtrade_client.client import FreqtradeClient, FreqtradeClientError


class TestFreqtradeClient:
    """Test suite for FreqtradeClient"""

    def test_client_initialization(self):
        """Test client initializes with default settings"""
        client = FreqtradeClient()
        assert client.api_url is not None
        assert isinstance(client.api_url, str)

    def test_client_custom_url(self):
        """Test client accepts custom API URL"""
        custom_url = "http://custom:8080"
        client = FreqtradeClient(api_url=custom_url)
        assert client.api_url == custom_url

    @patch('freqtrade_client.client.requests.Session.post')
    def test_authentication_success(self, mock_post):
        """Test successful authentication"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_token'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = FreqtradeClient(
            api_url="http://test:8080",
            username="test_user",
            password="test_pass"
        )

        assert 'Authorization' in client.session.headers

    def test_get_summary_mock_data(self):
        """Test get_summary returns mock data when Freqtrade unavailable"""
        client = FreqtradeClient(api_url="http://invalid:9999")
        summary = client.get_summary()

        assert 'total_profit' in summary
        assert 'profit_24h' in summary
        assert 'active_bots' in summary
        assert 'total_trades' in summary
        assert isinstance(summary['total_profit'], (int, float))

    def test_get_bots_mock_data(self):
        """Test get_bots returns mock data"""
        client = FreqtradeClient(api_url="http://invalid:9999")
        bots = client.get_bots()

        assert isinstance(bots, list)
        assert len(bots) > 0
        assert 'bot_id' in bots[0]
        assert 'status' in bots[0]

    def test_get_trades_mock_data(self):
        """Test get_trades returns mock data"""
        client = FreqtradeClient(api_url="http://invalid:9999")
        trades = client.get_trades()

        assert isinstance(trades, list)
        if len(trades) > 0:
            assert 'trade_id' in trades[0]
            assert 'pair' in trades[0]

    def test_get_trades_with_pagination(self):
        """Test get_trades accepts pagination parameters"""
        client = FreqtradeClient(api_url="http://invalid:9999")
        trades = client.get_trades(limit=5, offset=10)

        assert isinstance(trades, list)

    def test_get_performance_mock_data(self):
        """Test get_performance returns mock data"""
        client = FreqtradeClient(api_url="http://invalid:9999")
        performance = client.get_performance()

        assert isinstance(performance, list)

    def test_start_bot(self):
        """Test start_bot method"""
        client = FreqtradeClient(api_url="http://invalid:9999")
        result = client.start_bot(1)

        assert 'status' in result
        assert 'message' in result

    def test_stop_bot(self):
        """Test stop_bot method"""
        client = FreqtradeClient(api_url="http://invalid:9999")
        result = client.stop_bot(1)

        assert 'status' in result
        assert 'message' in result

    def test_get_freqtrade_client_singleton(self):
        """Test singleton pattern for client"""
        from freqtrade_client.client import get_freqtrade_client

        client1 = get_freqtrade_client()
        client2 = get_freqtrade_client()

        assert client1 is client2
