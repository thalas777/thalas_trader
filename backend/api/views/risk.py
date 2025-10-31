"""Risk Management API Views"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.services.risk_manager import (
    RiskManager,
    Position,
    MarketType,
    RiskLevel,
)
from api.serializers.risk import (
    PortfolioRiskRequestSerializer,
    PortfolioRiskResponseSerializer,
    PositionRiskRequestSerializer,
    PositionRiskResponseSerializer,
    SignalRiskRequestSerializer,
    SignalRiskResponseSerializer,
    PositionLimitCheckRequestSerializer,
    PositionLimitCheckResponseSerializer,
    StopLossCalculationRequestSerializer,
    StopLossCalculationResponseSerializer,
)
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class PortfolioRiskView(APIView):
    """
    Calculate overall portfolio risk metrics

    POST /api/v1/risk/portfolio
    Request Body: {
        "positions": [
            {
                "id": "pos_1",
                "pair": "BTC/USDT",
                "market_type": "crypto",
                "entry_price": 42000.0,
                "current_price": 42500.0,
                "amount": 0.5,
                "value_usd": 21250.0,
                "unrealized_pnl": 250.0,
                "leverage": 1.0,
                "stop_loss": 41000.0,
                "take_profit": 45000.0
            }
        ],
        "portfolio_value": 50000.0
    }

    Response: {
        "metrics": {
            "total_exposure": 50000.0,
            "crypto_exposure": 35000.0,
            "polymarket_exposure": 15000.0,
            "diversification_score": 0.75,
            "var_95": 2500.0,
            "position_count": 8,
            "max_drawdown": 0.12,
            "risk_level": "medium",
            "correlation_risk": 0.45,
            "leverage_ratio": 1.2,
            "concentration_risk": 0.25
        },
        "timestamp": "2025-10-31T12:00:00Z",
        "portfolio_value": 50000.0
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.risk_manager = RiskManager()

    def post(self, request):
        """Calculate portfolio risk"""
        try:
            # Validate request
            request_serializer = PortfolioRiskRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                return Response(
                    {"error": "Invalid request data", "details": request_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = request_serializer.validated_data
            portfolio_value = validated_data["portfolio_value"]
            positions_data = validated_data["positions"]

            # Convert to Position objects
            positions = []
            for pos_data in positions_data:
                position = Position(
                    id=pos_data["id"],
                    pair=pos_data["pair"],
                    market_type=MarketType(pos_data["market_type"]),
                    entry_price=pos_data["entry_price"],
                    current_price=pos_data["current_price"],
                    amount=pos_data["amount"],
                    value_usd=pos_data["value_usd"],
                    unrealized_pnl=pos_data["unrealized_pnl"],
                    leverage=pos_data.get("leverage", 1.0),
                    stop_loss=pos_data.get("stop_loss"),
                    take_profit=pos_data.get("take_profit"),
                )
                positions.append(position)

            # Calculate risk metrics
            metrics = self.risk_manager.calculate_portfolio_risk(positions, portfolio_value)

            # Prepare response
            response_data = {
                "metrics": {
                    "total_exposure": metrics.total_exposure,
                    "crypto_exposure": metrics.crypto_exposure,
                    "polymarket_exposure": metrics.polymarket_exposure,
                    "diversification_score": metrics.diversification_score,
                    "var_95": metrics.var_95,
                    "position_count": metrics.position_count,
                    "max_drawdown": metrics.max_drawdown,
                    "risk_level": metrics.risk_level.value,
                    "correlation_risk": metrics.correlation_risk,
                    "leverage_ratio": metrics.leverage_ratio,
                    "concentration_risk": metrics.concentration_risk,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "portfolio_value": portfolio_value,
            }

            # Validate response
            response_serializer = PortfolioRiskResponseSerializer(data=response_data)
            if not response_serializer.is_valid():
                logger.error(f"Response serialization failed: {response_serializer.errors}")
                return Response(
                    {"error": "Response serialization failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(
                f"Portfolio risk calculated: {metrics.position_count} positions, "
                f"risk_level={metrics.risk_level.value}, exposure={metrics.total_exposure:.2f}"
            )

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Invalid input data: {e}")
            return Response(
                {"error": "Invalid input data", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Portfolio risk calculation error: {e}", exc_info=True)
            return Response(
                {"error": "Risk calculation failed", "detail": "An internal error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PositionRiskView(APIView):
    """
    Calculate risk for a single position

    POST /api/v1/risk/position
    Request Body: {
        "position": {
            "id": "pos_1",
            "pair": "BTC/USDT",
            "market_type": "crypto",
            "entry_price": 42000.0,
            "current_price": 42500.0,
            "amount": 0.5,
            "value_usd": 21250.0,
            "unrealized_pnl": 250.0,
            "leverage": 2.0
        },
        "portfolio_value": 50000.0
    }

    Response: {
        "position_id": "pos_1",
        "pair": "BTC/USDT",
        "market_type": "crypto",
        "position_size_pct": 42.5,
        "volatility": 0.0118,
        "potential_loss_usd": 250.75,
        "stop_loss_distance_pct": 2.35,
        "leverage": 2.0,
        "risk_level": "medium",
        "exceeds_max_size": false,
        "recommended_stop_loss": 41000.0
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.risk_manager = RiskManager()

    def post(self, request):
        """Calculate position risk"""
        try:
            # Validate request
            request_serializer = PositionRiskRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                return Response(
                    {"error": "Invalid request data", "details": request_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = request_serializer.validated_data
            portfolio_value = validated_data["portfolio_value"]
            pos_data = validated_data["position"]

            # Convert to Position object
            position = Position(
                id=pos_data["id"],
                pair=pos_data["pair"],
                market_type=MarketType(pos_data["market_type"]),
                entry_price=pos_data["entry_price"],
                current_price=pos_data["current_price"],
                amount=pos_data["amount"],
                value_usd=pos_data["value_usd"],
                unrealized_pnl=pos_data["unrealized_pnl"],
                leverage=pos_data.get("leverage", 1.0),
                stop_loss=pos_data.get("stop_loss"),
                take_profit=pos_data.get("take_profit"),
            )

            # Calculate position risk
            risk_data = self.risk_manager.calculate_position_risk(position, portfolio_value)

            # Validate response
            response_serializer = PositionRiskResponseSerializer(data=risk_data)
            if not response_serializer.is_valid():
                logger.error(f"Response serialization failed: {response_serializer.errors}")
                return Response(
                    {"error": "Response serialization failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(
                f"Position risk calculated: {position.pair}, "
                f"risk_level={risk_data['risk_level']}, size={risk_data['position_size_pct']:.2f}%"
            )

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Invalid input data: {e}")
            return Response(
                {"error": "Invalid input data", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Position risk calculation error: {e}", exc_info=True)
            return Response(
                {"error": "Risk calculation failed", "detail": "An internal error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SignalRiskView(APIView):
    """
    Evaluate risk of an LLM trading signal

    POST /api/v1/risk/evaluate-signal
    Request Body: {
        "consensus_metadata": {
            "weighted_confidence": 0.85,
            "agreement_score": 0.75,
            "participating_providers": 3,
            "total_providers": 4
        },
        "market_conditions": {
            "volatility": 0.15
        }
    }

    Response: {
        "risk_level": "low",
        "signal_strength": 0.800,
        "provider_diversity": 0.750,
        "confidence": 0.850,
        "agreement_score": 0.750,
        "recommended_position_size_pct": 15.0,
        "should_trade": true,
        "warnings": []
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.risk_manager = RiskManager()

    def post(self, request):
        """Evaluate signal risk"""
        try:
            # Validate request
            request_serializer = SignalRiskRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                return Response(
                    {"error": "Invalid request data", "details": request_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = request_serializer.validated_data
            consensus_metadata = validated_data["consensus_metadata"]
            market_conditions = validated_data.get("market_conditions")

            # Evaluate signal risk
            risk_evaluation = self.risk_manager.evaluate_signal_risk(
                consensus_metadata, market_conditions
            )

            # Validate response
            response_serializer = SignalRiskResponseSerializer(data=risk_evaluation)
            if not response_serializer.is_valid():
                logger.error(f"Response serialization failed: {response_serializer.errors}")
                return Response(
                    {"error": "Response serialization failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(
                f"Signal risk evaluated: risk_level={risk_evaluation['risk_level']}, "
                f"signal_strength={risk_evaluation['signal_strength']:.3f}, "
                f"should_trade={risk_evaluation['should_trade']}"
            )

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Invalid input data: {e}")
            return Response(
                {"error": "Invalid input data", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Signal risk evaluation error: {e}", exc_info=True)
            return Response(
                {"error": "Risk evaluation failed", "detail": "An internal error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PositionLimitCheckView(APIView):
    """
    Check if a new position would violate limits

    POST /api/v1/risk/check-limits
    Request Body: {
        "positions": [...],
        "new_position_value": 5000.0,
        "new_position_type": "crypto",
        "portfolio_value": 50000.0
    }

    Response: {
        "approved": true,
        "violations": [],
        "warnings": ["Position size near limit (14.5%)"]
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.risk_manager = RiskManager()

    def post(self, request):
        """Check position limits"""
        try:
            # Validate request
            request_serializer = PositionLimitCheckRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                return Response(
                    {"error": "Invalid request data", "details": request_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = request_serializer.validated_data
            positions_data = validated_data["positions"]
            new_position_value = validated_data["new_position_value"]
            new_position_type = MarketType(validated_data["new_position_type"])
            portfolio_value = validated_data["portfolio_value"]

            # Convert to Position objects
            positions = []
            for pos_data in positions_data:
                position = Position(
                    id=pos_data["id"],
                    pair=pos_data["pair"],
                    market_type=MarketType(pos_data["market_type"]),
                    entry_price=pos_data["entry_price"],
                    current_price=pos_data["current_price"],
                    amount=pos_data["amount"],
                    value_usd=pos_data["value_usd"],
                    unrealized_pnl=pos_data["unrealized_pnl"],
                    leverage=pos_data.get("leverage", 1.0),
                    stop_loss=pos_data.get("stop_loss"),
                    take_profit=pos_data.get("take_profit"),
                )
                positions.append(position)

            # Check limits
            limit_check = self.risk_manager.check_position_limits(
                positions, new_position_value, new_position_type, portfolio_value
            )

            # Validate response
            response_serializer = PositionLimitCheckResponseSerializer(data=limit_check)
            if not response_serializer.is_valid():
                logger.error(f"Response serialization failed: {response_serializer.errors}")
                return Response(
                    {"error": "Response serialization failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(
                f"Position limit check: approved={limit_check['approved']}, "
                f"violations={len(limit_check['violations'])}, warnings={len(limit_check['warnings'])}"
            )

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Invalid input data: {e}")
            return Response(
                {"error": "Invalid input data", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Position limit check error: {e}", exc_info=True)
            return Response(
                {"error": "Limit check failed", "detail": "An internal error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StopLossCalculationView(APIView):
    """
    Calculate recommended stop-loss and take-profit levels

    POST /api/v1/risk/calculate-stop-loss
    Request Body: {
        "entry_price": 42500.0,
        "position_type": "LONG",
        "volatility": 0.15,
        "market_type": "crypto",
        "risk_per_trade": 0.02
    }

    Response: {
        "stop_loss": 41275.0,
        "take_profit": 45950.0,
        "stop_distance_pct": 2.88,
        "take_distance_pct": 8.12,
        "risk_reward_ratio": 2.82
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.risk_manager = RiskManager()

    def post(self, request):
        """Calculate stop loss levels"""
        try:
            # Validate request
            request_serializer = StopLossCalculationRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                return Response(
                    {"error": "Invalid request data", "details": request_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = request_serializer.validated_data

            # Calculate stop loss
            stop_loss_data = self.risk_manager.calculate_stop_loss(
                entry_price=validated_data["entry_price"],
                position_type=validated_data["position_type"],
                volatility=validated_data["volatility"],
                market_type=MarketType(validated_data["market_type"]),
                risk_per_trade=validated_data.get("risk_per_trade", 0.02),
            )

            # Validate response
            response_serializer = StopLossCalculationResponseSerializer(data=stop_loss_data)
            if not response_serializer.is_valid():
                logger.error(f"Response serialization failed: {response_serializer.errors}")
                return Response(
                    {"error": "Response serialization failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(
                f"Stop loss calculated: entry={validated_data['entry_price']}, "
                f"sl={stop_loss_data['stop_loss']}, tp={stop_loss_data['take_profit']}"
            )

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Invalid input data: {e}")
            return Response(
                {"error": "Invalid input data", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Stop loss calculation error: {e}", exc_info=True)
            return Response(
                {"error": "Calculation failed", "detail": "An internal error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
