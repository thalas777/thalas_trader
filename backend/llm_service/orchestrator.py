"""
LLM Orchestrator Service
Handles communication with various LLM providers (Claude, GPT)
for trading signal generation
"""
import json
import logging
from typing import Dict, Any, Optional, List
from django.conf import settings

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)


class LLMOrchestratorError(Exception):
    """Base exception for LLM orchestrator errors"""
    pass


class LLMOrchestrator:
    """
    Orchestrates LLM interactions for trading signal generation
    Supports multiple providers: Anthropic Claude, OpenAI GPT
    """

    TRADING_SIGNAL_PROMPT = """You are an expert trading analyst. Analyze the following market data and provide a trading recommendation.

Market Data:
{market_data}

Current Context:
- Pair: {pair}
- Timeframe: {timeframe}
- Current Price: {current_price}

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

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = provider or settings.DEFAULT_LLM_PROVIDER
        self.model = model or settings.DEFAULT_LLM_MODEL

        # Initialize clients
        self.anthropic_client = None
        self.openai_client = None

        if self.provider == "anthropic":
            if not Anthropic:
                raise LLMOrchestratorError("Anthropic library not installed")
            api_key = settings.ANTHROPIC_API_KEY
            if not api_key:
                raise LLMOrchestratorError("ANTHROPIC_API_KEY not configured")
            self.anthropic_client = Anthropic(api_key=api_key)

        elif self.provider == "openai":
            if not OpenAI:
                raise LLMOrchestratorError("OpenAI library not installed")
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                raise LLMOrchestratorError("OPENAI_API_KEY not configured")
            self.openai_client = OpenAI(api_key=api_key)

        else:
            raise LLMOrchestratorError(f"Unknown provider: {self.provider}")

    def generate_trading_signal(
        self,
        market_data: Dict[str, Any],
        pair: str,
        timeframe: str = "5m",
        current_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate a trading signal using the configured LLM

        Args:
            market_data: Dictionary containing market indicators and data
            pair: Trading pair (e.g., "BTC/USDT")
            timeframe: Timeframe of the data (e.g., "5m", "1h")
            current_price: Current market price

        Returns:
            Dictionary with trading decision and reasoning
        """
        # Format the prompt
        prompt = self.TRADING_SIGNAL_PROMPT.format(
            market_data=self._format_market_data(market_data),
            pair=pair,
            timeframe=timeframe,
            current_price=current_price or "N/A",
        )

        try:
            if self.provider == "anthropic":
                response = self._call_anthropic(prompt)
            elif self.provider == "openai":
                response = self._call_openai(prompt)
            else:
                raise LLMOrchestratorError(f"Unsupported provider: {self.provider}")

            # Parse and validate response
            signal = self._parse_llm_response(response)
            return signal

        except Exception as e:
            logger.error(f"LLM signal generation failed: {e}")
            raise LLMOrchestratorError(f"Signal generation failed: {str(e)}")

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        try:
            message = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise LLMOrchestratorError(f"Anthropic API error: {str(e)}")

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI GPT API"""
        try:
            completion = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.7,
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise LLMOrchestratorError(f"OpenAI API error: {str(e)}")

    def _format_market_data(self, market_data: Dict[str, Any]) -> str:
        """Format market data for LLM consumption"""
        formatted = []
        for key, value in market_data.items():
            if isinstance(value, list):
                # Format list data (e.g., recent candles)
                formatted.append(f"{key}: {value[:5]}... (showing first 5)")
            else:
                formatted.append(f"{key}: {value}")
        return "\n".join(formatted)

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate LLM response"""
        try:
            # Try to extract JSON from response
            # Handle cases where LLM adds extra text
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            signal = json.loads(json_str)

            # Validate required fields
            required_fields = ["decision", "confidence", "reasoning"]
            for field in required_fields:
                if field not in signal:
                    raise ValueError(f"Missing required field: {field}")

            # Validate decision value
            if signal["decision"] not in ["BUY", "SELL", "HOLD"]:
                raise ValueError(f"Invalid decision: {signal['decision']}")

            # Validate confidence range
            if not 0 <= signal["confidence"] <= 1:
                raise ValueError(f"Invalid confidence: {signal['confidence']}")

            return signal

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response}")
            raise LLMOrchestratorError(f"Invalid JSON response: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid LLM response structure: {e}")
            raise LLMOrchestratorError(f"Invalid response: {str(e)}")

    def health_check(self) -> Dict[str, Any]:
        """Check if LLM service is configured and accessible"""
        return {
            "provider": self.provider,
            "model": self.model,
            "configured": bool(
                self.anthropic_client if self.provider == "anthropic"
                else self.openai_client
            ),
        }


# Singleton instance
_orchestrator_instance = None


def get_llm_orchestrator() -> LLMOrchestrator:
    """Get or create LLM orchestrator singleton"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        try:
            _orchestrator_instance = LLMOrchestrator()
        except LLMOrchestratorError as e:
            logger.warning(f"LLM orchestrator initialization failed: {e}")
            # Return None or raise depending on requirements
            raise
    return _orchestrator_instance
