from django.urls import path
from api.views import summary, bots, trades, performance, strategies, risk

urlpatterns = [
    # Summary endpoint
    path("summary", summary.SummaryView.as_view(), name="summary"),

    # Bot management endpoints
    path("bots", bots.BotListView.as_view(), name="bot-list"),
    path("bots/<int:bot_id>", bots.BotDetailView.as_view(), name="bot-detail"),
    path("bots/<int:bot_id>/start", bots.BotStartView.as_view(), name="bot-start"),
    path("bots/<int:bot_id>/stop", bots.BotStopView.as_view(), name="bot-stop"),

    # Trade endpoints
    path("trades", trades.TradeListView.as_view(), name="trade-list"),
    path("trades/<int:trade_id>", trades.TradeDetailView.as_view(), name="trade-detail"),

    # Performance endpoint
    path("performance", performance.PerformanceView.as_view(), name="performance"),

    # LLM Strategy endpoints
    path("strategies/llm", strategies.LLMSignalView.as_view(), name="llm-signal"),
    path("strategies/llm-consensus", strategies.LLMConsensusView.as_view(), name="llm-consensus"),

    # Risk Management endpoints
    path("risk/portfolio", risk.PortfolioRiskView.as_view(), name="portfolio-risk"),
    path("risk/position", risk.PositionRiskView.as_view(), name="position-risk"),
    path("risk/evaluate-signal", risk.SignalRiskView.as_view(), name="signal-risk"),
    path("risk/check-limits", risk.PositionLimitCheckView.as_view(), name="check-limits"),
    path("risk/calculate-stop-loss", risk.StopLossCalculationView.as_view(), name="calculate-stop-loss"),
]
