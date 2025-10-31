"""
Comprehensive test suite for Risk Management module
"""
import pytest
from api.services.risk_manager import (
    RiskManager,
    Position,
    MarketType,
    RiskLevel,
    RiskMetrics,
)


class TestRiskManager:
    """Test suite for RiskManager core functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.risk_manager = RiskManager()

    def test_initialization(self):
        """Test RiskManager initialization"""
        rm = RiskManager(
            max_portfolio_risk=0.25,
            max_position_size=0.20,
            max_positions=15,
        )
        assert rm.max_portfolio_risk == 0.25
        assert rm.max_position_size == 0.20
        assert rm.max_positions == 15

    def test_calculate_portfolio_risk_empty(self):
        """Test portfolio risk calculation with no positions"""
        positions = []
        portfolio_value = 10000.0

        metrics = self.risk_manager.calculate_portfolio_risk(positions, portfolio_value)

        assert isinstance(metrics, RiskMetrics)
        assert metrics.total_exposure == 0.0
        assert metrics.position_count == 0
        assert metrics.risk_level == RiskLevel.LOW

    def test_calculate_portfolio_risk_single_crypto(self):
        """Test portfolio risk with single crypto position"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=0.5,
                value_usd=21000.0,
                unrealized_pnl=1000.0,
                leverage=1.0,
            )
        ]
        portfolio_value = 50000.0

        metrics = self.risk_manager.calculate_portfolio_risk(positions, portfolio_value)

        assert metrics.total_exposure == 21000.0
        assert metrics.crypto_exposure == 21000.0
        assert metrics.polymarket_exposure == 0.0
        assert metrics.position_count == 1
        assert metrics.diversification_score == 0.0  # Single position = concentrated
        assert metrics.concentration_risk == 0.42  # 21000/50000

    def test_calculate_portfolio_risk_mixed_markets(self):
        """Test portfolio risk with crypto and polymarket positions"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=0.5,
                value_usd=21000.0,
                unrealized_pnl=1000.0,
                leverage=1.0,
            ),
            Position(
                id="pos_2",
                pair="ETH/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=2000.0,
                current_price=2100.0,
                amount=5.0,
                value_usd=10500.0,
                unrealized_pnl=500.0,
                leverage=1.0,
            ),
            Position(
                id="pos_3",
                pair="ELECTION_2024",
                market_type=MarketType.POLYMARKET,
                entry_price=0.50,
                current_price=0.55,
                amount=1000.0,
                value_usd=550.0,
                unrealized_pnl=50.0,
                leverage=1.0,
            ),
        ]
        portfolio_value = 50000.0

        metrics = self.risk_manager.calculate_portfolio_risk(positions, portfolio_value)

        assert metrics.total_exposure == 32050.0
        assert metrics.crypto_exposure == 31500.0
        assert metrics.polymarket_exposure == 550.0
        assert metrics.position_count == 3
        assert metrics.diversification_score > 0.0  # Multiple positions
        assert metrics.var_95 > 0.0

    def test_calculate_portfolio_risk_high_leverage(self):
        """Test portfolio risk with high leverage positions"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=0.5,
                value_usd=21000.0,
                unrealized_pnl=1000.0,
                leverage=5.0,  # High leverage
            ),
        ]
        portfolio_value = 50000.0

        metrics = self.risk_manager.calculate_portfolio_risk(positions, portfolio_value)

        assert metrics.leverage_ratio == 5.0
        # High leverage + concentration can trigger CRITICAL risk level
        assert metrics.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]

    def test_calculate_position_risk_normal(self):
        """Test position risk calculation for normal position"""
        position = Position(
            id="pos_1",
            pair="BTC/USDT",
            market_type=MarketType.CRYPTO,
            entry_price=40000.0,
            current_price=42000.0,
            amount=0.5,
            value_usd=21000.0,
            unrealized_pnl=1000.0,
            leverage=1.0,
            stop_loss=38000.0,
        )
        portfolio_value = 100000.0

        risk = self.risk_manager.calculate_position_risk(position, portfolio_value)

        assert risk["position_id"] == "pos_1"
        assert risk["pair"] == "BTC/USDT"
        assert risk["position_size_pct"] == 21.0
        # Single large position (21%) can be marked as high risk due to concentration
        assert risk["risk_level"] in ["low", "medium", "high"]
        # 21% exceeds max_position_size of 15%
        assert risk["exceeds_max_size"] is True
        assert risk["stop_loss_distance_pct"] is not None

    def test_calculate_position_risk_oversized(self):
        """Test position risk for oversized position"""
        position = Position(
            id="pos_1",
            pair="BTC/USDT",
            market_type=MarketType.CRYPTO,
            entry_price=40000.0,
            current_price=42000.0,
            amount=5.0,
            value_usd=210000.0,  # Large position
            unrealized_pnl=10000.0,
            leverage=1.0,
        )
        portfolio_value = 100000.0

        risk = self.risk_manager.calculate_position_risk(position, portfolio_value)

        assert risk["position_size_pct"] > 100.0
        assert risk["exceeds_max_size"]
        assert risk["risk_level"] == "high"

    def test_evaluate_signal_risk_high_quality(self):
        """Test signal risk evaluation for high quality signal"""
        consensus_metadata = {
            "weighted_confidence": 0.90,
            "agreement_score": 0.85,
            "participating_providers": 4,
            "total_providers": 4,
        }

        risk_eval = self.risk_manager.evaluate_signal_risk(consensus_metadata)

        assert risk_eval["risk_level"] == "low"
        assert risk_eval["signal_strength"] >= 0.8
        assert risk_eval["provider_diversity"] == 1.0
        assert risk_eval["should_trade"] is True
        assert len(risk_eval["warnings"]) == 0

    def test_evaluate_signal_risk_low_quality(self):
        """Test signal risk evaluation for low quality signal"""
        consensus_metadata = {
            "weighted_confidence": 0.40,
            "agreement_score": 0.35,
            "participating_providers": 1,
            "total_providers": 4,
        }

        risk_eval = self.risk_manager.evaluate_signal_risk(consensus_metadata)

        assert risk_eval["risk_level"] in ["medium", "high"]
        assert risk_eval["signal_strength"] < 0.5
        assert risk_eval["provider_diversity"] < 0.5
        assert len(risk_eval["warnings"]) > 0

    def test_evaluate_signal_risk_with_volatility(self):
        """Test signal risk with high market volatility"""
        consensus_metadata = {
            "weighted_confidence": 0.75,
            "agreement_score": 0.70,
            "participating_providers": 3,
            "total_providers": 4,
        }
        market_conditions = {
            "volatility": 0.25,  # High volatility
        }

        risk_eval = self.risk_manager.evaluate_signal_risk(
            consensus_metadata, market_conditions
        )

        # High volatility should reduce recommended position size
        assert risk_eval["recommended_position_size_pct"] < 15.0

    def test_check_position_limits_approved(self):
        """Test position limit check for valid new position"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=0.5,
                value_usd=21000.0,
                unrealized_pnl=1000.0,
                leverage=1.0,
            ),
        ]
        new_position_value = 5000.0
        new_position_type = MarketType.CRYPTO
        portfolio_value = 100000.0

        result = self.risk_manager.check_position_limits(
            positions, new_position_value, new_position_type, portfolio_value
        )

        assert result["approved"] is True
        assert len(result["violations"]) == 0

    def test_check_position_limits_too_large(self):
        """Test position limit check for oversized position"""
        positions = []
        new_position_value = 20000.0  # 20% of portfolio
        new_position_type = MarketType.CRYPTO
        portfolio_value = 100000.0

        result = self.risk_manager.check_position_limits(
            positions, new_position_value, new_position_type, portfolio_value
        )

        assert result["approved"] is False
        assert len(result["violations"]) > 0
        assert any("Position size too large" in v for v in result["violations"])

    def test_check_position_limits_max_positions(self):
        """Test position limit check when max positions reached"""
        # Create 10 positions (default max)
        positions = [
            Position(
                id=f"pos_{i}",
                pair=f"PAIR_{i}/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=1000.0,
                current_price=1100.0,
                amount=1.0,
                value_usd=1100.0,
                unrealized_pnl=100.0,
                leverage=1.0,
            )
            for i in range(10)
        ]
        new_position_value = 1000.0
        new_position_type = MarketType.CRYPTO
        portfolio_value = 100000.0

        result = self.risk_manager.check_position_limits(
            positions, new_position_value, new_position_type, portfolio_value
        )

        assert result["approved"] is False
        assert any("Maximum positions reached" in v for v in result["violations"])

    def test_check_position_limits_crypto_exposure(self):
        """Test position limit check for crypto exposure limit"""
        # Create positions with 65% crypto exposure
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=1.0,
                value_usd=42000.0,
                unrealized_pnl=2000.0,
                leverage=1.0,
            ),
            Position(
                id="pos_2",
                pair="ETH/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=2000.0,
                current_price=2100.0,
                amount=10.0,
                value_usd=21000.0,
                unrealized_pnl=1000.0,
                leverage=1.0,
            ),
        ]
        # Adding another 10% would exceed 70% limit
        new_position_value = 10000.0
        new_position_type = MarketType.CRYPTO
        portfolio_value = 100000.0

        result = self.risk_manager.check_position_limits(
            positions, new_position_value, new_position_type, portfolio_value
        )

        assert result["approved"] is False
        assert any("Crypto exposure too high" in v for v in result["violations"])

    def test_calculate_stop_loss_long_crypto(self):
        """Test stop loss calculation for long crypto position"""
        result = self.risk_manager.calculate_stop_loss(
            entry_price=50000.0,
            position_type="LONG",
            volatility=0.10,
            market_type=MarketType.CRYPTO,
            risk_per_trade=0.02,
        )

        assert "stop_loss" in result
        assert "take_profit" in result
        assert result["stop_loss"] < 50000.0  # Below entry for long
        assert result["take_profit"] > 50000.0  # Above entry for long
        assert result["risk_reward_ratio"] > 1.0

    def test_calculate_stop_loss_short_crypto(self):
        """Test stop loss calculation for short crypto position"""
        result = self.risk_manager.calculate_stop_loss(
            entry_price=50000.0,
            position_type="SHORT",
            volatility=0.10,
            market_type=MarketType.CRYPTO,
            risk_per_trade=0.02,
        )

        assert result["stop_loss"] > 50000.0  # Above entry for short
        assert result["take_profit"] < 50000.0  # Below entry for short

    def test_calculate_stop_loss_polymarket(self):
        """Test stop loss calculation for polymarket position"""
        result = self.risk_manager.calculate_stop_loss(
            entry_price=0.60,
            position_type="LONG",
            volatility=0.05,
            market_type=MarketType.POLYMARKET,
            risk_per_trade=0.02,
        )

        assert result["stop_loss"] < 0.60
        assert result["take_profit"] > 0.60
        # Polymarket should have tighter stops than crypto
        assert result["stop_distance_pct"] < 5.0

    def test_calculate_stop_loss_high_volatility(self):
        """Test stop loss with high volatility"""
        result = self.risk_manager.calculate_stop_loss(
            entry_price=50000.0,
            position_type="LONG",
            volatility=0.30,  # High volatility
            market_type=MarketType.CRYPTO,
            risk_per_trade=0.02,
        )

        # Higher volatility should mean wider stops
        assert result["stop_distance_pct"] > 4.0  # Adjusted threshold

    def test_diversification_score_single_position(self):
        """Test diversification with single position (concentrated)"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=0.5,
                value_usd=21000.0,
                unrealized_pnl=1000.0,
                leverage=1.0,
            ),
        ]
        portfolio_value = 50000.0

        score = self.risk_manager._calculate_diversification(positions, portfolio_value)

        assert score == 0.0  # Single position = no diversification

    def test_diversification_score_multiple_equal_positions(self):
        """Test diversification with multiple equal positions"""
        positions = [
            Position(
                id=f"pos_{i}",
                pair=f"PAIR_{i}/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=1000.0,
                current_price=1100.0,
                amount=1.0,
                value_usd=1100.0,
                unrealized_pnl=100.0,
                leverage=1.0,
            )
            for i in range(5)
        ]
        portfolio_value = 10000.0

        score = self.risk_manager._calculate_diversification(positions, portfolio_value)

        # Equal positions should have good diversification
        assert score > 0.7

    def test_var_calculation(self):
        """Test Value at Risk calculation"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=0.5,
                value_usd=21000.0,
                unrealized_pnl=1000.0,
                leverage=1.0,
            ),
        ]
        portfolio_value = 50000.0

        var = self.risk_manager._calculate_var(positions, portfolio_value)

        assert var > 0.0
        assert var <= portfolio_value  # VaR shouldn't exceed portfolio

    def test_max_drawdown_calculation(self):
        """Test max drawdown calculation"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=38000.0,
                amount=0.5,
                value_usd=19000.0,
                unrealized_pnl=-1000.0,  # Negative PnL
                leverage=1.0,
            ),
        ]
        portfolio_value = 50000.0

        drawdown = self.risk_manager._calculate_max_drawdown(positions, portfolio_value)

        assert drawdown > 0.0
        assert drawdown <= 1.0  # Drawdown is a ratio

    def test_correlation_risk_crypto_heavy(self):
        """Test correlation risk with many crypto positions"""
        positions = [
            Position(
                id=f"pos_{i}",
                pair=f"CRYPTO_{i}/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=1000.0,
                current_price=1100.0,
                amount=1.0,
                value_usd=1100.0,
                unrealized_pnl=100.0,
                leverage=1.0,
            )
            for i in range(5)
        ]
        portfolio_value = 10000.0

        correlation_risk = self.risk_manager._calculate_correlation_risk(positions)

        # All crypto positions = high correlation
        assert correlation_risk > 0.5

    def test_leverage_ratio_calculation(self):
        """Test average leverage ratio calculation"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=0.5,
                value_usd=21000.0,
                unrealized_pnl=1000.0,
                leverage=2.0,
            ),
            Position(
                id="pos_2",
                pair="ETH/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=2000.0,
                current_price=2100.0,
                amount=5.0,
                value_usd=10500.0,
                unrealized_pnl=500.0,
                leverage=1.0,
            ),
        ]
        portfolio_value = 50000.0

        leverage = self.risk_manager._calculate_leverage_ratio(positions, portfolio_value)

        # Weighted average should be between 1.0 and 2.0
        assert 1.0 < leverage < 2.0

    def test_concentration_risk_calculation(self):
        """Test concentration risk (largest position)"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=1.0,
                value_usd=42000.0,  # Large position
                unrealized_pnl=2000.0,
                leverage=1.0,
            ),
            Position(
                id="pos_2",
                pair="ETH/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=2000.0,
                current_price=2100.0,
                amount=1.0,
                value_usd=2100.0,  # Small position
                unrealized_pnl=100.0,
                leverage=1.0,
            ),
        ]
        portfolio_value = 100000.0

        concentration = self.risk_manager._calculate_concentration_risk(
            positions, portfolio_value
        )

        # Largest position is 42% of portfolio
        assert concentration >= 0.42

    def test_risk_level_determination_low(self):
        """Test risk level determination for low risk portfolio"""
        risk_level = self.risk_manager._determine_risk_level(
            exposure_ratio=0.50,
            diversification=0.80,
            var_ratio=0.05,
            max_drawdown=0.05,
            correlation_risk=0.30,
            leverage_ratio=1.0,
            concentration_risk=0.15,
        )

        assert risk_level == RiskLevel.LOW

    def test_risk_level_determination_high(self):
        """Test risk level determination for high risk portfolio"""
        risk_level = self.risk_manager._determine_risk_level(
            exposure_ratio=0.95,
            diversification=0.20,
            var_ratio=0.25,
            max_drawdown=0.30,
            correlation_risk=0.80,
            leverage_ratio=4.0,
            concentration_risk=0.40,
        )

        assert risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def test_invalid_portfolio_value(self):
        """Test handling of invalid portfolio value"""
        positions = [
            Position(
                id="pos_1",
                pair="BTC/USDT",
                market_type=MarketType.CRYPTO,
                entry_price=40000.0,
                current_price=42000.0,
                amount=0.5,
                value_usd=21000.0,
                unrealized_pnl=1000.0,
                leverage=1.0,
            ),
        ]

        # Zero portfolio value
        metrics = self.risk_manager.calculate_portfolio_risk(positions, 0.0)
        assert metrics.risk_level == RiskLevel.LOW

        # Negative portfolio value
        metrics = self.risk_manager.calculate_portfolio_risk(positions, -1000.0)
        assert metrics.risk_level == RiskLevel.LOW
