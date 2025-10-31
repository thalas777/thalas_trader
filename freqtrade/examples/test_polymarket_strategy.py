#!/usr/bin/env python
"""
Test script for Polymarket LLM Strategy
Demonstrates how to use the strategy and consensus provider

This script:
1. Tests the PolymarketLLMProvider connection
2. Simulates market data for a prediction market
3. Gets LLM consensus prediction
4. Shows how the strategy would respond

Run from freqtrade directory:
    python examples/test_polymarket_strategy.py
"""
import sys
import os
from pathlib import Path

# Add adapters to path
sys.path.insert(0, str(Path(__file__).parent.parent / "adapters"))

from polymarket_llm_provider import PolymarketLLMProvider
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_health_check():
    """Test if LLM consensus service is available"""
    print("\n" + "="*80)
    print("TEST 1: Health Check")
    print("="*80)

    provider = PolymarketLLMProvider()
    health = provider.health_check()

    print(f"\nHealth Status: {health.get('status', 'unknown')}")
    print(f"Available Providers: {health.get('available_providers', 0)}")
    print(f"Required Providers: {health.get('required_providers', 1)}")

    if health.get('configured'):
        print("✓ Service is configured and ready")
        return True
    else:
        print(f"✗ Service not available: {health.get('error', 'Unknown error')}")
        return False


def test_market_prediction():
    """Test getting prediction for a sample market"""
    print("\n" + "="*80)
    print("TEST 2: Market Prediction")
    print("="*80)

    # Sample prediction market
    market_context = {
        "question": "Will Bitcoin reach $100k by end of 2025?",
        "current_yes_price": 0.45,  # 45% probability
        "current_no_price": 0.55,   # 55% probability
        "volume_24h": 50000,
        "expiration_date": "2025-12-31",
        "days_to_expiration": 60,
        "current_date": "2025-10-31",
        "momentum_24h": 5.0,  # +5% in last 24h
        "volatility": 0.05,
    }

    print(f"\nMarket Question: {market_context['question']}")
    print(f"Current YES Probability: {market_context['current_yes_price']:.1%}")
    print(f"Current NO Probability: {market_context['current_no_price']:.1%}")
    print(f"24h Volume: ${market_context['volume_24h']:,.0f}")
    print(f"Days to Expiration: {market_context['days_to_expiration']}")
    print(f"24h Momentum: {market_context['momentum_24h']:+.1f}%")

    # Get consensus prediction
    provider = PolymarketLLMProvider()

    print("\n⏳ Requesting LLM consensus prediction...")
    consensus = provider.get_market_prediction(
        market_context=market_context,
        include_provider_breakdown=True
    )

    # Display results
    print("\n" + "-"*80)
    print("CONSENSUS RESULT")
    print("-"*80)

    decision = consensus.get('decision', 'UNKNOWN')
    confidence = consensus.get('confidence', 0.0)
    reasoning = consensus.get('reasoning', 'N/A')

    print(f"\n🎯 Decision: {decision}")
    print(f"📊 Confidence: {confidence:.1%}")
    print(f"💭 Reasoning: {reasoning[:200]}...")

    # Consensus metadata
    metadata = consensus.get('consensus_metadata', {})
    print(f"\n📈 Consensus Metadata:")
    print(f"   Total Providers: {metadata.get('total_providers', 0)}")
    print(f"   Participating: {metadata.get('participating_providers', 0)}")
    print(f"   Agreement Score: {metadata.get('agreement_score', 0):.1%}")
    print(f"   Vote Breakdown: {metadata.get('vote_breakdown', {})}")
    print(f"   Weighted Votes: {metadata.get('weighted_votes', {})}")
    print(f"   Total Latency: {metadata.get('total_latency_ms', 0):.0f}ms")
    print(f"   Total Cost: ${metadata.get('total_cost_usd', 0):.6f}")
    print(f"   Total Tokens: {metadata.get('total_tokens', 0)}")

    # Provider breakdown
    provider_responses = consensus.get('provider_responses', [])
    if provider_responses:
        print(f"\n🤖 Provider Breakdown:")
        for resp in provider_responses:
            print(f"   {resp.get('provider', 'Unknown'):12s} | "
                  f"{resp.get('decision', 'N/A'):4s} | "
                  f"Confidence: {resp.get('confidence', 0):.1%}")

    return consensus


