"""Performance API View"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from freqtrade_client.client import get_freqtrade_client
import logging

logger = logging.getLogger(__name__)


class PerformanceView(APIView):
    """
    Get historical performance data

    GET /api/v1/performance
    Returns: List of performance data points over time
    """

    def get(self, request):
        try:
            client = get_freqtrade_client()
            performance = client.get_performance()
            return Response(performance, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Performance endpoint error: {e}")
            return Response(
                {"error": "Failed to fetch performance data"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
