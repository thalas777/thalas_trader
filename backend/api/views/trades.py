"""Trade API Views"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from freqtrade_client.client import get_freqtrade_client
import logging

logger = logging.getLogger(__name__)


class TradeListView(APIView):
    """
    Get list of recent trades

    GET /api/v1/trades?limit=20&offset=0
    Returns: Paginated list of trades
    """

    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 20))
            offset = int(request.query_params.get("offset", 0))

            client = get_freqtrade_client()
            trades = client.get_trades(limit=limit, offset=offset)

            return Response(
                {
                    "trades": trades,
                    "limit": limit,
                    "offset": offset,
                    "count": len(trades),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Trade list endpoint error: {e}")
            return Response(
                {"error": "Failed to fetch trades"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TradeDetailView(APIView):
    """
    Get details of a specific trade

    GET /api/v1/trades/<trade_id>
    """

    def get(self, request, trade_id):
        try:
            client = get_freqtrade_client()
            trades = client.get_trades()
            trade = next((t for t in trades if t.get("trade_id") == trade_id), None)

            if not trade:
                return Response(
                    {"error": "Trade not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(trade, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Trade detail endpoint error: {e}")
            return Response(
                {"error": "Failed to fetch trade details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
