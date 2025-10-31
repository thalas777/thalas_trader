"""
Data models for Polymarket API client.

This module defines dataclasses for markets, orders, and positions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class OrderSide(str, Enum):
    """Order side (buy/sell)."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    GTC = "GTC"  # Good Till Cancelled
    FOK = "FOK"  # Fill or Kill
    IOC = "IOC"  # Immediate or Cancel


class MarketStatus(str, Enum):
    """Market status."""
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    RESOLVED = "RESOLVED"
    SUSPENDED = "SUSPENDED"


@dataclass
class Market:
    """
    Represents a prediction market on Polymarket.

    Attributes:
        id: Unique market identifier (condition_id or token_id)
        question: The market question
        description: Detailed description of the market
        end_date: Market close/resolution date
        status: Current market status
        yes_price: Current price of YES outcome (0.0-1.0)
        no_price: Current price of NO outcome (0.0-1.0)
        volume: Total trading volume
        liquidity: Available liquidity
        created_at: Market creation timestamp
        outcomes: List of possible outcomes (typically ["YES", "NO"])
        metadata: Additional market metadata
    """
    id: str
    question: str
    description: str
    end_date: datetime
    status: MarketStatus
    yes_price: float
    no_price: float
    volume: float = 0.0
    liquidity: float = 0.0
    created_at: Optional[datetime] = None
    outcomes: List[str] = field(default_factory=lambda: ["YES", "NO"])
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate market data after initialization."""
        if not (0.0 <= self.yes_price <= 1.0):
            raise ValueError(f"yes_price must be between 0.0 and 1.0, got {self.yes_price}")
        if not (0.0 <= self.no_price <= 1.0):
            raise ValueError(f"no_price must be between 0.0 and 1.0, got {self.no_price}")
        if self.volume < 0:
            raise ValueError(f"volume must be non-negative, got {self.volume}")
        if self.liquidity < 0:
            raise ValueError(f"liquidity must be non-negative, got {self.liquidity}")

    @property
    def implied_probability_yes(self) -> float:
        """Get implied probability of YES outcome."""
        return self.yes_price

    @property
    def implied_probability_no(self) -> float:
        """Get implied probability of NO outcome."""
        return self.no_price

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "question": self.question,
            "description": self.description,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status.value,
            "yes_price": self.yes_price,
            "no_price": self.no_price,
            "volume": self.volume,
            "liquidity": self.liquidity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "outcomes": self.outcomes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Market":
        """Create Market from dictionary."""
        # Parse datetime fields
        end_date = data.get("end_date")
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        # Parse status
        status = data.get("status", "ACTIVE")
        if isinstance(status, str):
            status = MarketStatus(status)

        return cls(
            id=data["id"],
            question=data["question"],
            description=data.get("description", ""),
            end_date=end_date,
            status=status,
            yes_price=float(data.get("yes_price", 0.5)),
            no_price=float(data.get("no_price", 0.5)),
            volume=float(data.get("volume", 0.0)),
            liquidity=float(data.get("liquidity", 0.0)),
            created_at=created_at,
            outcomes=data.get("outcomes", ["YES", "NO"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Order:
    """
    Represents an order on Polymarket.

    Attributes:
        id: Unique order identifier
        market_id: Market identifier
        side: Order side (BUY/SELL)
        outcome: Outcome being traded (e.g., "YES", "NO")
        order_type: Type of order (MARKET, LIMIT, etc.)
        status: Current order status
        price: Limit price (for limit orders)
        size: Order size/amount
        filled_size: Amount filled so far
        remaining_size: Amount remaining to be filled
        created_at: Order creation timestamp
        updated_at: Last update timestamp
        metadata: Additional order metadata
    """
    id: str
    market_id: str
    side: OrderSide
    outcome: str
    order_type: OrderType
    status: OrderStatus
    price: float
    size: float
    filled_size: float = 0.0
    remaining_size: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and initialize order data."""
        if self.remaining_size is None:
            self.remaining_size = self.size - self.filled_size

        # Validations
        if not (0.0 <= self.price <= 1.0):
            raise ValueError(f"price must be between 0.0 and 1.0, got {self.price}")
        if self.size <= 0:
            raise ValueError(f"size must be positive, got {self.size}")
        if self.filled_size < 0:
            raise ValueError(f"filled_size must be non-negative, got {self.filled_size}")
        if self.filled_size > self.size:
            raise ValueError(f"filled_size ({self.filled_size}) cannot exceed size ({self.size})")

    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED or self.filled_size >= self.size

    @property
    def fill_percentage(self) -> float:
        """Get fill percentage (0.0-1.0)."""
        if self.size == 0:
            return 0.0
        return self.filled_size / self.size

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "market_id": self.market_id,
            "side": self.side.value,
            "outcome": self.outcome,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "price": self.price,
            "size": self.size,
            "filled_size": self.filled_size,
            "remaining_size": self.remaining_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Order":
        """Create Order from dictionary."""
        # Parse datetime fields
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        # Parse enums
        side = OrderSide(data["side"]) if isinstance(data["side"], str) else data["side"]
        order_type = OrderType(data["order_type"]) if isinstance(data["order_type"], str) else data["order_type"]
        status = OrderStatus(data["status"]) if isinstance(data["status"], str) else data["status"]

        return cls(
            id=data["id"],
            market_id=data["market_id"],
            side=side,
            outcome=data["outcome"],
            order_type=order_type,
            status=status,
            price=float(data["price"]),
            size=float(data["size"]),
            filled_size=float(data.get("filled_size", 0.0)),
            remaining_size=float(data["remaining_size"]) if data.get("remaining_size") else None,
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {}),
        )


