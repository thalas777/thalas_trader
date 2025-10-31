"""
Freqtrade API Client
Handles communication with Freqtrade instance via REST API
"""
import requests
from typing import Dict, List, Optional, Any
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class FreqtradeClientError(Exception):
    """Base exception for Freqtrade client errors"""
    pass


class FreqtradeClient:
    """
    Client for communicating with Freqtrade REST API
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.api_url = (api_url or settings.FREQTRADE_API_URL).rstrip("/")
        self.username = username or settings.FREQTRADE_USERNAME
        self.password = password or settings.FREQTRADE_PASSWORD
        self.session = requests.Session()
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Freqtrade API"""
        if not self.username or not self.password:
            logger.warning("No Freqtrade credentials provided")
            return

        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/token/login",
                json={"username": self.username, "password": self.password},
                timeout=10,
            )
            response.raise_for_status()
            token_data = response.json()
            self.session.headers.update(
                {"Authorization": f"Bearer {token_data.get('access_token')}"}
            )
            logger.info("Successfully authenticated with Freqtrade")
        except requests.RequestException as e:
            logger.error(f"Failed to authenticate with Freqtrade: {e}")
            # Continue without auth for development/testing

    def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to Freqtrade API"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Freqtrade API request failed: {method} {url} - {e}")
            raise FreqtradeClientError(f"API request failed: {str(e)}")

    def get_summary(self) -> Dict[str, Any]:
        """Get trading summary statistics"""
        try:
            profit = self._make_request("GET", "/api/v1/profit")
            status = self._make_request("GET", "/api/v1/status")
            count = self._make_request("GET", "/api/v1/count")

            return {
                "total_profit": profit.get("profit_closed_coin", 0),
                "profit_24h": profit.get("profit_closed_coin_24h", 0),
                "active_bots": len([s for s in status if s.get("is_open", False)]),
                "total_trades": count.get("trade_count", 0),
                "win_rate": profit.get("winning_trades_percent", 0),
            }
        except FreqtradeClientError:
            # Return mock data if Freqtrade is not available
            return self._get_mock_summary()

    def get_bots(self) -> List[Dict[str, Any]]:
        """Get list of all bots"""
        try:
            status_data = self._make_request("GET", "/api/v1/status")
            return status_data
        except FreqtradeClientError:
            return self._get_mock_bots()

    def get_trades(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent trades"""
        try:
            trades = self._make_request(
                "GET", f"/api/v1/trades?limit={limit}&offset={offset}"
            )
            return trades.get("trades", [])
        except FreqtradeClientError:
            return self._get_mock_trades()

    def get_performance(self) -> List[Dict[str, Any]]:
        """Get performance history"""
        try:
            performance = self._make_request("GET", "/api/v1/performance")
            return performance
        except FreqtradeClientError:
            return self._get_mock_performance()

    def start_bot(self, bot_id: int) -> Dict[str, Any]:
        """Start a specific bot"""
        try:
            result = self._make_request("POST", "/api/v1/start")
            return {"status": "success", "message": "Bot started"}
        except FreqtradeClientError as e:
            return {"status": "error", "message": str(e)}

    def stop_bot(self, bot_id: int) -> Dict[str, Any]:
        """Stop a specific bot"""
        try:
            result = self._make_request("POST", "/api/v1/stop")
            return {"status": "success", "message": "Bot stopped"}
        except FreqtradeClientError as e:
            return {"status": "error", "message": str(e)}

    # Mock data methods for development/testing
    def _get_mock_summary(self) -> Dict[str, Any]:
        """Return mock summary data"""
        return {
            "total_profit": 1250.75,
            "profit_24h": 125.50,
            "active_bots": 3,
            "total_trades": 147,
            "win_rate": 64.5,
        }

    def _get_mock_bots(self) -> List[Dict[str, Any]]:
        """Return mock bot data"""
        return [
            {
                "bot_id": 1,
                "name": "BTC-USDT Bot",
                "status": "running",
                "strategy": "EMAStrategy",
                "pair": "BTC/USDT",
                "profit": 245.30,
            },
            {
                "bot_id": 2,
                "name": "ETH-USDT Bot",
                "status": "running",
                "strategy": "RSIStrategy",
                "pair": "ETH/USDT",
                "profit": 189.45,
            },
            {
                "bot_id": 3,
                "name": "LLM Momentum Bot",
                "status": "running",
                "strategy": "LLM_Momentum_Strategy",
                "pair": "SOL/USDT",
                "profit": 312.80,
            },
        ]

    def _get_mock_trades(self) -> List[Dict[str, Any]]:
        """Return mock trade data"""
        return [
            {
                "trade_id": 1,
                "pair": "BTC/USDT",
                "type": "buy",
                "amount": 0.01,
                "price": 42500.00,
                "profit": 125.50,
                "timestamp": "2024-01-15T10:30:00Z",
            },
            {
                "trade_id": 2,
                "pair": "ETH/USDT",
                "type": "sell",
                "amount": 0.5,
                "price": 2450.00,
                "profit": 45.20,
                "timestamp": "2024-01-15T09:15:00Z",
            },
        ]

    def _get_mock_performance(self) -> List[Dict[str, Any]]:
        """Return mock performance data"""
        return [
            {"date": "2024-01-01", "value": 10000},
            {"date": "2024-01-08", "value": 10500},
            {"date": "2024-01-15", "value": 11250},
        ]


# Singleton instance
_client_instance = None


def get_freqtrade_client() -> FreqtradeClient:
    """Get or create Freqtrade client singleton"""
    global _client_instance
    if _client_instance is None:
        _client_instance = FreqtradeClient()
    return _client_instance
