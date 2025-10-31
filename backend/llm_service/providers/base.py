"""
Base Provider System for Multi-LLM Architecture
Defines abstract interfaces and data structures for LLM providers
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Provider operational status"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider"""
    name: str
    model: str
    api_key: str
    max_tokens: int = 1024
    temperature: float = 0.7
    timeout: int = 30
    max_retries: int = 3
    weight: float = 1.0  # Weight for consensus voting
    enabled: bool = True
    base_url: Optional[str] = None  # For custom endpoints
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration"""
        if self.weight < 0 or self.weight > 1:
            raise ValueError("Weight must be between 0 and 1")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if self.timeout < 1:
            raise ValueError("timeout must be positive")


@dataclass
class ProviderResponse:
    """Standardized response from an LLM provider"""
    provider_name: str
    model: str
    decision: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 to 1.0
    reasoning: str
    risk_level: Optional[str] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    raw_response: Optional[str] = None
    latency_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            "provider_name": self.provider_name,
            "model": self.model,
            "decision": self.decision,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
            "suggested_stop_loss": self.suggested_stop_loss,
            "suggested_take_profit": self.suggested_take_profit,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "metadata": self.metadata,
        }


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers

    All provider implementations must inherit from this class and implement
    the required abstract methods. This ensures consistency across different
    LLM providers and enables the multi-LLM consensus system.
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize provider with configuration

        Args:
            config: Provider configuration object
        """
        self.config = config
        self.status = ProviderStatus.ACTIVE
        self._request_count = 0
        self._error_count = 0
        self._total_latency = 0.0
        self._last_error: Optional[Exception] = None
        self._last_request_time: Optional[datetime] = None

        logger.info(f"Initialized {self.config.name} provider with model {self.config.model}")

    @abstractmethod
    async def generate_signal(
        self,
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str,
        current_price: Optional[float] = None,
    ) -> ProviderResponse:
        """
        Generate a trading signal using the LLM

        Args:
            market_data: Dictionary containing market indicators and data
            pair: Trading pair (e.g., "BTC/USDT")
            timeframe: Timeframe of the data (e.g., "5m", "1h")
            current_price: Current market price

        Returns:
            ProviderResponse object with the trading signal

        Raises:
            ProviderError: If signal generation fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is operational

        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate the cost of an API call

        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion

        Returns:
            Estimated cost in USD
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        Get current provider status and statistics

        Returns:
            Dictionary with provider status information
        """
        avg_latency = (
            self._total_latency / self._request_count
            if self._request_count > 0
            else 0
        )

        error_rate = (
            self._error_count / self._request_count
            if self._request_count > 0
            else 0
        )

        return {
            "name": self.config.name,
            "model": self.config.model,
            "status": self.status.value,
            "enabled": self.config.enabled,
            "weight": self.config.weight,
            "requests": self._request_count,
            "errors": self._error_count,
            "error_rate": error_rate,
            "avg_latency_ms": avg_latency,
            "last_request": self._last_request_time.isoformat() if self._last_request_time else None,
            "last_error": str(self._last_error) if self._last_error else None,
        }

    def update_metrics(self, latency_ms: float, error: Optional[Exception] = None):
        """
        Update provider metrics after a request

        Args:
            latency_ms: Request latency in milliseconds
            error: Exception if request failed
        """
        self._request_count += 1
        self._last_request_time = datetime.utcnow()

        if error:
            self._error_count += 1
            self._last_error = error
            logger.warning(f"{self.config.name} error: {error}")
        else:
            self._total_latency += latency_ms

    def set_status(self, status: ProviderStatus):
        """
        Update provider status

        Args:
            status: New provider status
        """
        if self.status != status:
            logger.info(f"{self.config.name} status changed: {self.status.value} -> {status.value}")
            self.status = status

    def is_available(self) -> bool:
        """
        Check if provider is available for requests

        Returns:
            True if provider can accept requests
        """
        return (
            self.config.enabled
            and self.status != ProviderStatus.UNAVAILABLE
            and self.status != ProviderStatus.CIRCUIT_OPEN
        )

    def format_market_data(self, market_data: Dict[str, Any]) -> str:
        """
        Format market data for LLM consumption

        Args:
            market_data: Raw market data dictionary

        Returns:
            Formatted string representation
        """
        formatted = []
        for key, value in market_data.items():
            if isinstance(value, list):
                # Format list data (e.g., recent candles)
                formatted.append(f"{key}: {value[:5]}... (showing first 5)")
            elif isinstance(value, float):
                formatted.append(f"{key}: {value:.4f}")
            else:
                formatted.append(f"{key}: {value}")
        return "\n".join(formatted)

    def build_prompt(
        self,
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str,
        current_price: Optional[float],
    ) -> str:
        """
        Build the standard trading signal prompt

        Args:
            market_data: Market indicators and data
            pair: Trading pair
            timeframe: Data timeframe
            current_price: Current price

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert trading analyst. Analyze the following market data and provide a trading recommendation.

Market Data:
{self.format_market_data(market_data)}

Current Context:
- Pair: {pair}
- Timeframe: {timeframe}
- Current Price: {current_price if current_price else 'N/A'}

Please provide your analysis in the following JSON format:
{{
    "decision": "BUY" or "SELL" or "HOLD",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of your decision",
    "risk_level": "low" or "medium" or "high",
    "suggested_stop_loss": price level (optional),
    "suggested_take_profit": price level (optional)
}}

Respond ONLY with valid JSON, no additional text."""
        return prompt


class ProviderError(Exception):
    """Base exception for provider errors"""

    def __init__(self, provider_name: str, message: str, original_error: Optional[Exception] = None):
        self.provider_name = provider_name
        self.original_error = original_error
        super().__init__(f"{provider_name}: {message}")


class ProviderTimeoutError(ProviderError):
    """Exception raised when provider times out"""
    pass


class ProviderRateLimitError(ProviderError):
    """Exception raised when provider rate limit is hit"""
    pass


class ProviderAuthenticationError(ProviderError):
    """Exception raised when provider authentication fails"""
    pass
