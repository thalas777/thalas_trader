"""
Test suite for Risk Management API endpoints
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
import json


class TestRiskAPIEndpoints(TestCase):
    """Test suite for Risk Management API endpoints"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()

    def test_portfolio_risk_endpoint_success(self):
        """Test portfolio risk endpoint with valid data"""
        data = {
            "positions": [
                {
                    "id": "pos_1",
                    "pair": "BTC/USDT",
                    "market_type": "crypto",
                    "entry_price": 40000.0,
                    "current_price": 42000.0,
                    "amount": 0.5,
                    "value_usd": 21000.0,
                    "unrealized_pnl": 1000.0,
                    "leverage": 1.0,
                }
            ],
            "portfolio_value": 50000.0,
        }

        response = self.client.post(
            "/api/v1/risk/portfolio",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "metrics" in response_data
        assert "timestamp" in response_data
        assert response_data["metrics"]["position_count"] == 1
        assert response_data["metrics"]["total_exposure"] == 21000.0

    def test_portfolio_risk_endpoint_invalid_data(self):
        """Test portfolio risk endpoint with invalid data"""
        data = {
            "positions": [],
            # Missing portfolio_value
        }

        response = self.client.post(
            "/api/v1/risk/portfolio",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 400
        response_data = response.json()
        assert "error" in response_data

    def test_portfolio_risk_endpoint_mixed_markets(self):
        """Test portfolio risk with mixed market types"""
        data = {
            "positions": [
                {
                    "id": "pos_1",
                    "pair": "BTC/USDT",
                    "market_type": "crypto",
                    "entry_price": 40000.0,
                    "current_price": 42000.0,
                    "amount": 0.5,
                    "value_usd": 21000.0,
                    "unrealized_pnl": 1000.0,
                    "leverage": 1.0,
                },
                {
                    "id": "pos_2",
                    "pair": "ELECTION_2024",
                    "market_type": "polymarket",
                    "entry_price": 0.50,
                    "current_price": 0.55,
                    "amount": 1000.0,
                    "value_usd": 550.0,
                    "unrealized_pnl": 50.0,
                    "leverage": 1.0,
                },
            ],
            "portfolio_value": 50000.0,
        }

        response = self.client.post(
            "/api/v1/risk/portfolio",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["metrics"]["crypto_exposure"] == 21000.0
        assert response_data["metrics"]["polymarket_exposure"] == 550.0

    def test_position_risk_endpoint_success(self):
        """Test position risk endpoint with valid data"""
        data = {
            "position": {
                "id": "pos_1",
                "pair": "BTC/USDT",
                "market_type": "crypto",
                "entry_price": 40000.0,
                "current_price": 42000.0,
                "amount": 0.5,
                "value_usd": 21000.0,
                "unrealized_pnl": 1000.0,
                "leverage": 2.0,
                "stop_loss": 38000.0,
            },
            "portfolio_value": 100000.0,
        }

        response = self.client.post(
            "/api/v1/risk/position",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["position_id"] == "pos_1"
        assert response_data["pair"] == "BTC/USDT"
        assert response_data["position_size_pct"] == 21.0
        assert "risk_level" in response_data
        assert "recommended_stop_loss" in response_data

    def test_position_risk_endpoint_oversized(self):
        """Test position risk with oversized position"""
        data = {
            "position": {
                "id": "pos_1",
                "pair": "BTC/USDT",
                "market_type": "crypto",
                "entry_price": 40000.0,
                "current_price": 42000.0,
                "amount": 5.0,
                "value_usd": 210000.0,
                "unrealized_pnl": 10000.0,
                "leverage": 1.0,
            },
            "portfolio_value": 100000.0,
        }

        response = self.client.post(
            "/api/v1/risk/position",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["exceeds_max_size"] is True
        assert response_data["risk_level"] == "high"

    def test_signal_risk_endpoint_success(self):
        """Test signal risk evaluation endpoint"""
        data = {
            "consensus_metadata": {
                "weighted_confidence": 0.85,
                "agreement_score": 0.75,
                "participating_providers": 3,
                "total_providers": 4,
            },
        }

        response = self.client.post(
            "/api/v1/risk/evaluate-signal",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "risk_level" in response_data
        assert "signal_strength" in response_data
        assert "should_trade" in response_data
        assert "warnings" in response_data

    def test_signal_risk_endpoint_with_market_conditions(self):
        """Test signal risk evaluation with market conditions"""
        data = {
            "consensus_metadata": {
                "weighted_confidence": 0.75,
                "agreement_score": 0.70,
                "participating_providers": 3,
                "total_providers": 4,
            },
            "market_conditions": {
                "volatility": 0.25,
            },
        }

        response = self.client.post(
            "/api/v1/risk/evaluate-signal",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        # High volatility should reduce position size
        assert response_data["recommended_position_size_pct"] < 15.0

    def test_signal_risk_endpoint_missing_fields(self):
        """Test signal risk evaluation with missing required fields"""
        data = {
            "consensus_metadata": {
                "weighted_confidence": 0.85,
                # Missing required fields
            },
        }

        response = self.client.post(
            "/api/v1/risk/evaluate-signal",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_check_limits_endpoint_approved(self):
        """Test position limit check endpoint - approved"""
        data = {
            "positions": [
                {
                    "id": "pos_1",
                    "pair": "BTC/USDT",
                    "market_type": "crypto",
                    "entry_price": 40000.0,
                    "current_price": 42000.0,
                    "amount": 0.5,
                    "value_usd": 21000.0,
                    "unrealized_pnl": 1000.0,
                    "leverage": 1.0,
                }
            ],
            "new_position_value": 5000.0,
            "new_position_type": "crypto",
            "portfolio_value": 100000.0,
        }

        response = self.client.post(
            "/api/v1/risk/check-limits",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["approved"] is True
        assert len(response_data["violations"]) == 0

    def test_check_limits_endpoint_rejected(self):
        """Test position limit check endpoint - rejected"""
        data = {
            "positions": [],
            "new_position_value": 20000.0,  # 20% of portfolio
            "new_position_type": "crypto",
            "portfolio_value": 100000.0,
        }

        response = self.client.post(
            "/api/v1/risk/check-limits",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["approved"] is False
        assert len(response_data["violations"]) > 0

    def test_check_limits_endpoint_max_positions(self):
        """Test position limit check with max positions reached"""
        positions = [
            {
                "id": f"pos_{i}",
                "pair": f"PAIR_{i}/USDT",
                "market_type": "crypto",
                "entry_price": 1000.0,
                "current_price": 1100.0,
                "amount": 1.0,
                "value_usd": 1100.0,
                "unrealized_pnl": 100.0,
                "leverage": 1.0,
            }
            for i in range(10)
        ]

        data = {
            "positions": positions,
            "new_position_value": 1000.0,
            "new_position_type": "crypto",
            "portfolio_value": 100000.0,
        }

        response = self.client.post(
            "/api/v1/risk/check-limits",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["approved"] is False
        assert any("Maximum positions" in v for v in response_data["violations"])

    def test_calculate_stop_loss_endpoint_long(self):
        """Test stop loss calculation endpoint for long position"""
        data = {
            "entry_price": 50000.0,
            "position_type": "LONG",
            "volatility": 0.10,
            "market_type": "crypto",
            "risk_per_trade": 0.02,
        }

        response = self.client.post(
            "/api/v1/risk/calculate-stop-loss",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "stop_loss" in response_data
        assert "take_profit" in response_data
        assert response_data["stop_loss"] < 50000.0
        assert response_data["take_profit"] > 50000.0
        assert response_data["risk_reward_ratio"] > 1.0

    def test_calculate_stop_loss_endpoint_short(self):
        """Test stop loss calculation endpoint for short position"""
        data = {
            "entry_price": 50000.0,
            "position_type": "SHORT",
            "volatility": 0.10,
            "market_type": "crypto",
            "risk_per_trade": 0.02,
        }

        response = self.client.post(
            "/api/v1/risk/calculate-stop-loss",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["stop_loss"] > 50000.0
        assert response_data["take_profit"] < 50000.0

    def test_calculate_stop_loss_endpoint_polymarket(self):
        """Test stop loss calculation for polymarket position"""
        data = {
            "entry_price": 0.60,
            "position_type": "LONG",
            "volatility": 0.05,
            "market_type": "polymarket",
            "risk_per_trade": 0.02,
        }

        response = self.client.post(
            "/api/v1/risk/calculate-stop-loss",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["stop_loss"] < 0.60
        assert response_data["take_profit"] > 0.60

    def test_calculate_stop_loss_endpoint_invalid_data(self):
        """Test stop loss calculation with invalid data"""
        data = {
            "entry_price": -50000.0,  # Invalid negative price
            "position_type": "LONG",
            "volatility": 0.10,
            "market_type": "crypto",
        }

        response = self.client.post(
            "/api/v1/risk/calculate-stop-loss",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_all_endpoints_exist(self):
        """Test that all risk endpoints are properly registered"""
        endpoints = [
            "/api/v1/risk/portfolio",
            "/api/v1/risk/position",
            "/api/v1/risk/evaluate-signal",
            "/api/v1/risk/check-limits",
            "/api/v1/risk/calculate-stop-loss",
        ]

        for endpoint in endpoints:
            # Test that endpoint exists (even if it returns error without data)
            response = self.client.post(
                endpoint,
                data=json.dumps({}),
                content_type="application/json",
            )
            # Should not be 404
            assert response.status_code != 404

    def test_portfolio_risk_empty_positions(self):
        """Test portfolio risk with empty positions list"""
        data = {
            "positions": [],
            "portfolio_value": 50000.0,
        }

        response = self.client.post(
            "/api/v1/risk/portfolio",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["metrics"]["position_count"] == 0
        assert response_data["metrics"]["total_exposure"] == 0.0

    def test_high_leverage_position_risk(self):
        """Test position risk with high leverage"""
        data = {
            "position": {
                "id": "pos_1",
                "pair": "BTC/USDT",
                "market_type": "crypto",
                "entry_price": 40000.0,
                "current_price": 42000.0,
                "amount": 0.5,
                "value_usd": 21000.0,
                "unrealized_pnl": 1000.0,
                "leverage": 10.0,  # Very high leverage
            },
            "portfolio_value": 100000.0,
        }

        response = self.client.post(
            "/api/v1/risk/position",
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["leverage"] == 10.0
        # High leverage should result in higher risk
        assert response_data["risk_level"] in ["medium", "high"]
