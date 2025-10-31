"""
Signal Aggregator for Multi-LLM Consensus
Implements weighted voting and consensus algorithms
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter
import logging

from llm_service.providers.base import ProviderResponse

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    """
    Result of consensus aggregation across multiple LLM providers

    Contains the final decision, confidence, and detailed breakdown
    of how consensus was achieved.
    """
    decision: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 to 1.0
    reasoning: str
    risk_level: str
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None

    # Consensus metadata
    total_providers: int = 0
    participating_providers: int = 0
    agreement_score: float = 0.0  # How well providers agreed
    weighted_confidence: float = 0.0

    # Individual provider responses
    provider_responses: List[ProviderResponse] = field(default_factory=list)
    vote_breakdown: Dict[str, int] = field(default_factory=dict)
    weighted_votes: Dict[str, float] = field(default_factory=dict)

    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_latency_ms: Optional[float] = None

    # Cost tracking
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert consensus result to dictionary"""
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
            "suggested_stop_loss": self.suggested_stop_loss,
            "suggested_take_profit": self.suggested_take_profit,
            "consensus_metadata": {
                "total_providers": self.total_providers,
                "participating_providers": self.participating_providers,
                "agreement_score": self.agreement_score,
                "weighted_confidence": self.weighted_confidence,
                "vote_breakdown": self.vote_breakdown,
                "weighted_votes": self.weighted_votes,
                "total_latency_ms": self.total_latency_ms,
                "total_cost_usd": self.total_cost_usd,
                "total_tokens": self.total_tokens,
                "timestamp": self.timestamp.isoformat(),
            },
            "provider_responses": [
                {
                    "provider": resp.provider_name,
                    "decision": resp.decision,
                    "confidence": resp.confidence,
                    "reasoning": resp.reasoning[:200] + "..." if len(resp.reasoning) > 200 else resp.reasoning,
                }
                for resp in self.provider_responses
            ],
        }


