"""Bot Management API Views"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.models import PaperBot
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class BotListView(APIView):
    """
    Get list of all bots

    GET /api/v1/bots
    Returns: List of bot objects

    POST /api/v1/bots
    Creates a new bot
    """

    def get(self, request):
        try:
            bots = PaperBot.objects.all()
            bot_list = [
                {
                    "bot_id": bot.id,
                    "name": bot.name,
                    "status": bot.status,
                    "strategy": bot.strategy,
                    "pair": bot.current_pair if bot.auto_mode else bot.pair,
                    "auto_mode": bot.auto_mode,
                    "current_pair": bot.current_pair,
                    "profit": float(bot.total_profit),
                    "profit_percentage": bot.profit_percentage,
                    "trades_count": bot.trades.count(),
                }
                for bot in bots
            ]
            return Response({"bots": bot_list}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Bot list endpoint error: {e}")
            return Response(
                {"error": "Failed to fetch bot list"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """Create a new trading bot"""
        try:
            data = request.data

            # Get auto_mode flag (default False)
            auto_mode = data.get('auto_mode', False)

            # Validate required fields based on mode
            if auto_mode:
                required_fields = ['name', 'strategy', 'initial_balance', 'position_size']
            else:
                required_fields = ['name', 'pair', 'strategy', 'initial_balance', 'position_size']

            for field in required_fields:
                if field not in data:
                    return Response(
                        {"error": f"Missing required field: {field}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Create bot
            bot_params = {
                'name': data['name'],
                'strategy': data['strategy'],
                'initial_balance': Decimal(str(data['initial_balance'])),
                'current_balance': Decimal(str(data['initial_balance'])),
                'position_size': Decimal(str(data['position_size'])),
                'status': 'stopped',
                'auto_mode': auto_mode,
            }

            # Add pair only if not in auto mode
            if not auto_mode:
                bot_params['pair'] = data['pair']

            bot = PaperBot.objects.create(**bot_params)

            logger.info(f"Created new bot: {bot.name} (ID: {bot.id}, Auto Mode: {auto_mode})")

            return Response(
                {
                    "message": f"Bot '{bot.name}' created successfully",
                    "bot_id": bot.id,
                    "auto_mode": auto_mode
                },
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            logger.error(f"Bot creation validation error: {e}")
            return Response(
                {"error": "Invalid numeric value provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Bot creation error: {e}")
            return Response(
                {"error": "Failed to create bot"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BotDetailView(APIView):
    """
    Get details of a specific bot

    GET /api/v1/bots/<bot_id>
    """

    def get(self, request, bot_id):
        try:
            bot = PaperBot.objects.get(id=bot_id)
            bot_data = {
                "bot_id": bot.id,
                "name": bot.name,
                "status": bot.status,
                "strategy": bot.strategy,
                "pair": bot.current_pair if bot.auto_mode else bot.pair,
                "auto_mode": bot.auto_mode,
                "current_pair": bot.current_pair,
                "profit": float(bot.total_profit),
                "profit_percentage": bot.profit_percentage,
                "trades_count": bot.trades.count(),
                "initial_balance": float(bot.initial_balance),
                "current_balance": float(bot.current_balance),
                "position_size": float(bot.position_size),
                "created_at": bot.created_at.isoformat(),
                "last_trade_at": bot.last_trade_at.isoformat() if bot.last_trade_at else None,
            }
            return Response(bot_data, status=status.HTTP_200_OK)
        except PaperBot.DoesNotExist:
            return Response(
                {"error": "Bot not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Bot detail endpoint error: {e}")
            return Response(
                {"error": "Failed to fetch bot details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BotStartView(APIView):
    """
    Start a specific bot

    POST /api/v1/bots/<bot_id>/start
    """

    def post(self, request, bot_id):
        try:
            bot = PaperBot.objects.get(id=bot_id)
            bot.status = 'running'
            bot.save()
            return Response({"message": f"Bot {bot.name} started successfully"}, status=status.HTTP_200_OK)
        except PaperBot.DoesNotExist:
            return Response(
                {"error": "Bot not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Bot start endpoint error: {e}")
            return Response(
                {"error": "Failed to start bot"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BotStopView(APIView):
    """
    Stop a specific bot

    POST /api/v1/bots/<bot_id>/stop
    """

    def post(self, request, bot_id):
        try:
            bot = PaperBot.objects.get(id=bot_id)
            bot.status = 'stopped'
            bot.save()
            return Response({"message": f"Bot {bot.name} stopped successfully"}, status=status.HTTP_200_OK)
        except PaperBot.DoesNotExist:
            return Response(
                {"error": "Bot not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Bot stop endpoint error: {e}")
            return Response(
                {"error": "Failed to stop bot"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
