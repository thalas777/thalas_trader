"""Trade API Views"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.models import PaperTrade
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

            all_trades = PaperTrade.objects.all()[offset:offset+limit]

            trades = [
                {
                    "trade_id": trade.id,
                    "pair": trade.pair,
                    "type": trade.trade_type,
                    "amount": float(trade.amount),
                    "price": float(trade.price),
                    "profit": float(trade.profit) if trade.profit else None,
                    "timestamp": trade.timestamp.isoformat(),
                    "bot_name": trade.bot.name,
                    "consensus_decision": trade.consensus_decision,
                    "consensus_confidence": float(trade.consensus_confidence),
                }
                for trade in all_trades
            ]

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
