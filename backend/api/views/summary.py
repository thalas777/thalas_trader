"""Summary API View"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.models import PaperBot, PaperTrade, PaperPosition
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SummaryView(APIView):
    """
    Get portfolio summary statistics

    GET /api/v1/summary
    Returns: {
        "total_balance": float,
        "cash_balance": float,
        "position_value": float,
        "total_profit": float,
        "profit_percentage": float,
        "profit_24h": float,
        "total_trades": int,
        "win_rate": float,
        "active_bots": int,
        "total_bots": int,
        "open_positions": int
    }
    """

    def get(self, request):
        try:
            # Get all bots
            bots = PaperBot.objects.all()
            total_bots = bots.count()

            # Calculate cash balance (sum of all bot balances)
            cash_balance = bots.aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal('0')

            # Calculate position value (sum of all open positions)
            open_positions = PaperPosition.objects.all()
            position_value = Decimal('0')
            for position in open_positions:
                # Assume current price is similar to entry price for now
                # In a real system, you'd fetch current market price
                position_value += position.amount * position.entry_price

            # Total balance
            total_balance = Decimal(str(cash_balance)) + Decimal(str(position_value))

            # Calculate total profit across all bots
            total_profit = bots.aggregate(Sum('total_profit'))['total_profit__sum'] or Decimal('0')

            # Calculate profit percentage
            # Assume initial total balance was 10000 per bot
            initial_balance = Decimal('10000') * total_bots if total_bots > 0 else Decimal('10000')
            profit_percentage = (float(total_profit) / float(initial_balance) * 100) if initial_balance > 0 else 0

            # Calculate 24h profit
            yesterday = timezone.now() - timedelta(days=1)
            trades_24h = PaperTrade.objects.filter(timestamp__gte=yesterday, profit__isnull=False)
            profit_24h = trades_24h.aggregate(Sum('profit'))['profit__sum'] or Decimal('0')

            # Count active bots
            active_bots = bots.filter(status='running').count()

            # Total trades
            total_trades = PaperTrade.objects.count()

            # Win rate (trades with profit > 0)
            profitable_trades = PaperTrade.objects.filter(profit__gt=0).count()
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0

            summary_data = {
                "total_balance": float(total_balance),
                "cash_balance": float(cash_balance),
                "position_value": float(position_value),
                "total_profit": float(total_profit),
                "profit_percentage": round(profit_percentage, 2),
                "profit_24h": float(profit_24h),
                "total_trades": total_trades,
                "win_rate": round(win_rate, 2),
                "active_bots": active_bots,
                "total_bots": total_bots,
                "open_positions": open_positions.count()
            }

            return Response(summary_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Summary endpoint error: {e}")
            return Response(
                {"error": "Failed to fetch summary data"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
