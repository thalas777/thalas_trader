"""Bot Management API Views"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from freqtrade_client.client import get_freqtrade_client
import logging

logger = logging.getLogger(__name__)


class BotListView(APIView):
    """
    Get list of all bots

    GET /api/v1/bots
    Returns: List of bot objects
    """

    def get(self, request):
        try:
            client = get_freqtrade_client()
            bots = client.get_bots()
            return Response(bots, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Bot list endpoint error: {e}")
            return Response(
                {"error": "Failed to fetch bot list"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BotDetailView(APIView):
    """
    Get details of a specific bot

    GET /api/v1/bots/<bot_id>
    """

    def get(self, request, bot_id):
        try:
            client = get_freqtrade_client()
            bots = client.get_bots()
            bot = next((b for b in bots if b.get("bot_id") == bot_id), None)

            if not bot:
                return Response(
                    {"error": "Bot not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(bot, status=status.HTTP_200_OK)
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
            client = get_freqtrade_client()
            result = client.start_bot(bot_id)
            return Response(result, status=status.HTTP_200_OK)
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
            client = get_freqtrade_client()
            result = client.stop_bot(bot_id)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Bot stop endpoint error: {e}")
            return Response(
                {"error": "Failed to stop bot"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
