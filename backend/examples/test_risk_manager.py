#!/usr/bin/env python
"""
Example script demonstrating the Risk Management system
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.risk_manager import (
    RiskManager,
    Position,
    MarketType,
    RiskLevel,
)


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def main():
    print("\n" + "+" * 70)
    print("  THALAS TRADER - RISK MANAGEMENT SYSTEM DEMO")
    print("+" * 70)

    # Initialize risk manager
    risk_manager = RiskManager(
        max_portfolio_risk=0.20,
        max_position_size=0.15,
        max_positions=10,
    )

    print_section("1. Portfolio Risk Analysis")

    # Create sample positions
    positions = [
        Position(
            id="pos_1",
            pair="BTC/USDT",
            market_type=MarketType.CRYPTO,
            entry_price=42000.0,
            current_price=43500.0,
            amount=0.5,
            value_usd=21750.0,
            unrealized_pnl=750.0,
            leverage=2.0,
            stop_loss=40000.0,
        ),
        Position(
            id="pos_2",
            pair="ETH/USDT",
            market_type=MarketType.CRYPTO,
            entry_price=2200.0,
            current_price=2350.0,
            amount=5.0,
            value_usd=11750.0,
            unrealized_pnl=750.0,
            leverage=1.0,
        ),
        Position(
            id="pos_3",
            pair="ELECTION_2024",
            market_type=MarketType.POLYMARKET,
            entry_price=0.48,
            current_price=0.62,
            amount=2000.0,
            value_usd=1240.0,
            unrealized_pnl=280.0,
            leverage=1.0,
        ),
    ]

    portfolio_value = 50000.0

    # Calculate portfolio risk
    metrics = risk_manager.calculate_portfolio_risk(positions, portfolio_value)

    print(f"Portfolio Value: ${portfolio_value:,.2f}")
    print(f"Total Exposure: ${metrics.total_exposure:,.2f} ({metrics.total_exposure/portfolio_value*100:.1f}%)")
    print(f"  - Crypto: ${metrics.crypto_exposure:,.2f}")
    print(f"  - Polymarket: ${metrics.polymarket_exposure:,.2f}")
    print(f"\nRisk Metrics:")
    print(f"  - Risk Level: {metrics.risk_level.value.upper()}")
    print(f"  - Diversification Score: {metrics.diversification_score:.3f} (0=concentrated, 1=diversified)")
    print(f"  - Value at Risk (95%): ${metrics.var_95:,.2f}")
    print(f"  - Max Drawdown: {metrics.max_drawdown:.1%}")
    print(f"  - Position Count: {metrics.position_count}")
    print(f"  - Concentration Risk: {metrics.concentration_risk:.3f}")
    print(f"  - Correlation Risk: {metrics.correlation_risk:.3f}")
    print(f"  - Average Leverage: {metrics.leverage_ratio:.2f}x")

    print_section("2. Individual Position Risk")

    for position in positions:
        risk = risk_manager.calculate_position_risk(position, portfolio_value)
        print(f"\n{position.pair} ({position.market_type.value}):")
        print(f"  - Position Size: {risk['position_size_pct']:.2f}% of portfolio")
        print(f"  - Risk Level: {risk['risk_level'].upper()}")
        print(f"  - Volatility: {risk['volatility']:.4f}")
        print(f"  - Potential Loss: ${risk['potential_loss_usd']:,.2f}")
        print(f"  - Leverage: {risk['leverage']:.1f}x")
        if risk['stop_loss_distance_pct']:
            print(f"  - Stop Loss Distance: {risk['stop_loss_distance_pct']:.2f}%")
        if risk['exceeds_max_size']:
            print(f"  - WARNING: Exceeds maximum position size!")

    print_section("3. LLM Signal Risk Evaluation")

    # High quality signal
    high_quality_signal = {
        "weighted_confidence": 0.88,
        "agreement_score": 0.82,
        "participating_providers": 4,
        "total_providers": 4,
    }

    risk_eval = risk_manager.evaluate_signal_risk(high_quality_signal)
    print("High Quality Signal:")
    print(f"  - Risk Level: {risk_eval['risk_level'].upper()}")
    print(f"  - Signal Strength: {risk_eval['signal_strength']:.3f}")
    print(f"  - Provider Diversity: {risk_eval['provider_diversity']:.3f}")
    print(f"  - Recommended Position Size: {risk_eval['recommended_position_size_pct']:.2f}%")
    print(f"  - Should Trade: {risk_eval['should_trade']}")
    if risk_eval['warnings']:
        print(f"  - Warnings: {', '.join(risk_eval['warnings'])}")

    # Low quality signal
    low_quality_signal = {
        "weighted_confidence": 0.45,
        "agreement_score": 0.38,
        "participating_providers": 2,
        "total_providers": 4,
    }

    risk_eval = risk_manager.evaluate_signal_risk(low_quality_signal)
    print("\nLow Quality Signal:")
    print(f"  - Risk Level: {risk_eval['risk_level'].upper()}")
    print(f"  - Signal Strength: {risk_eval['signal_strength']:.3f}")
    print(f"  - Provider Diversity: {risk_eval['provider_diversity']:.3f}")
    print(f"  - Recommended Position Size: {risk_eval['recommended_position_size_pct']:.2f}%")
    print(f"  - Should Trade: {risk_eval['should_trade']}")
    if risk_eval['warnings']:
        print(f"  - Warnings:")
        for warning in risk_eval['warnings']:
            print(f"    * {warning}")

    print_section("4. Position Limit Check")

    # Check if a new position would violate limits
    new_position_value = 8000.0
    new_position_type = MarketType.CRYPTO

    limit_check = risk_manager.check_position_limits(
        positions, new_position_value, new_position_type, portfolio_value
    )

    print(f"Checking new {new_position_type.value} position worth ${new_position_value:,.2f}:")
    print(f"  - Approved: {limit_check['approved']}")
    if limit_check['violations']:
        print(f"  - Violations:")
        for violation in limit_check['violations']:
            print(f"    * {violation}")
    if limit_check['warnings']:
        print(f"  - Warnings:")
        for warning in limit_check['warnings']:
            print(f"    * {warning}")

    print_section("5. Stop-Loss Calculation")

    # Calculate stop-loss for long crypto position
    entry_price = 45000.0
    volatility = 0.12

    stop_loss_calc = risk_manager.calculate_stop_loss(
        entry_price=entry_price,
        position_type="LONG",
        volatility=volatility,
        market_type=MarketType.CRYPTO,
        risk_per_trade=0.02,
    )

    print(f"BTC/USDT LONG position at ${entry_price:,.2f} (volatility: {volatility:.1%}):")
    print(f"  - Stop Loss: ${stop_loss_calc['stop_loss']:,.2f} (-{stop_loss_calc['stop_distance_pct']:.2f}%)")
    print(f"  - Take Profit: ${stop_loss_calc['take_profit']:,.2f} (+{stop_loss_calc['take_distance_pct']:.2f}%)")
    print(f"  - Risk:Reward Ratio: 1:{stop_loss_calc['risk_reward_ratio']:.2f}")

    # Calculate stop-loss for polymarket position
    stop_loss_calc = risk_manager.calculate_stop_loss(
        entry_price=0.55,
        position_type="LONG",
        volatility=0.08,
        market_type=MarketType.POLYMARKET,
        risk_per_trade=0.02,
    )

    print(f"\nPolymarket position at $0.55 (volatility: 8%):")
    print(f"  - Stop Loss: ${stop_loss_calc['stop_loss']:.4f} (-{stop_loss_calc['stop_distance_pct']:.2f}%)")
    print(f"  - Take Profit: ${stop_loss_calc['take_profit']:.4f} (+{stop_loss_calc['take_distance_pct']:.2f}%)")
    print(f"  - Risk:Reward Ratio: 1:{stop_loss_calc['risk_reward_ratio']:.2f}")

    print("\n" + "+" * 70)
    print("  DEMO COMPLETE")
    print("+" * 70 + "\n")


if __name__ == "__main__":
    main()
