"""Risk Management API Serializers"""
from rest_framework import serializers


class PositionSerializer(serializers.Serializer):
    """Serializer for position data"""
    id = serializers.CharField()
    pair = serializers.CharField()
    market_type = serializers.ChoiceField(choices=["crypto", "polymarket"])
    entry_price = serializers.FloatField()
    current_price = serializers.FloatField()
    amount = serializers.FloatField()
    value_usd = serializers.FloatField()
    unrealized_pnl = serializers.FloatField()
    leverage = serializers.FloatField(default=1.0)
    stop_loss = serializers.FloatField(allow_null=True, required=False)
    take_profit = serializers.FloatField(allow_null=True, required=False)


class RiskMetricsSerializer(serializers.Serializer):
    """Serializer for portfolio risk metrics"""
    total_exposure = serializers.FloatField()
    crypto_exposure = serializers.FloatField()
    polymarket_exposure = serializers.FloatField()
    diversification_score = serializers.FloatField()
    var_95 = serializers.FloatField()
    position_count = serializers.IntegerField()
    max_drawdown = serializers.FloatField()
    risk_level = serializers.CharField()
    correlation_risk = serializers.FloatField()
    leverage_ratio = serializers.FloatField()
    concentration_risk = serializers.FloatField()


class PortfolioRiskRequestSerializer(serializers.Serializer):
    """Serializer for portfolio risk calculation request"""
    positions = PositionSerializer(many=True)
    portfolio_value = serializers.FloatField(min_value=0.01)

    def validate_positions(self, value):
        """Validate positions list"""
        if not isinstance(value, list):
            raise serializers.ValidationError("positions must be a list")
        return value


class PortfolioRiskResponseSerializer(serializers.Serializer):
    """Serializer for portfolio risk response"""
    metrics = RiskMetricsSerializer()
    timestamp = serializers.CharField()
    portfolio_value = serializers.FloatField()


class PositionRiskRequestSerializer(serializers.Serializer):
    """Serializer for individual position risk request"""
    position = PositionSerializer()
    portfolio_value = serializers.FloatField(min_value=0.01)


class PositionRiskResponseSerializer(serializers.Serializer):
    """Serializer for position risk response"""
    position_id = serializers.CharField()
    pair = serializers.CharField()
    market_type = serializers.CharField()
    position_size_pct = serializers.FloatField()
    volatility = serializers.FloatField()
    potential_loss_usd = serializers.FloatField()
    stop_loss_distance_pct = serializers.FloatField(allow_null=True)
    leverage = serializers.FloatField()
    risk_level = serializers.CharField()
    exceeds_max_size = serializers.BooleanField()
    recommended_stop_loss = serializers.FloatField(allow_null=True)


class SignalRiskRequestSerializer(serializers.Serializer):
    """Serializer for LLM signal risk evaluation request"""
    consensus_metadata = serializers.DictField()
    market_conditions = serializers.DictField(required=False, allow_null=True)

    def validate_consensus_metadata(self, value):
        """Validate consensus metadata has required fields"""
        required_fields = ["weighted_confidence", "agreement_score", "participating_providers", "total_providers"]
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"consensus_metadata must contain '{field}'")
        return value


class SignalRiskResponseSerializer(serializers.Serializer):
    """Serializer for signal risk evaluation response"""
    risk_level = serializers.CharField()
    signal_strength = serializers.FloatField()
    provider_diversity = serializers.FloatField()
    confidence = serializers.FloatField()
    agreement_score = serializers.FloatField()
    recommended_position_size_pct = serializers.FloatField()
    should_trade = serializers.BooleanField()
    warnings = serializers.ListField(child=serializers.CharField())


class PositionLimitCheckRequestSerializer(serializers.Serializer):
    """Serializer for position limit check request"""
    positions = PositionSerializer(many=True)
    new_position_value = serializers.FloatField(min_value=0.01)
    new_position_type = serializers.ChoiceField(choices=["crypto", "polymarket"])
    portfolio_value = serializers.FloatField(min_value=0.01)


class PositionLimitCheckResponseSerializer(serializers.Serializer):
    """Serializer for position limit check response"""
    approved = serializers.BooleanField()
    violations = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())


class StopLossCalculationRequestSerializer(serializers.Serializer):
    """Serializer for stop loss calculation request"""
    entry_price = serializers.FloatField(min_value=0.01)
    position_type = serializers.ChoiceField(choices=["LONG", "SHORT"])
    volatility = serializers.FloatField(min_value=0.0, max_value=1.0)
    market_type = serializers.ChoiceField(choices=["crypto", "polymarket"])
    risk_per_trade = serializers.FloatField(default=0.02, min_value=0.001, max_value=0.1)


class StopLossCalculationResponseSerializer(serializers.Serializer):
    """Serializer for stop loss calculation response"""
    stop_loss = serializers.FloatField()
    take_profit = serializers.FloatField()
    stop_distance_pct = serializers.FloatField()
    take_distance_pct = serializers.FloatField()
    risk_reward_ratio = serializers.FloatField()
