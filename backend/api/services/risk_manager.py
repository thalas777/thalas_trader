"""
Risk Management Module for Thalas Trader
Handles portfolio-wide risk calculations for crypto and prediction market positions
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import math
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MarketType(Enum):
    """Market type classification"""
    CRYPTO = "crypto"
    POLYMARKET = "polymarket"


@dataclass
class Position:
    """Position data structure"""
    id: str
    pair: str
    market_type: MarketType
    entry_price: float
    current_price: float
    amount: float
    value_usd: float
    unrealized_pnl: float
    leverage: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    total_exposure: float
    crypto_exposure: float
    polymarket_exposure: float
    diversification_score: float
    var_95: float
    position_count: int
    max_drawdown: float
    risk_level: RiskLevel
    correlation_risk: float
    leverage_ratio: float
    concentration_risk: float


class RiskManager:
    """
    Enhanced risk management system that handles both crypto and prediction market positions

    Features:
    - Portfolio-wide risk calculation
    - Position limits enforcement
    - Correlation analysis
    - Stop-loss recommendations
    - Signal risk scoring
    """

    def __init__(
        self,
        max_portfolio_risk: float = 0.20,  # 20% max portfolio risk
        max_position_size: float = 0.15,   # 15% max per position
        max_positions: int = 10,            # Max concurrent positions
        max_crypto_exposure: float = 0.70,  # 70% max crypto
        max_polymarket_exposure: float = 0.50,  # 50% max polymarket
        var_confidence: float = 0.95,       # 95% VaR confidence
    ):
        """Initialize risk manager with configurable limits"""
        self.max_portfolio_risk = max_portfolio_risk
        self.max_position_size = max_position_size
        self.max_positions = max_positions
        self.max_crypto_exposure = max_crypto_exposure
        self.max_polymarket_exposure = max_polymarket_exposure
        self.var_confidence = var_confidence

        logger.info(
            f"RiskManager initialized: max_portfolio_risk={max_portfolio_risk}, "
            f"max_position_size={max_position_size}, max_positions={max_positions}"
        )

    def calculate_portfolio_risk(
        self,
        positions: List[Position],
        portfolio_value: float
    ) -> RiskMetrics:
        """
        Calculate comprehensive portfolio risk metrics

        Args:
            positions: List of current positions
            portfolio_value: Total portfolio value in USD

        Returns:
            RiskMetrics with all calculated risk indicators
        """
        if portfolio_value <= 0:
            logger.warning("Invalid portfolio value, returning default metrics")
            return self._get_default_metrics()

        # Calculate exposures
        crypto_exposure = sum(
            p.value_usd for p in positions if p.market_type == MarketType.CRYPTO
        )
        polymarket_exposure = sum(
            p.value_usd for p in positions if p.market_type == MarketType.POLYMARKET
        )
        total_exposure = crypto_exposure + polymarket_exposure

        # Calculate diversification score (0-1, higher is better)
        diversification_score = self._calculate_diversification(positions, portfolio_value)

        # Calculate Value at Risk (VaR)
        var_95 = self._calculate_var(positions, portfolio_value)

        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown(positions, portfolio_value)

        # Calculate correlation risk
        correlation_risk = self._calculate_correlation_risk(positions)

        # Calculate leverage ratio
        leverage_ratio = self._calculate_leverage_ratio(positions, portfolio_value)

        # Calculate concentration risk
        concentration_risk = self._calculate_concentration_risk(positions, portfolio_value)

        # Determine overall risk level
        risk_level = self._determine_risk_level(
            total_exposure / portfolio_value if portfolio_value > 0 else 0,
            diversification_score,
            var_95 / portfolio_value if portfolio_value > 0 else 0,
            max_drawdown,
            correlation_risk,
            leverage_ratio,
            concentration_risk,
        )

        metrics = RiskMetrics(
            total_exposure=total_exposure,
            crypto_exposure=crypto_exposure,
            polymarket_exposure=polymarket_exposure,
            diversification_score=diversification_score,
            var_95=var_95,
            position_count=len(positions),
            max_drawdown=max_drawdown,
            risk_level=risk_level,
            correlation_risk=correlation_risk,
            leverage_ratio=leverage_ratio,
            concentration_risk=concentration_risk,
        )

        logger.info(
            f"Portfolio risk calculated: exposure={total_exposure:.2f}, "
            f"VaR={var_95:.2f}, risk_level={risk_level.value}"
        )

        return metrics

    def calculate_position_risk(
        self,
        position: Position,
        portfolio_value: float
    ) -> Dict[str, Any]:
        """
        Calculate risk metrics for a single position

        Args:
            position: Position to analyze
            portfolio_value: Total portfolio value

        Returns:
            Dictionary with position risk metrics
        """
        position_size_pct = (position.value_usd / portfolio_value * 100) if portfolio_value > 0 else 0

        # Calculate position volatility (simplified)
        volatility = abs(position.unrealized_pnl / position.value_usd) if position.value_usd > 0 else 0

        # Calculate distance to stop loss
        stop_loss_distance = None
        if position.stop_loss:
            stop_loss_distance = abs(position.current_price - position.stop_loss) / position.current_price

        # Calculate potential loss
        potential_loss = position.value_usd * volatility

        # Determine position risk level
        if position_size_pct > self.max_position_size * 100:
            risk_level = RiskLevel.HIGH
        elif volatility > 0.15:
            risk_level = RiskLevel.MEDIUM
        elif position.leverage > 2.0:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return {
            "position_id": position.id,
            "pair": position.pair,
            "market_type": position.market_type.value,
            "position_size_pct": round(position_size_pct, 2),
            "volatility": round(volatility, 4),
            "potential_loss_usd": round(potential_loss, 2),
            "stop_loss_distance_pct": round(stop_loss_distance * 100, 2) if stop_loss_distance else None,
            "leverage": position.leverage,
            "risk_level": risk_level.value,
            "exceeds_max_size": position_size_pct > self.max_position_size * 100,
            "recommended_stop_loss": self._calculate_recommended_stop_loss(position),
        }

    def evaluate_signal_risk(
        self,
        consensus_metadata: Dict[str, Any],
        market_conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate risk of an LLM trading signal

        Args:
            consensus_metadata: Metadata from consensus signal
            market_conditions: Optional market conditions data

        Returns:
            Risk evaluation with score and recommendations
        """
        # Extract key metrics
        confidence = consensus_metadata.get("weighted_confidence", 0.5)
        agreement_score = consensus_metadata.get("agreement_score", 0.5)
        participating_providers = consensus_metadata.get("participating_providers", 0)
        total_providers = consensus_metadata.get("total_providers", 4)

        # Calculate provider diversity score (0-1)
        provider_diversity = participating_providers / max(total_providers, 1)

        # Calculate signal strength (0-1)
        signal_strength = (confidence + agreement_score) / 2

        # Determine risk level based on multiple factors
        if signal_strength >= 0.8 and provider_diversity >= 0.75 and agreement_score >= 0.8:
            risk_level = RiskLevel.LOW
            recommended_position_size = self.max_position_size
        elif signal_strength >= 0.6 and provider_diversity >= 0.5:
            risk_level = RiskLevel.MEDIUM
            recommended_position_size = self.max_position_size * 0.7
        elif signal_strength >= 0.4:
            risk_level = RiskLevel.MEDIUM
            recommended_position_size = self.max_position_size * 0.5
        else:
            risk_level = RiskLevel.HIGH
            recommended_position_size = self.max_position_size * 0.3

        # Add market condition adjustments if provided
        volatility_adjustment = 1.0
        if market_conditions:
            volatility = market_conditions.get("volatility", 0)
            if volatility > 0.20:  # High volatility
                risk_level = RiskLevel.HIGH if risk_level == RiskLevel.MEDIUM else risk_level
                volatility_adjustment = 0.7
            elif volatility > 0.10:  # Moderate volatility
                volatility_adjustment = 0.85

        return {
            "risk_level": risk_level.value,
            "signal_strength": round(signal_strength, 3),
            "provider_diversity": round(provider_diversity, 3),
            "confidence": round(confidence, 3),
            "agreement_score": round(agreement_score, 3),
            "recommended_position_size_pct": round(recommended_position_size * volatility_adjustment * 100, 2),
            "should_trade": risk_level != RiskLevel.CRITICAL and signal_strength >= 0.3,
            "warnings": self._generate_signal_warnings(
                risk_level, signal_strength, provider_diversity, agreement_score
            ),
        }

    def check_position_limits(
        self,
        positions: List[Position],
        new_position_value: float,
        new_position_type: MarketType,
        portfolio_value: float
    ) -> Dict[str, Any]:
        """
        Check if adding a new position would violate limits

        Args:
            positions: Current positions
            new_position_value: Value of proposed new position
            new_position_type: Type of new position (crypto/polymarket)
            portfolio_value: Total portfolio value

        Returns:
            Dictionary with approval status and reasons
        """
        checks = {
            "approved": True,
            "violations": [],
            "warnings": [],
        }

        # Check max positions
        if len(positions) >= self.max_positions:
            checks["approved"] = False
            checks["violations"].append(
                f"Maximum positions reached ({len(positions)}/{self.max_positions})"
            )

        # Check position size
        position_size_pct = new_position_value / portfolio_value if portfolio_value > 0 else 0
        if position_size_pct > self.max_position_size:
            checks["approved"] = False
            checks["violations"].append(
                f"Position size too large ({position_size_pct:.1%} > {self.max_position_size:.1%})"
            )

        # Check market type exposure
        current_crypto = sum(p.value_usd for p in positions if p.market_type == MarketType.CRYPTO)
        current_polymarket = sum(p.value_usd for p in positions if p.market_type == MarketType.POLYMARKET)

        if new_position_type == MarketType.CRYPTO:
            new_crypto_exposure = (current_crypto + new_position_value) / portfolio_value if portfolio_value > 0 else 0
            if new_crypto_exposure > self.max_crypto_exposure:
                checks["approved"] = False
                checks["violations"].append(
                    f"Crypto exposure too high ({new_crypto_exposure:.1%} > {self.max_crypto_exposure:.1%})"
                )
        else:
            new_polymarket_exposure = (current_polymarket + new_position_value) / portfolio_value if portfolio_value > 0 else 0
            if new_polymarket_exposure > self.max_polymarket_exposure:
                checks["approved"] = False
                checks["violations"].append(
                    f"Polymarket exposure too high ({new_polymarket_exposure:.1%} > {self.max_polymarket_exposure:.1%})"
                )

        # Warnings (don't block but inform)
        if position_size_pct > self.max_position_size * 0.8:
            checks["warnings"].append(
                f"Position size near limit ({position_size_pct:.1%})"
            )

        if len(positions) >= self.max_positions * 0.8:
            checks["warnings"].append(
                f"Approaching max positions ({len(positions)}/{self.max_positions})"
            )

        return checks

    def calculate_stop_loss(
        self,
        entry_price: float,
        position_type: str,  # "LONG" or "SHORT"
        volatility: float,
        market_type: MarketType,
        risk_per_trade: float = 0.02  # 2% risk per trade default
    ) -> Dict[str, float]:
        """
        Calculate recommended stop-loss and take-profit levels

        Args:
            entry_price: Entry price for position
            position_type: LONG or SHORT
            volatility: Market volatility (0-1)
            market_type: Type of market
            risk_per_trade: Risk percentage per trade

        Returns:
            Dictionary with stop_loss and take_profit levels
        """
        # Base multipliers
        if market_type == MarketType.CRYPTO:
            # Crypto typically needs wider stops due to volatility
            base_stop_multiplier = 1.5
            base_take_multiplier = 3.0
        else:
            # Prediction markets have binary outcomes, tighter stops
            base_stop_multiplier = 1.0
            base_take_multiplier = 2.0

        # Adjust for volatility
        volatility_factor = 1.0 + (volatility * 2)  # Scale volatility impact
        stop_distance = risk_per_trade * volatility_factor * base_stop_multiplier
        take_distance = stop_distance * base_take_multiplier  # Risk:Reward typically 1:2 or 1:3

        if position_type.upper() == "LONG":
            stop_loss = entry_price * (1 - stop_distance)
            take_profit = entry_price * (1 + take_distance)
        else:  # SHORT
            stop_loss = entry_price * (1 + stop_distance)
            take_profit = entry_price * (1 - take_distance)

        return {
            "stop_loss": round(stop_loss, 8),
            "take_profit": round(take_profit, 8),
            "stop_distance_pct": round(stop_distance * 100, 2),
            "take_distance_pct": round(take_distance * 100, 2),
            "risk_reward_ratio": round(take_distance / stop_distance, 2),
        }

    # Private helper methods

    def _calculate_diversification(self, positions: List[Position], portfolio_value: float) -> float:
        """
        Calculate portfolio diversification score using Herfindahl-Hirschman Index
        Returns value between 0 (concentrated) and 1 (diversified)
        """
        if not positions or portfolio_value <= 0:
            return 0.0

        # Single position = no diversification
        if len(positions) == 1:
            return 0.0

        # Calculate position weights
        weights = [p.value_usd / portfolio_value for p in positions]

        # Calculate HHI (sum of squared weights)
        hhi = sum(w * w for w in weights)

        # Normalize to 0-1 scale (1/n is perfect diversification)
        n = len(positions)
        min_hhi = 1.0 / n if n > 0 else 1.0
        max_hhi = 1.0

        # Invert so higher score = more diversified
        if max_hhi > min_hhi:
            diversification = 1.0 - ((hhi - min_hhi) / (max_hhi - min_hhi))
        else:
            diversification = 0.0

        return round(max(0.0, min(1.0, diversification)), 3)

    def _calculate_var(self, positions: List[Position], portfolio_value: float) -> float:
        """
        Calculate Value at Risk (VaR) at specified confidence level
        Uses simplified variance-covariance method
        """
        if not positions or portfolio_value <= 0:
            return 0.0

        # Estimate portfolio volatility from position PnL
        total_unrealized_pnl = sum(abs(p.unrealized_pnl) for p in positions)
        estimated_volatility = total_unrealized_pnl / portfolio_value if portfolio_value > 0 else 0.10

        # Cap volatility at reasonable levels
        estimated_volatility = min(estimated_volatility, 0.50)

        # Z-score for 95% confidence = 1.645
        z_score = 1.645 if self.var_confidence == 0.95 else 1.96

        # VaR = Portfolio Value * Volatility * Z-score
        var = portfolio_value * estimated_volatility * z_score

        return round(var, 2)

    def _calculate_max_drawdown(self, positions: List[Position], portfolio_value: float) -> float:
        """
        Calculate maximum drawdown from unrealized losses
        """
        if not positions or portfolio_value <= 0:
            return 0.0

        # Sum all negative unrealized PnL
        total_losses = sum(p.unrealized_pnl for p in positions if p.unrealized_pnl < 0)

        # Calculate as percentage of portfolio
        max_drawdown = abs(total_losses) / portfolio_value if portfolio_value > 0 else 0.0

        return round(max(0.0, min(1.0, max_drawdown)), 4)

    def _calculate_correlation_risk(self, positions: List[Position]) -> float:
        """
        Estimate correlation risk (simplified)
        Higher correlation = higher risk
        """
        if len(positions) <= 1:
            return 0.0

        # Simplified: assume crypto positions are correlated
        crypto_positions = [p for p in positions if p.market_type == MarketType.CRYPTO]

        if len(crypto_positions) <= 1:
            return 0.0

        # Correlation risk increases with number of correlated positions
        # and their proportion of portfolio
        total_value = sum(p.value_usd for p in positions)
        crypto_value = sum(p.value_usd for p in crypto_positions)

        crypto_concentration = crypto_value / total_value if total_value > 0 else 0

        # Risk is high if many correlated positions make up large portion
        correlation_risk = crypto_concentration * (len(crypto_positions) / len(positions))

        return round(correlation_risk, 3)

    def _calculate_leverage_ratio(self, positions: List[Position], portfolio_value: float) -> float:
        """Calculate average leverage across all positions"""
        if not positions:
            return 1.0

        weighted_leverage = sum(p.leverage * p.value_usd for p in positions)
        total_value = sum(p.value_usd for p in positions)

        avg_leverage = weighted_leverage / total_value if total_value > 0 else 1.0

        return round(avg_leverage, 2)

    def _calculate_concentration_risk(self, positions: List[Position], portfolio_value: float) -> float:
        """
        Calculate concentration risk (largest position as % of portfolio)
        """
        if not positions or portfolio_value <= 0:
            return 0.0

        largest_position = max(p.value_usd for p in positions)
        concentration = largest_position / portfolio_value

        return round(concentration, 3)

    def _determine_risk_level(
        self,
        exposure_ratio: float,
        diversification: float,
        var_ratio: float,
        max_drawdown: float,
        correlation_risk: float,
        leverage_ratio: float,
        concentration_risk: float,
    ) -> RiskLevel:
        """Determine overall portfolio risk level based on multiple factors"""

        # Empty portfolio = LOW risk
        if exposure_ratio == 0.0:
            return RiskLevel.LOW

        # Count risk factors
        high_risk_factors = 0
        medium_risk_factors = 0

        # Exposure checks
        if exposure_ratio > 0.90:
            high_risk_factors += 1
        elif exposure_ratio > 0.75:
            medium_risk_factors += 1

        # Diversification checks (inverted - low diversification = high risk)
        # Only check if there are positions (diversification > 0 or concentration_risk > 0)
        if concentration_risk > 0 or diversification > 0:
            if diversification < 0.30 and concentration_risk > 0.30:
                high_risk_factors += 1
            elif diversification < 0.50 and concentration_risk > 0.20:
                medium_risk_factors += 1

        # VaR checks
        if var_ratio > 0.20:
            high_risk_factors += 1
        elif var_ratio > 0.10:
            medium_risk_factors += 1

        # Drawdown checks
        if max_drawdown > 0.25:
            high_risk_factors += 1
        elif max_drawdown > 0.15:
            medium_risk_factors += 1

        # Correlation risk
        if correlation_risk > 0.75:
            medium_risk_factors += 1

        # Leverage checks
        if leverage_ratio > 3.0:
            high_risk_factors += 1
        elif leverage_ratio > 2.0:
            medium_risk_factors += 1

        # Concentration risk
        if concentration_risk > 0.30:
            high_risk_factors += 1
        elif concentration_risk > 0.20:
            medium_risk_factors += 1

        # Determine level
        if high_risk_factors >= 3:
            return RiskLevel.CRITICAL
        elif high_risk_factors >= 1:
            return RiskLevel.HIGH
        elif medium_risk_factors >= 3:
            return RiskLevel.HIGH
        elif medium_risk_factors >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _calculate_recommended_stop_loss(self, position: Position) -> Optional[float]:
        """Calculate recommended stop loss for a position"""
        if position.stop_loss:
            return position.stop_loss

        # Estimate volatility from unrealized PnL
        volatility = abs(position.unrealized_pnl / position.value_usd) if position.value_usd > 0 else 0.10

        # Calculate stop loss
        stop_calc = self.calculate_stop_loss(
            entry_price=position.entry_price,
            position_type="LONG" if position.current_price >= position.entry_price else "SHORT",
            volatility=volatility,
            market_type=position.market_type,
        )

        return stop_calc["stop_loss"]

    def _generate_signal_warnings(
        self,
        risk_level: RiskLevel,
        signal_strength: float,
        provider_diversity: float,
        agreement_score: float
    ) -> List[str]:
        """Generate warnings for signal risk"""
        warnings = []

        if risk_level == RiskLevel.CRITICAL:
            warnings.append("CRITICAL: Signal quality insufficient for trading")
        elif risk_level == RiskLevel.HIGH:
            warnings.append("HIGH RISK: Consider reducing position size or waiting")

        if signal_strength < 0.5:
            warnings.append("Low signal strength - weak consensus")

        if provider_diversity < 0.5:
            warnings.append("Low provider diversity - fewer opinions")

        if agreement_score < 0.6:
            warnings.append("Low agreement - providers disagree")

        return warnings

    def _get_default_metrics(self) -> RiskMetrics:
        """Return default/empty risk metrics"""
        return RiskMetrics(
            total_exposure=0.0,
            crypto_exposure=0.0,
            polymarket_exposure=0.0,
            diversification_score=0.0,
            var_95=0.0,
            position_count=0,
            max_drawdown=0.0,
            risk_level=RiskLevel.LOW,
            correlation_risk=0.0,
            leverage_ratio=1.0,
            concentration_risk=0.0,
        )