class SignalAggregator:
    """
    Aggregates signals from multiple LLM providers using weighted voting

    Implements several consensus strategies:
    - Weighted majority voting
    - Confidence-weighted averaging
    - Risk-adjusted aggregation
    """

    def __init__(self, min_providers: int = 1, min_confidence: float = 0.5):
        """
        Initialize signal aggregator

        Args:
            min_providers: Minimum number of providers required for consensus
            min_confidence: Minimum confidence threshold for final decision
        """
        self.min_providers = min_providers
        self.min_confidence = min_confidence
        logger.info(
            f"SignalAggregator initialized (min_providers={min_providers}, "
            f"min_confidence={min_confidence})"
        )

    def aggregate(
        self,
        responses: List[ProviderResponse],
        weights: Optional[Dict[str, float]] = None
    ) -> ConsensusResult:
        """
        Aggregate multiple provider responses into consensus

        Args:
            responses: List of provider responses
            weights: Optional dict mapping provider names to weights

        Returns:
            ConsensusResult with consensus decision

        Raises:
            ValueError: If insufficient providers or invalid data
        """
        if not responses:
            raise ValueError("No provider responses to aggregate")

        if len(responses) < self.min_providers:
            raise ValueError(
                f"Insufficient providers: {len(responses)} < {self.min_providers}"
            )

        # Use equal weights if not provided
        if weights is None:
            weights = {resp.provider_name: 1.0 for resp in responses}

        # Perform weighted voting
        weighted_votes = self._calculate_weighted_votes(responses, weights)
        vote_breakdown = self._count_votes(responses)

        # Determine consensus decision
        decision = max(weighted_votes.items(), key=lambda x: x[1])[0]

        # Calculate consensus confidence
        confidence = self._calculate_consensus_confidence(
            responses, decision, weights
        )

        # Calculate agreement score
        agreement_score = self._calculate_agreement_score(
            responses, decision, weighted_votes
        )

        # Aggregate reasoning
        reasoning = self._aggregate_reasoning(responses, decision)

        # Determine consensus risk level
        risk_level = self._aggregate_risk_level(responses)

        # Calculate stop loss and take profit
        stop_loss = self._aggregate_stop_loss(responses, decision)
        take_profit = self._aggregate_take_profit(responses, decision)

        # Calculate total metrics
        total_latency = sum(
            r.latency_ms for r in responses if r.latency_ms
        )
        total_cost = sum(
            r.cost_usd for r in responses if r.cost_usd
        )
        total_tokens = sum(
            r.tokens_used for r in responses if r.tokens_used
        )

        # Build consensus result
        result = ConsensusResult(
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            risk_level=risk_level,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            total_providers=len(responses),
            participating_providers=len(responses),
            agreement_score=agreement_score,
            weighted_confidence=confidence,
            provider_responses=responses,
            vote_breakdown=vote_breakdown,
            weighted_votes=weighted_votes,
            total_latency_ms=total_latency,
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
        )

        logger.info(
            f"Consensus reached: {decision} (confidence: {confidence:.2f}, "
            f"agreement: {agreement_score:.2f}, providers: {len(responses)})"
        )

        return result

    def _calculate_weighted_votes(
        self,
        responses: List[ProviderResponse],
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate weighted votes for each decision"""
        weighted_votes = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}

        for response in responses:
            weight = weights.get(response.provider_name, 1.0)
            # Weight by both provider weight and response confidence
            vote_weight = weight * response.confidence
            weighted_votes[response.decision] += vote_weight

        return weighted_votes

    def _count_votes(self, responses: List[ProviderResponse]) -> Dict[str, int]:
        """Count raw votes for each decision"""
        return dict(Counter(r.decision for r in responses))

    def _calculate_consensus_confidence(
        self,
        responses: List[ProviderResponse],
        decision: str,
        weights: Dict[str, float]
    ) -> float:
        """
        Calculate consensus confidence for the chosen decision

        Considers:
        - Average confidence of providers voting for this decision
        - Weight of supporting providers
        - Agreement level among all providers
        """
        # Get responses supporting the consensus decision
        supporting_responses = [
            r for r in responses if r.decision == decision
        ]

        if not supporting_responses:
            return 0.0

        # Calculate weighted average confidence
        total_weight = 0.0
        weighted_sum = 0.0

        for response in supporting_responses:
            weight = weights.get(response.provider_name, 1.0)
            total_weight += weight
            weighted_sum += response.confidence * weight

        base_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Adjust based on agreement (penalize if many providers disagree)
        agreement_factor = len(supporting_responses) / len(responses)

        # Final confidence is weighted average adjusted by agreement
        final_confidence = base_confidence * (0.7 + 0.3 * agreement_factor)

        return min(1.0, max(0.0, final_confidence))

    def _calculate_agreement_score(
        self,
        responses: List[ProviderResponse],
        decision: str,
        weighted_votes: Dict[str, float]
    ) -> float:
        """
        Calculate how much providers agree on the decision

        Returns:
            Score from 0.0 (total disagreement) to 1.0 (unanimous)
        """
        total_weight = sum(weighted_votes.values())
        if total_weight == 0:
            return 0.0

        consensus_weight = weighted_votes[decision]
        return consensus_weight / total_weight

    def _aggregate_reasoning(
        self,
        responses: List[ProviderResponse],
        decision: str
    ) -> str:
        """
        Aggregate reasoning from providers supporting the decision

        Args:
            responses: All provider responses
            decision: Consensus decision

        Returns:
            Combined reasoning text
        """
        supporting_responses = [
            r for r in responses if r.decision == decision
        ]

        if not supporting_responses:
            return "No consensus reasoning available"

        # Take reasoning from the most confident provider
        most_confident = max(supporting_responses, key=lambda r: r.confidence)

        base_reasoning = f"Consensus ({len(supporting_responses)}/{len(responses)} providers agree): "
        base_reasoning += most_confident.reasoning

        return base_reasoning

    def _aggregate_risk_level(self, responses: List[ProviderResponse]) -> str:
        """
        Aggregate risk level from all responses

        Uses conservative approach - takes the highest risk level
        """
        risk_levels = [r.risk_level for r in responses if r.risk_level]

        if not risk_levels:
            return "medium"

        # Risk priority: high > medium > low
        risk_priority = {"high": 3, "medium": 2, "low": 1}

        highest_risk = max(
            risk_levels,
            key=lambda x: risk_priority.get(x.lower(), 2)
        )

        return highest_risk

    def _aggregate_stop_loss(
        self,
        responses: List[ProviderResponse],
        decision: str
    ) -> Optional[float]:
        """Aggregate stop loss from supporting providers"""
        supporting_responses = [
            r for r in responses
            if r.decision == decision and r.suggested_stop_loss
        ]

        if not supporting_responses:
            return None

        # Use median stop loss for robustness
        stop_losses = sorted(r.suggested_stop_loss for r in supporting_responses)
        median_idx = len(stop_losses) // 2

        return stop_losses[median_idx]

    def _aggregate_take_profit(
        self,
        responses: List[ProviderResponse],
        decision: str
    ) -> Optional[float]:
        """Aggregate take profit from supporting providers"""
        supporting_responses = [
            r for r in responses
            if r.decision == decision and r.suggested_take_profit
        ]

        if not supporting_responses:
            return None

        # Use median take profit for robustness
        take_profits = sorted(r.suggested_take_profit for r in supporting_responses)
        median_idx = len(take_profits) // 2

        return take_profits[median_idx]
