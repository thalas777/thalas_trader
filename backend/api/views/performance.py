"""Performance API View"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.models import PaperBot, PaperTrade
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PerformanceView(APIView):
    """
    Get historical performance data

    GET /api/v1/performance
    Returns: {
        "equity_curve": [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "balance": 10000.0,
                "profit": 0.0
            },
            ...
        ]
    }
    """

    def get(self, request):
        try:
            # Get all trades ordered by timestamp
            trades = PaperTrade.objects.all().order_by('timestamp')

            # Get initial balance from all bots
            bots = PaperBot.objects.all()
            initial_balance = sum([float(bot.initial_balance) for bot in bots])

            # Build equity curve from trades
            equity_curve = []
            cumulative_profit = Decimal('0')

            # Add starting point
            if trades.exists():
                first_trade_time = trades.first().timestamp.isoformat()
                equity_curve.append({
                    "timestamp": first_trade_time,
                    "balance": initial_balance,
                    "profit": 0.0
                })

            # Process each trade
            for trade in trades:
                if trade.profit:
                    cumulative_profit += Decimal(str(trade.profit))

                current_balance = initial_balance + float(cumulative_profit)

                equity_curve.append({
                    "timestamp": trade.timestamp.isoformat(),
                    "balance": round(current_balance, 2),
                    "profit": round(float(cumulative_profit), 2)
                })

            # If no trades, return empty curve
            if not equity_curve:
                equity_curve = []

            return Response({"equity_curve": equity_curve}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Performance endpoint error: {e}")
            return Response(
                {"error": "Failed to fetch performance data"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
