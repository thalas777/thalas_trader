"""LLM Strategy API Views"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from llm_service.orchestrator import get_llm_orchestrator, LLMOrchestratorError
from llm_service.multi_provider_orchestrator import MultiProviderOrchestrator
from llm_service.providers.registry import get_registry
from llm_service.providers.base import ProviderError, ProviderAuthenticationError
from api.serializers import ConsensusRequestSerializer, ConsensusResultSerializer
import logging
import asyncio

logger = logging.getLogger(__name__)


class LLMSignalView(APIView):
    """
    Generate trading signal using LLM

    POST /api/v1/strategies/llm
    Request Body: {
        "market_data": {
            "rsi": 45.2,
            "ema_20": 42500.0,
            "ema_50": 42300.0,
            "volume": 1250000,
            "recent_candles": [...]
        },
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "current_price": 42500.0,
        "provider": "anthropic"  // optional
    }

    Response: {
        "decision": "BUY" | "SELL" | "HOLD",
        "confidence": 0.85,
        "reasoning": "Technical analysis indicates...",
        "risk_level": "medium",
        "suggested_stop_loss": 42000.0,
        "suggested_take_profit": 43500.0
    }
    """

    def post(self, request):
        try:
            # Validate request data
            market_data = request.data.get("market_data")
            pair = request.data.get("pair")
            timeframe = request.data.get("timeframe", "5m")
            current_price = request.data.get("current_price")
            provider = request.data.get("provider")  # Optional

            if not market_data or not pair:
                return Response(
                    {"error": "market_data and pair are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get LLM orchestrator
            try:
                orchestrator = get_llm_orchestrator()
            except LLMOrchestratorError as e:
                logger.error(f"LLM orchestrator unavailable: {e}")
                return Response(
                    {"error": "LLM service not configured"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # Generate signal
            signal = orchestrator.generate_trading_signal(
                market_data=market_data,
                pair=pair,
                timeframe=timeframe,
                current_price=current_price,
            )

            # Add metadata
            signal["pair"] = pair
            signal["timeframe"] = timeframe
            signal["provider"] = orchestrator.provider
            signal["model"] = orchestrator.model

            return Response(signal, status=status.HTTP_200_OK)

        except LLMOrchestratorError as e:
            logger.error(f"LLM signal generation failed: {e}")
            return Response(
                {"error": f"Signal generation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            logger.error(f"LLM signal endpoint error: {e}")
            return Response(
                {"error": "Unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request):
        """
        Health check endpoint for LLM service

        GET /api/v1/strategies/llm
        Returns: Service status and configuration
        """
        try:
            orchestrator = get_llm_orchestrator()
            health = orchestrator.health_check()
            return Response(health, status=status.HTTP_200_OK)
        except LLMOrchestratorError as e:
            return Response(
                {
                    "configured": False,
                    "error": str(e),
                },
                status=status.HTTP_200_OK,
            )


class LLMConsensusView(APIView):
    """
    Generate trading signal using multi-provider LLM consensus

    POST /api/v1/strategies/llm-consensus
    Request Body: {
        "market_data": {
            "rsi": 65.5,
            "macd": 150.0,
            "bollinger_upper": 51000,
            "bollinger_lower": 49000
        },
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "current_price": 50000.0,
        "provider_weights": {  // optional
            "Anthropic": 1.0,
            "OpenAI": 0.9
        }
    }

    Response (200 OK): {
        "decision": "BUY",
        "confidence": 0.82,
        "reasoning": "Consensus (3/4 providers agree): Strong bullish momentum...",
        "risk_level": "medium",
        "suggested_stop_loss": 48500.0,
        "suggested_take_profit": 52000.0,
        "consensus_metadata": {
            "total_providers": 4,
            "participating_providers": 3,
            "agreement_score": 0.75,
            "weighted_confidence": 0.82,
            "vote_breakdown": {"BUY": 3, "HOLD": 1},
            "weighted_votes": {"BUY": 2.4, "HOLD": 0.6, "SELL": 0.0},
            "total_latency_ms": 1850.5,
            "total_cost_usd": 0.0234,
            "total_tokens": 2450,
            "timestamp": "2025-10-30T12:34:56.789Z"
        },
        "provider_responses": [
            {
                "provider": "Anthropic",
                "decision": "BUY",
                "confidence": 0.85,
                "reasoning": "Strong momentum indicators..."
            }
        ]
    }

    Error Response (503 Service Unavailable): {
        "error": "No LLM providers available",
        "detail": "All configured providers are unavailable or disabled"
    }
    """

    def post(self, request):
        """Generate consensus signal from multiple LLM providers"""
        try:
            # Validate request data using serializer
            serializer = ConsensusRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Invalid request data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Extract validated data
            validated_data = serializer.validated_data
            market_data = validated_data["market_data"]
            pair = validated_data["pair"]
            timeframe = validated_data.get("timeframe", "5m")
            current_price = validated_data["current_price"]
            provider_weights = validated_data.get("provider_weights")

            logger.info(
                f"Consensus signal request for {pair} ({timeframe}) "
                f"at price {current_price}"
            )

            # Initialize provider registry and orchestrator
            try:
                registry = get_registry()
                orchestrator = MultiProviderOrchestrator(
                    registry=registry,
                    min_providers=1,
                    min_confidence=0.5,
                    timeout_seconds=30.0
                )
            except Exception as e:
                logger.error(f"Failed to initialize orchestrator: {e}")
                return Response(
                    {
                        "error": "LLM service initialization failed",
                        "detail": str(e)
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # Check if any providers are available
            available_providers = registry.get_available_providers()
            if not available_providers:
                logger.warning("No LLM providers available")
                return Response(
                    {
                        "error": "No LLM providers available",
                        "detail": "All configured providers are unavailable or disabled"
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # Generate consensus signal (async)
            try:
                # Run the async function in an event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    consensus = loop.run_until_complete(
                        orchestrator.generate_consensus_signal(
                            market_data=market_data,
                            pair=pair,
                            timeframe=timeframe,
                            current_price=current_price,
                            provider_weights=provider_weights,
                        )
                    )
                finally:
                    loop.close()

            except ValueError as e:
                # Insufficient providers or validation errors
                logger.error(f"Consensus generation failed (validation): {e}")
                return Response(
                    {
                        "error": "Insufficient providers or invalid data",
                        "detail": str(e)
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            except RuntimeError as e:
                # Consensus aggregation failed
                logger.error(f"Consensus aggregation failed: {e}")
                return Response(
                    {
                        "error": "Consensus aggregation failed",
                        "detail": str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            except ProviderAuthenticationError as e:
                # Authentication errors
                logger.error(f"Provider authentication failed: {e}")
                return Response(
                    {
                        "error": "Provider authentication failed",
                        "detail": str(e)
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            except ProviderError as e:
                # Other provider errors
                logger.error(f"Provider error: {e}")
                return Response(
                    {
                        "error": "Provider error occurred",
                        "detail": str(e)
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # Convert ConsensusResult to dict and serialize
            consensus_dict = consensus.to_dict()

            # Validate response format with serializer
            response_serializer = ConsensusResultSerializer(data=consensus_dict)
            if not response_serializer.is_valid():
                logger.error(f"Consensus serialization failed: {response_serializer.errors}")
                return Response(
                    {
                        "error": "Response serialization failed",
                        "detail": response_serializer.errors
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(
                f"Consensus signal generated successfully: "
                f"{consensus.decision} (confidence: {consensus.confidence:.2f}, "
                f"providers: {consensus.participating_providers}/{consensus.total_providers})"
            )

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Unexpected error in consensus endpoint: {e}", exc_info=True)
            return Response(
                {
                    "error": "Unexpected error occurred",
                    "detail": "An internal error occurred while processing your request"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request):
        """
        Health check endpoint for consensus service

        GET /api/v1/strategies/llm-consensus
        Returns: Service status and available providers
        """
        try:
            registry = get_registry()
            orchestrator = MultiProviderOrchestrator(
                registry=registry,
                min_providers=1,
                min_confidence=0.5,
                timeout_seconds=30.0
            )

            # Run health check async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                health_status = loop.run_until_complete(orchestrator.health_check())
            finally:
                loop.close()

            # Add metrics
            metrics = orchestrator.get_metrics()
            health_status["metrics"] = metrics

            return Response(health_status, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return Response(
                {
                    "status": "unavailable",
                    "error": str(e),
                    "available_providers": 0,
                    "required_providers": 1,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