@dataclass
class Position:
    """
    Represents a position in a Polymarket market.

    Attributes:
        market_id: Market identifier
        outcome: Outcome held (e.g., "YES", "NO")
        size: Position size (number of shares)
        average_entry_price: Average entry price
        current_price: Current market price
        unrealized_pnl: Unrealized profit/loss
        realized_pnl: Realized profit/loss
        total_pnl: Total profit/loss
        cost_basis: Total cost of position
        market_value: Current market value
        metadata: Additional position metadata
    """
    market_id: str
    outcome: str
    size: float
    average_entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    cost_basis: float = 0.0
    market_value: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate derived values after initialization."""
        if self.cost_basis == 0.0:
            self.cost_basis = self.size * self.average_entry_price
        if self.market_value == 0.0:
            self.market_value = self.size * self.current_price
        if self.unrealized_pnl == 0.0:
            self.unrealized_pnl = self.market_value - self.cost_basis
        if self.total_pnl == 0.0:
            self.total_pnl = self.unrealized_pnl + self.realized_pnl

        # Validations
        if self.size < 0:
            raise ValueError(f"size must be non-negative, got {self.size}")
        if not (0.0 <= self.average_entry_price <= 1.0):
            raise ValueError(f"average_entry_price must be between 0.0 and 1.0, got {self.average_entry_price}")
        if not (0.0 <= self.current_price <= 1.0):
            raise ValueError(f"current_price must be between 0.0 and 1.0, got {self.current_price}")

    @property
    def pnl_percentage(self) -> float:
        """Get PnL percentage."""
        if self.cost_basis == 0:
            return 0.0
        return (self.total_pnl / self.cost_basis) * 100

    @property
    def is_profitable(self) -> bool:
        """Check if position is profitable."""
        return self.total_pnl > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "market_id": self.market_id,
            "outcome": self.outcome,
            "size": self.size,
            "average_entry_price": self.average_entry_price,
            "current_price": self.current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "total_pnl": self.total_pnl,
            "cost_basis": self.cost_basis,
            "market_value": self.market_value,
            "pnl_percentage": self.pnl_percentage,
            "is_profitable": self.is_profitable,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        """Create Position from dictionary."""
        return cls(
            market_id=data["market_id"],
            outcome=data["outcome"],
            size=float(data["size"]),
            average_entry_price=float(data["average_entry_price"]),
            current_price=float(data["current_price"]),
            unrealized_pnl=float(data.get("unrealized_pnl", 0.0)),
            realized_pnl=float(data.get("realized_pnl", 0.0)),
            total_pnl=float(data.get("total_pnl", 0.0)),
            cost_basis=float(data.get("cost_basis", 0.0)),
            market_value=float(data.get("market_value", 0.0)),
            metadata=data.get("metadata", {}),
        )
