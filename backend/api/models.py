"""
Django models for paper trading system
"""
from django.db import models
from django.utils import timezone
import json


class PaperBot(models.Model):
    """Paper trading bot instance"""

    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    ]

    name = models.CharField(max_length=200)
    strategy = models.CharField(max_length=100, default='LLM_Consensus_Strategy')
    pair = models.CharField(max_length=20, null=True, blank=True)  # Optional when auto_mode=True
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='stopped')

    # Auto-trading mode fields
    auto_mode = models.BooleanField(default=False)  # Enable autonomous pair selection
    current_pair = models.CharField(max_length=20, null=True, blank=True)  # Currently trading pair
    last_scan_at = models.DateTimeField(null=True, blank=True)  # Last market scan timestamp

    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=10000.00)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=10000.00)
    total_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    position_size = models.DecimalField(max_digits=5, decimal_places=4, default=0.15)  # 15%

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_trade_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'paper_bots'
        ordering = ['-created_at']

    def __str__(self):
        if self.auto_mode:
            pair_info = f"AUTO: {self.current_pair}" if self.current_pair else "AUTO"
        else:
            pair_info = self.pair or "No pair"
        return f"{self.name} ({pair_info})"

    @property
    def profit_percentage(self):
        if self.initial_balance > 0:
            return float((self.total_profit / self.initial_balance) * 100)
        return 0.0


class PaperTrade(models.Model):
    """Individual paper trade"""

    TYPE_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]

    bot = models.ForeignKey(PaperBot, on_delete=models.CASCADE, related_name='trades')

    trade_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    pair = models.CharField(max_length=20)

    amount = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=15, decimal_places=2)
    value = models.DecimalField(max_digits=15, decimal_places=2)

    profit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    profit_percentage = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # LLM Consensus data
    consensus_decision = models.CharField(max_length=10)
    consensus_confidence = models.DecimalField(max_digits=5, decimal_places=4)
    consensus_reasoning = models.TextField()

    provider_votes = models.JSONField(default=dict)  # Store provider responses

    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'paper_trades'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.trade_type.upper()} {self.pair} @ ${self.price}"


class PaperPosition(models.Model):
    """Current open positions"""

    bot = models.ForeignKey(PaperBot, on_delete=models.CASCADE, related_name='positions')
    pair = models.CharField(max_length=20)

    amount = models.DecimalField(max_digits=20, decimal_places=8)
    entry_price = models.DecimalField(max_digits=15, decimal_places=2)
    entry_value = models.DecimalField(max_digits=15, decimal_places=2)

    entry_trade = models.ForeignKey(PaperTrade, on_delete=models.SET_NULL, null=True, related_name='opened_position')

    opened_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'paper_positions'
        ordering = ['-opened_at']
        unique_together = ['bot', 'pair']

    def __str__(self):
        return f"{self.bot.name} - {self.pair} position"

    def get_unrealized_pnl(self, current_price: float):
        """Calculate unrealized P&L for open position"""
        current_value = float(self.amount) * current_price
        entry_value = float(self.entry_value)
        pnl = current_value - entry_value
        pnl_pct = (pnl / entry_value) * 100 if entry_value > 0 else 0
        return {
            'current_value': current_value,
            'unrealized_pnl': pnl,
            'unrealized_pnl_pct': pnl_pct
        }
