"""Summary API View"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from freqtrade_client.client import get_freqtrade_client
import logging

logger = logging.getLogger(__name__)


class SummaryView(APIView):
    """
    Get portfolio summary statistics

    GET /api/v1/summary
    Returns: {
        "total_profit": float,
        "profit_24h": float,
        "active_bots": int,
        "total_trades": int,
        "win_rate": float
    }
    """

    def get(self, request):
        try:
            client = get_freqtrade_client()
            summary_data = client.get_summary()
            return Response(summary_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Summary endpoint error: {e}")
            return Response(
                {"error": "Failed to fetch summary data"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