def test_kelly_calculation():
    """Test Kelly Criterion position sizing calculation"""
    print("\n" + "="*80)
    print("TEST 3: Kelly Criterion Position Sizing")
    print("="*80)

    # Example from consensus
    consensus_confidence = 0.82  # 82% confidence from LLMs
    market_probability = 0.45    # Market prices YES at 45%

    print(f"\nLLM Consensus Confidence: {consensus_confidence:.1%}")
    print(f"Market YES Probability: {market_probability:.1%}")

    # Kelly Criterion calculation
    p = consensus_confidence  # Probability of winning
    q = 1.0 - p              # Probability of losing
    b = (1.0 - market_probability) / market_probability  # Odds

    kelly_full = (b * p - q) / b
    print(f"\nOdds (b): {b:.2f} to 1")
    print(f"Win Probability (p): {p:.1%}")
    print(f"Loss Probability (q): {q:.1%}")
    print(f"Full Kelly: {kelly_full:.1%}")

    # Apply Kelly fractions
    kelly_fractions = [0.25, 0.50, 1.0]
    print(f"\n📊 Position Sizing (% of capital):")

    for fraction in kelly_fractions:
        stake = kelly_full * fraction
        stake = max(0.0, min(stake, 0.25))  # Cap at 25%

        fraction_name = {
            0.25: "Quarter Kelly (Conservative)",
            0.50: "Half Kelly (Moderate)",
            1.0: "Full Kelly (Aggressive)"
        }.get(fraction, f"{fraction:.0%} Kelly")

        print(f"   {fraction_name:30s}: {stake:.1%}")

    # Expected value calculation
    expected_value = (p * b - q) * 100
    print(f"\n💰 Expected Value (per $100 bet): ${expected_value:.2f}")

    if kelly_full > 0:
        print("\n✓ Positive edge detected - Position recommended")
    else:
        print("\n✗ No edge detected - Skip this market")


def test_batch_predictions():
    """Test batch predictions for multiple markets"""
    print("\n" + "="*80)
    print("TEST 4: Batch Market Predictions")
    print("="*80)

    markets = [
        {
            "question": "Will Bitcoin reach $100k by end of 2025?",
            "current_yes_price": 0.45,
            "volume_24h": 50000,
            "days_to_expiration": 60,
        },
        {
            "question": "Will Ethereum reach $5k by end of 2025?",
            "current_yes_price": 0.60,
            "volume_24h": 30000,
            "days_to_expiration": 60,
        },
        {
            "question": "Will Solana reach $200 by Q1 2026?",
            "current_yes_price": 0.35,
            "volume_24h": 15000,
            "days_to_expiration": 90,
        },
    ]

    print(f"\n📋 Analyzing {len(markets)} markets...")

    provider = PolymarketLLMProvider()
    results = provider.get_batch_predictions(markets, max_concurrent=2)

    print(f"\n✓ Received {len(results)} predictions\n")

    print("-"*80)
    print(f"{'Market':<45s} | {'Decision':<6s} | {'Conf':<6s} | {'Edge':<6s}")
    print("-"*80)

    for question, consensus in results.items():
        decision = consensus.get('decision', 'N/A')
        confidence = consensus.get('confidence', 0.0)

        # Find original market
        market = next((m for m in markets if m['question'] == question), None)
        market_prob = market['current_yes_price'] if market else 0.5

        # Calculate edge
        if decision == 'BUY':
            edge = confidence - market_prob
        elif decision == 'SELL':
            edge = (1.0 - confidence) - (1.0 - market_prob)
        else:
            edge = 0.0

        # Truncate question for display
        short_question = question[:42] + "..." if len(question) > 45 else question

        print(f"{short_question:<45s} | {decision:<6s} | {confidence:>5.1%} | {edge:>+5.1%}")

    print("-"*80)


def main():
    """Run all tests"""
    print("\n" + "█"*80)
    print("POLYMARKET LLM STRATEGY - TEST SUITE")
    print("█"*80)

    try:
        # Test 1: Health check
        if not test_health_check():
            print("\n⚠️  Warning: Backend service not available")
            print("Make sure Django backend is running:")
            print("  cd backend && python manage.py runserver")
            return

        # Test 2: Single market prediction
        test_market_prediction()

        # Test 3: Kelly Criterion
        test_kelly_calculation()

        # Test 4: Batch predictions
        test_batch_predictions()

        print("\n" + "█"*80)
        print("ALL TESTS COMPLETED SUCCESSFULLY ✓")
        print("█"*80)

        print("\n📚 Next Steps:")
        print("   1. Review the strategy file: freqtrade/strategies/LLM_Polymarket_Strategy.py")
        print("   2. Configure your settings: freqtrade/config_polymarket.json")
        print("   3. Read the documentation: freqtrade/POLYMARKET_STRATEGY_README.md")
        print("   4. Run in dry-run mode: freqtrade trade --config config_polymarket.json")
        print()

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n✗ Test suite failed: {e}")


if __name__ == "__main__":
    main()
