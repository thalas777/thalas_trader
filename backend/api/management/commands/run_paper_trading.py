"""
Django management command to run integrated paper trading
Saves all trades to database for frontend display
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import PaperBot, PaperTrade, PaperPosition
import requests
import time
import random
from decimal import Decimal


class Command(BaseCommand):
    help = 'Run paper trading with multi-LLM consensus and save to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=10,
            help='Number of trading iterations'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=15,
            help='Delay between iterations in seconds'
        )
        parser.add_argument(
            '--pairs',
            type=str,
            default='BTC/USD,ETH/USD',
            help='Comma-separated trading pairs'
        )

    def handle(self, *args, **options):
        iterations = options['iterations']
        delay = options['delay']
        pairs = options['pairs'].split(',')

        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS('🤖 Multi-LLM Consensus Paper Trading'))
        self.stdout.write(self.style.SUCCESS(f'{"="*80}\n'))

        # Create or get bots for each pair
        bots = {}
        for pair in pairs:
            bot, created = PaperBot.objects.get_or_create(
                name=f'LLM Consensus Bot - {pair}',
                pair=pair,
                defaults={
                    'strategy': 'LLM_Consensus_Strategy',
                    'status': 'running',
                    'initial_balance': Decimal('10000.00'),
                    'current_balance': Decimal('10000.00'),
                    'position_size': Decimal('0.15'),
                }
            )
            bots[pair] = bot

            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Created bot: {bot.name}'))
            else:
                bot.status = 'running'
                bot.save()
                self.stdout.write(self.style.WARNING(f'♻️  Restarted existing bot: {bot.name}'))

        self.stdout.write(f'\n⏱️  Running {iterations} iterations with {delay}s delay\n')

        # Run trading loop
        for i in range(iterations):
            self.stdout.write(self.style.HTTP_INFO(f'\n📍 Iteration {i+1}/{iterations} - {timezone.now().strftime("%H:%M:%S")}'))
            self.stdout.write('-' * 80)

            for pair in pairs:
                bot = bots[pair]
                self.process_trading_signal(bot, pair)

            # Status update every 3 iterations
            if (i + 1) % 3 == 0:
                self.print_status(bots.values())

            # Wait before next iteration
            if i < iterations - 1:
                self.stdout.write(f'⏳ Waiting {delay} seconds...')
                time.sleep(delay)

        # Final status
        self.stdout.write(self.style.SUCCESS(f'\n\n🏁 Paper Trading Completed!'))
        self.print_status(bots.values())

        # Mark bots as stopped
        for bot in bots.values():
            bot.status = 'stopped'
            bot.save()

    def get_market_data(self, pair):
        """Generate mock market data"""
        base_price = {
            'BTC/USD': 50000,
            'ETH/USD': 3000,
        }.get(pair, 1000)

        price = base_price * (1 + random.uniform(-0.02, 0.02))

        return {
            'price': price,
            'market_data': {
                'rsi': random.uniform(30, 70),
                'macd': random.uniform(-0.02, 0.02),
                'macd_signal': random.uniform(-0.015, 0.015),
                'ema_short': price * 0.99,
                'ema_long': price * 0.98,
                'volume_24h': random.uniform(1000000, 2000000),
                'bb_upper': price * 1.02,
                'bb_middle': price,
                'bb_lower': price * 0.98,
            }
        }

    def get_consensus_signal(self, pair, market_data, current_price):
        """Get consensus signal from API"""
        try:
            url = 'http://localhost:8000/api/v1/strategies/llm-consensus'
            payload = {
                'market_data': market_data,
                'pair': pair,
                'timeframe': '1h',
                'current_price': current_price,
            }

            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error getting consensus: {e}'))
            return None

    def process_trading_signal(self, bot, pair):
        """Process trading signal and execute trade"""
        # Get market data
        market_info = self.get_market_data(pair)
        price = Decimal(str(market_info['price']))

        # Get consensus signal
        signal = self.get_consensus_signal(pair, market_info['market_data'], float(price))
        if not signal:
            return

        decision = signal['decision']
        confidence = Decimal(str(signal['confidence']))

        # Check if we have an open position
        has_position = PaperPosition.objects.filter(bot=bot, pair=pair).exists()

        # Only trade on high confidence
        if confidence < Decimal('0.6'):
            self.stdout.write(f'⚠️  {pair}: Low confidence ({confidence:.2f}), skipping')
            return

        if decision == 'BUY' and not has_position:
            self.execute_buy(bot, pair, price, signal)

        elif decision == 'SELL' and has_position:
            self.execute_sell(bot, pair, price, signal)

        elif decision == 'HOLD':
            status_text = 'in position' if has_position else 'no position'
            self.stdout.write(f'⚪ HOLD {pair} @ ${price:,.2f} ({status_text}, confidence: {confidence:.2f})')

    def execute_buy(self, bot, pair, price, signal):
        """Execute BUY trade"""
        # Calculate trade amount
        trade_value = bot.current_balance * bot.position_size
        amount = trade_value / price

        # Create trade record
        trade = PaperTrade.objects.create(
            bot=bot,
            trade_type='buy',
            pair=pair,
            amount=amount,
            price=price,
            value=trade_value,
            consensus_decision=signal['decision'],
            consensus_confidence=Decimal(str(signal['confidence'])),
            consensus_reasoning=signal['reasoning'],
            provider_votes=signal.get('provider_responses', []),
        )

        # Create position
        PaperPosition.objects.create(
            bot=bot,
            pair=pair,
            amount=amount,
            entry_price=price,
            entry_value=trade_value,
            entry_trade=trade,
        )

        # Update bot balance
        bot.current_balance -= trade_value
        bot.last_trade_at = timezone.now()
        bot.save()

        self.stdout.write(self.style.SUCCESS(
            f'🟢 BUY  {pair} @ ${price:,.2f} | Amount: {amount:.6f} | Value: ${trade_value:,.2f}'
        ))

    def execute_sell(self, bot, pair, price, signal):
        """Execute SELL trade"""
        # Get position
        position = PaperPosition.objects.get(bot=bot, pair=pair)

        # Calculate P&L
        trade_value = position.amount * price
        pnl = trade_value - position.entry_value
        pnl_pct = (pnl / position.entry_value) * 100 if position.entry_value > 0 else Decimal('0')

        # Create trade record
        trade = PaperTrade.objects.create(
            bot=bot,
            trade_type='sell',
            pair=pair,
            amount=position.amount,
            price=price,
            value=trade_value,
            profit=pnl,
            profit_percentage=pnl_pct,
            consensus_decision=signal['decision'],
            consensus_confidence=Decimal(str(signal['confidence'])),
            consensus_reasoning=signal['reasoning'],
            provider_votes=signal.get('provider_responses', []),
        )

        # Update bot
        bot.current_balance += trade_value
        bot.total_profit += pnl
        bot.last_trade_at = timezone.now()
        bot.save()

        # Remove position
        position.delete()

        self.stdout.write(self.style.SUCCESS(
            f'🔴 SELL {pair} @ ${price:,.2f} | P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)'
        ))

    def print_status(self, bots):
        """Print portfolio status"""
        self.stdout.write(f'\n{"="*80}')
        self.stdout.write(self.style.HTTP_INFO('💼 Portfolio Status'))
        self.stdout.write(f'{"="*80}')

        total_balance = Decimal('0')
        total_profit = Decimal('0')
        total_trades = 0

        for bot in bots:
            total_balance += Decimal(str(bot.current_balance))
            total_profit += Decimal(str(bot.total_profit))
            total_trades += bot.trades.count()

            self.stdout.write(f'\n🤖 {bot.name}:')
            self.stdout.write(f'   Balance: ${bot.current_balance:,.2f} | Profit: ${bot.total_profit:,.2f} ({bot.profit_percentage:+.2f}%)')
            self.stdout.write(f'   Trades: {bot.trades.count()} | Status: {bot.status.upper()}')

        self.stdout.write(f'\n📊 TOTAL Portfolio:')
        self.stdout.write(f'   Cash: ${total_balance:,.2f}')
        self.stdout.write(f'   Profit: ${total_profit:,.2f}')
        self.stdout.write(f'   Trades: {total_trades}')
        self.stdout.write(f'{"="*80}\n')
