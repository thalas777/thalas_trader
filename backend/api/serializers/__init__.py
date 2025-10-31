"""API Serializers for Thalas Trader"""
from rest_framework import serializers


class ProviderResponseSerializer(serializers.Serializer):
    """Serializer for individual provider response"""
    provider = serializers.CharField()
    decision = serializers.CharField()
    confidence = serializers.FloatField()
    reasoning = serializers.CharField()


class ConsensusMetadataSerializer(serializers.Serializer):
    """Serializer for consensus metadata"""
    total_providers = serializers.IntegerField()
    participating_providers = serializers.IntegerField()
    agreement_score = serializers.FloatField()
    weighted_confidence = serializers.FloatField()
    vote_breakdown = serializers.DictField()
    weighted_votes = serializers.DictField()
    total_latency_ms = serializers.FloatField(allow_null=True)
    total_cost_usd = serializers.FloatField()
    total_tokens = serializers.IntegerField()
    timestamp = serializers.CharField()


class ConsensusResultSerializer(serializers.Serializer):
    """Serializer for consensus result response"""
    decision = serializers.CharField()
    confidence = serializers.FloatField()
    reasoning = serializers.CharField()
    risk_level = serializers.CharField()
    suggested_stop_loss = serializers.FloatField(allow_null=True, required=False)
    suggested_take_profit = serializers.FloatField(allow_null=True, required=False)
    consensus_metadata = ConsensusMetadataSerializer()
    provider_responses = ProviderResponseSerializer(many=True)


class ConsensusRequestSerializer(serializers.Serializer):
    """Serializer for consensus request"""
    market_data = serializers.DictField()
    pair = serializers.CharField()
    timeframe = serializers.CharField(default="5m")
    current_price = serializers.FloatField()
    provider_weights = serializers.DictField(required=False, allow_null=True)

    def validate_market_data(self, value):
        """Validate market_data is a non-empty dictionary"""
        if not value:
            raise serializers.ValidationError("market_data cannot be empty")
        return value

    def validate_timeframe(self, value):
        """Validate timeframe format"""
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        if value not in valid_timeframes:
            raise serializers.ValidationError(
                f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            )
        return value

    def validate_provider_weights(self, value):
        """Validate provider weights if provided"""
        if value is not None:
            for provider, weight in value.items():
                if not isinstance(weight, (int, float)):
                    raise serializers.ValidationError(
                        f"Weight for {provider} must be a number"
                    )
                if weight < 0 or weight > 1:
                    raise serializers.ValidationError(
                        f"Weight for {provider} must be between 0 and 1"
                    )
        return value
