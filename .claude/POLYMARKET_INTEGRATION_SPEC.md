# POLYMARKET INTEGRATION SPECIFICATION
## Comprehensive Technical Documentation for CLOB API Integration

**Document Version**: 1.0
**Created**: 2025-10-31
**Author**: Polymarket-Research-Agent
**Status**: COMPLETE
**Target Implementation**: Thalas Trader - Wave 2, Phase 3

---

## TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
5. [Data Models](#data-models)
6. [Order Placement Flow](#order-placement-flow)
7. [WebSocket Real-Time Data](#websocket-real-time-data)
8. [Rate Limits](#rate-limits)
9. [Costs and Fees](#costs-and-fees)
10. [Python SDK Integration](#python-sdk-integration)
11. [Implementation Checklist](#implementation-checklist)
12. [References](#references)

---

## EXECUTIVE SUMMARY

Polymarket is a decentralized prediction market platform built on Polygon (Chain ID: 137) that uses a hybrid-decentralized Central Limit Order Book (CLOB) architecture. The CLOB provides off-chain order matching with on-chain settlement, enabling non-custodial trading of binary outcome tokens.

### Key Features
- **Hybrid-Decentralized**: Off-chain matching + on-chain settlement
- **Non-Custodial**: Users maintain control of funds via private keys
- **Zero Platform Fees**: No direct trading fees (liquidity provider spreads apply)
- **EIP-712 Signatures**: Orders signed with Ethereum wallet standards
- **Multi-Protocol Support**: REST API + WebSocket feeds
- **Official Python SDK**: `py-clob-client` for easy integration

### Use Cases for Thalas Trader
- Multi-market trading (crypto + prediction markets)
- LLM-based prediction signal generation
- Consensus-based prediction market analysis
- Portfolio diversification with binary outcomes
- Risk management across correlated markets

---

## ARCHITECTURE OVERVIEW

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    POLYMARKET ECOSYSTEM                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────┐      ┌───────────────┐                   │
│  │  CLOB API     │      │  Gamma API    │                   │
│  │  (Trading)    │      │  (Markets)    │                   │
│  │  REST + WSS   │      │  REST Only    │                   │
│  └───────┬───────┘      └───────┬───────┘                   │
│          │                      │                            │
│          │                      │                            │
│  ┌───────▼──────────────────────▼───────┐                   │
│  │     Exchange Contract (Polygon)      │                   │
│  │     - Atomic Swaps (CTF Tokens)      │                   │
│  │     - On-Chain Settlement            │                   │
│  │     - Non-Custodial Execution        │                   │
│  └──────────────────────────────────────┘                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Concepts

1. **CLOB (Central Limit Order Book)**
   - Operator provides off-chain matching/ordering services
   - Settlement happens on-chain via smart contracts
   - Operator cannot set prices or execute unauthorized trades

2. **Outcome Tokens (CTF ERC1155)**
   - Binary outcome tokens (YES/NO)
   - Traded against collateral assets (USDC as ERC20)
   - Atomic swaps between tokens and collateral

3. **Order Structure**
   - EIP-712 signed structured data
   - Maker/taker model with taker price improvements
   - On-chain cancellation capability by users

4. **Settlement**
   - Non-custodial execution
   - Smart contract enforcement
   - User maintains private key control

### Security
- **Audited by ChainSecurity**
- **Open Source**: Contracts and documentation on GitHub
- **Non-Custodial**: Operator never controls user funds

---

## AUTHENTICATION

Polymarket uses a **two-tier authentication system** combining Ethereum wallet signatures with API credentials.

### Authentication Tiers

#### L1: Private Key Authentication (Wallet-Based)
- **Purpose**: Critical operations (order signing, API key management)
- **Method**: EIP-712 signature generation
- **Chain**: Polygon (Chain ID: 137)
- **Required Headers**:
  - `POLY_ADDRESS`: User's Ethereum address
  - `POLY_SIGNATURE`: EIP-712 signature
  - `POLY_TIMESTAMP`: Unix timestamp (milliseconds)
  - `POLY_NONCE`: Unique nonce for signature

**EIP-712 Signature Domain**:
```json
{
  "name": "ClobAuthDomain",
  "version": "1",
  "chainId": 137
}
```

**Signature Message Structure**:
```json
{
  "address": "0x...",
  "timestamp": 1698765432000,
  "nonce": 0,
  "message": "This message attests that I control the given wallet"
}
```

#### L2: API Key Authentication (Request-Based)
- **Purpose**: API request authentication
- **Method**: HMAC-based credentials
- **Required Headers**:
  - `POLY_ADDRESS`: User's Ethereum address
  - `POLY_SIGNATURE`: HMAC signature for request
  - `POLY_TIMESTAMP`: Unix timestamp (milliseconds)
  - `POLY_API_KEY`: UUID key identifier
  - `POLY_PASSPHRASE`: API passphrase

**Credentials**:
1. **API Key**: UUID identifier
2. **API Secret**: Used locally for HMAC signature generation
3. **API Passphrase**: Sent with requests for encryption/decryption

### Authentication Flow

```
┌──────────────────────────────────────────────────────────┐
│ Step 1: Generate L1 Signature (One-Time Setup)          │
├──────────────────────────────────────────────────────────┤
│ 1. Create EIP-712 signature with private key            │
│ 2. POST /auth/api-key with L1 headers                   │
│ 3. Server generates API credentials deterministically   │
│ 4. Receive: API_KEY, API_SECRET, API_PASSPHRASE         │
│ 5. Store credentials securely                           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Step 2: Use L2 Credentials for API Calls                │
├──────────────────────────────────────────────────────────┤
│ 1. Generate HMAC signature using API_SECRET             │
│ 2. Include L2 headers in API requests                   │
│ 3. Server validates signature and passphrase            │
│ 4. Execute API operation                                │
└──────────────────────────────────────────────────────────┘
```

### API Key Management Endpoints

| Operation | Endpoint | Auth Level | Description |
|-----------|----------|------------|-------------|
| Create | `POST /auth/api-key` | L1 | Generate new API credentials |
| Derive | `POST /auth/derive-api-key` | L1 | Recover existing credentials for address/nonce |
| Retrieve | `GET /auth/api-keys` | L2 | List all API keys for address |
| Delete | `DELETE /auth/api-key` | L2 | Revoke specific credentials |

### Wallet Types and Signature Types

Polymarket supports three signature types for different wallet implementations:

| Signature Type | Value | Wallet Type | Use Case |
|----------------|-------|-------------|----------|
| EOA | 0 | Standard wallets | MetaMask, hardware wallets, private key |
| POLY_PROXY | 1 | Email/Magic wallets | Email-based authentication |
| POLY_GNOSIS_SAFE | 2 | Browser proxy wallets | Multi-sig, smart contract wallets |

**Important**: For proxy wallets (types 1 and 2), you must specify a **funder address** (the account holding funds) separate from the signing key.

### Python SDK Authentication Example

```python
from py_clob_client.client import ClobClient

# Initialize client with private key
client = ClobClient(
    host="https://clob.polymarket.com",
    key="<your-private-key>",
    chain_id=137,
    signature_type=0,  # 0=EOA, 1=Email/Magic, 2=Browser
    funder="<funder-address>"  # Required for signature_type 1 or 2
)

# Create or derive API credentials
creds = client.create_or_derive_api_creds()
client.set_api_creds(creds)

# Now authenticated for all API operations
```

---

## API ENDPOINTS

Polymarket provides multiple API services for different purposes.

### Base URLs

| Service | Base URL | Purpose |
|---------|----------|---------|
| CLOB REST API | `https://clob.polymarket.com/` | Trading, orders, market data |
| Data API | `https://data-api.polymarket.com/` | User data, holdings, on-chain activities |
| Gamma Markets API | `https://gamma-api.polymarket.com/` | Market metadata, categorization, volume |
| CLOB WebSocket | `wss://ws-subscriptions-clob.polymarket.com/ws/` | Real-time order/trade updates |
| Real-Time Data Socket | `wss://ws-live-data.polymarket.com` | Real-time price/comment streams |

### CLOB API Endpoint Categories

The CLOB API provides comprehensive trading and market data functionality:

#### 1. Authentication Endpoints
- `POST /auth/api-key` - Create API credentials
- `POST /auth/derive-api-key` - Derive existing credentials
- `GET /auth/api-keys` - List API keys
- `DELETE /auth/api-key` - Revoke credentials

#### 2. Market Data Endpoints
- Get order book for token
- Get midpoint price
- Get spread
- Get last trade price
- Get market prices

#### 3. Order Management Endpoints
- `POST /order` - Place single order
- `POST /orders` - Place multiple orders (batch)
- `GET /order` - Get specific order details
- `GET /orders` - Get active orders
- `GET /orders/scored` - Check order reward scoring
- `DELETE /order` - Cancel order
- `DELETE /orders` - Cancel multiple orders
- Get on-chain order info

#### 4. Trade Endpoints
- `GET /trades` - Get trade history
- `GET /trades/user` - Get user's trade history

#### 5. Balance and Position Endpoints
- Get balances
- Get positions
- Get ledger/transaction history

### Gamma Markets API Endpoints

**Base URL**: `https://gamma-api.polymarket.com`

The Gamma API indexes on-chain market data and provides additional market metadata.

#### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/markets` | GET | List all markets with metadata |
| `/markets/{market_id}` | GET | Get specific market details |
| `/events` | GET | List all events |
| `/events/{event_id}` | GET | Get specific event details |

#### Query Parameters for `/markets`

| Parameter | Type | Description |
|-----------|------|-------------|
| `active` | boolean | Filter for active markets |
| `closed` | boolean | Filter for closed markets |
| `archived` | boolean | Filter for archived markets |
| `limit` | integer | Number of results per page (default: 100) |
| `offset` | integer | Pagination offset |

#### Market Response Fields

The Gamma API returns comprehensive market metadata:

```json
{
  "id": "string",
  "question": "string",
  "description": "string",
  "outcomes": ["YES", "NO"],
  "outcome_prices": ["0.45", "0.55"],
  "volume": "string",
  "active": true,
  "closed": false,
  "archived": false,
  "market_slug": "string",
  "condition_id": "string",
  "tokens": [
    {
      "token_id": "string",
      "outcome": "YES",
      "price": "0.45"
    }
  ],
  "created_at": "2025-01-01T00:00:00Z",
  "end_date": "2025-12-31T23:59:59Z",
  "category": "Politics",
  "tags": ["election", "2024"]
}
```

### Data API Endpoints

**Base URL**: `https://data-api.polymarket.com/`

#### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/positions` | GET | Get user positions |
| `/holdings` | GET | Get user token holdings |
| `/pnl` | GET | Get profit/loss data |

---

## DATA MODELS

### Order Data Model

Orders in Polymarket are EIP-712 signed structured data.

#### Order Structure (Python)

```python
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY, SELL

order = OrderArgs(
    token_id="string",        # Token ID from market
    price=0.50,               # Price per share (0.0-1.0)
    size=100.0,               # Number of shares
    side=BUY,                 # BUY or SELL
    fee_rate_bps=0,           # Fee rate in basis points (default: 0)
    nonce=0,                  # Unique nonce
    expiration=0              # Expiration timestamp (0 = no expiry)
)
```

#### Market Order Structure (Python)

```python
from py_clob_client.clob_types import MarketOrderArgs, OrderType

market_order = MarketOrderArgs(
    token_id="string",        # Token ID from market
    amount=50.0,              # Dollar amount (USDC)
    side=BUY,                 # BUY or SELL
    order_type=OrderType.FOK  # FOK (Fill or Kill)
)
```

#### Order Types

| Order Type | Code | Description |
|------------|------|-------------|
| Good Till Cancel | GTC | Order remains active until filled or canceled |
| Fill or Kill | FOK | Order must be filled immediately and completely or canceled |
| Fill and Kill | FAK | Order fills as much as possible immediately, cancels remainder |
| Good Till Date | GTD | Order expires at specified timestamp |

### Market Data Model

Markets are represented with comprehensive metadata from the Gamma API.

#### Market Object

```json
{
  "id": "0x123...",
  "question": "Will Bitcoin reach $100,000 by end of 2025?",
  "description": "This market resolves YES if Bitcoin...",
  "outcomes": ["YES", "NO"],
  "outcome_prices": ["0.35", "0.65"],
  "outcomePrices": ["0.35", "0.65"],
  "volume": "1500000.00",
  "active": true,
  "closed": false,
  "archived": false,
  "new": false,
  "featured": false,
  "restricted": false,
  "liquidity": "50000.00",
  "market_slug": "bitcoin-100k-2025",
  "condition_id": "0xabc...",
  "question_id": "0xdef...",
  "tokens": [
    {
      "token_id": "123456789",
      "outcome": "YES",
      "price": "0.35",
      "winner": false
    },
    {
      "token_id": "987654321",
      "outcome": "NO",
      "price": "0.65",
      "winner": false
    }
  ],
  "clob_token_ids": ["123456789", "987654321"],
  "minimum_order_size": "1.0",
  "minimum_tick_size": "0.01",
  "neg_risk": false,
  "maker_base_fee": 0,
  "taker_base_fee": 0,
  "created_at": "2025-01-01T00:00:00Z",
  "end_date_iso": "2025-12-31T23:59:59Z",
  "game_start_time": null,
  "seconds_delay": 0,
  "icon": "https://...",
  "category": "Crypto",
  "tags": ["cryptocurrency", "bitcoin", "price-prediction"],
  "umaBond": "5000",
  "umaReward": "500"
}
```

### Position Data Model

User positions include detailed P&L information.

#### Position Object

```json
{
  "asset": "string",              // Token ID
  "token_id": "string",           // Token ID
  "condition_id": "string",       // Market condition ID
  "market_id": "string",          // Market ID
  "size": "100.0",                // Position size (shares)
  "avg_price": "0.50",            // Average entry price
  "initial_value": "50.00",       // Initial value (USDC)
  "current_value": "65.00",       // Current value (USDC)
  "cash_pnl": "15.00",            // Cash profit/loss (USDC)
  "percent_pnl": "30.0",          // Percent profit/loss
  "total_bought": "100.0",        // Total shares bought
  "total_sold": "0.0",            // Total shares sold
  "realized_pnl": "0.00",         // Realized P&L
  "unrealized_pnl": "15.00",      // Unrealized P&L
  "current_price": "0.65",        // Current market price
  "title": "Bitcoin reaches $100K",
  "outcome": "YES",
  "outcome_index": 0
}
```

### Order Book Data Model

Order books provide market depth information.

#### Order Book Structure

```json
{
  "asset_id": "string",
  "market_id": "string",
  "bids": [
    {
      "price": "0.50",
      "size": "1000.0"
    },
    {
      "price": "0.49",
      "size": "2000.0"
    }
  ],
  "asks": [
    {
      "price": "0.51",
      "size": "800.0"
    },
    {
      "price": "0.52",
      "size": "1500.0"
    }
  ],
  "timestamp": 1698765432000,
  "hash": "0x..."
}
```

### Trade Data Model

Trade records capture executed transactions.

#### Trade Object

```json
{
  "id": "string",
  "market_id": "string",
  "asset_id": "string",
  "side": "BUY",
  "price": "0.50",
  "size": "100.0",
  "fee_rate_bps": "0",
  "timestamp": 1698765432000,
  "trader_address": "0x...",
  "maker_address": "0x...",
  "taker_address": "0x...",
  "match_time": 1698765432000,
  "type": "LIMIT"
}
```

---

## ORDER PLACEMENT FLOW

### Prerequisites

Before placing orders, EOA wallet users must set **token allowances** for USDC and Conditional Tokens across three exchange contracts. This is a one-time operation per wallet.

**Note**: Email/Magic wallet users skip this step (automatic approvals).

### Order Placement Steps

```
┌────────────────────────────────────────────────────────────┐
│ 1. Market Discovery                                        │
├────────────────────────────────────────────────────────────┤
│ - Fetch markets from Gamma API                            │
│ - Identify target market and token_id                     │
│ - Get market parameters (tick_size, neg_risk, etc.)       │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 2. Price Discovery (Optional)                             │
├────────────────────────────────────────────────────────────┤
│ - Get order book for token                                │
│ - Get midpoint price                                      │
│ - Determine optimal entry price                           │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 3. Create Order                                            │
├────────────────────────────────────────────────────────────┤
│ - Build OrderArgs or MarketOrderArgs                      │
│ - Sign order with EIP-712 signature                       │
│ - Client library handles signing automatically            │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 4. Submit Order                                            │
├────────────────────────────────────────────────────────────┤
│ - POST /order with signed order                           │
│ - Specify order type (GTC, FOK, FAK, GTD)                 │
│ - Receive order ID and status                             │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 5. Monitor Order                                           │
├────────────────────────────────────────────────────────────┤
│ - Track order status via WebSocket or REST API            │
│ - Check fills and partial fills                           │
│ - Monitor position updates                                │
└────────────────────────────────────────────────────────────┘
```

### Python Code Examples

#### Example 1: Limit Order (GTC)

```python
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

# Initialize client
client = ClobClient(
    host="https://clob.polymarket.com",
    key="<your-private-key>",
    chain_id=137,
    signature_type=0  # EOA wallet
)

# Set API credentials
creds = client.create_or_derive_api_creds()
client.set_api_creds(creds)

# Get market data
markets = client.get_simplified_markets()
token_id = markets[0]['tokens'][0]['token_id']

# Get current order book
order_book = client.get_order_book(token_id)
print(f"Best bid: {order_book['bids'][0]['price']}")
print(f"Best ask: {order_book['asks'][0]['price']}")

# Create limit order
order = OrderArgs(
    token_id=token_id,
    price=0.50,      # Limit price
    size=100.0,      # 100 shares
    side=BUY
)

# Sign and submit order
signed_order = client.create_order(order)
response = client.post_order(signed_order, OrderType.GTC)

print(f"Order placed: {response}")
print(f"Order ID: {response['orderID']}")
```

#### Example 2: Market Order (FOK)

```python
from py_clob_client.clob_types import MarketOrderArgs, OrderType

# Create market order (fill or kill)
market_order = MarketOrderArgs(
    token_id=token_id,
    amount=50.0,     # $50 USDC
    side=BUY,
    order_type=OrderType.FOK
)

# Sign and submit market order
signed_market_order = client.create_market_order(market_order)
response = client.post_order(signed_market_order, OrderType.FOK)

print(f"Market order executed: {response}")
```

#### Example 3: Cancel Order

```python
# Cancel specific order
order_id = "0x123..."
cancel_response = client.cancel(order_id)
print(f"Order canceled: {cancel_response}")

# Cancel all orders
cancel_all_response = client.cancel_all()
print(f"All orders canceled: {cancel_all_response}")
```

#### Example 4: Get Active Orders

```python
from py_clob_client.clob_types import OpenOrderParams

# Get all open orders
params = OpenOrderParams(market=None)  # None = all markets
orders = client.get_orders(params)

for order in orders:
    print(f"Order ID: {order['id']}")
    print(f"Token: {order['asset_id']}")
    print(f"Side: {order['side']}")
    print(f"Price: {order['original_size']}")
    print(f"Size: {order['size']}")
    print(f"Status: {order['status']}")
    print("---")
```

#### Example 5: Get Positions

```python
# Get current positions
positions = client.get_positions()

for position in positions:
    print(f"Market: {position['title']}")
    print(f"Outcome: {position['outcome']}")
    print(f"Size: {position['size']}")
    print(f"P&L: {position['cash_pnl']} USDC")
    print(f"P&L %: {position['percent_pnl']}%")
    print("---")
```

### Order Matching Logic

Polymarket uses a **maker/taker model** with price improvements:

1. **Maker**: User placing an order on the book
2. **Taker**: User filling an existing order
3. **Price Improvement**: Takers may receive better prices than posted

All orders are limit orders internally. Market orders are implemented as marketable limit orders that execute immediately.

---

## WEBSOCKET REAL-TIME DATA

Polymarket provides two WebSocket services for real-time data streaming.

### WebSocket Services

| Service | URL | Purpose |
|---------|-----|---------|
| CLOB WSS | `wss://ws-subscriptions-clob.polymarket.com/ws/` | Order/trade updates |
| Real-Time Data | `wss://ws-live-data.polymarket.com` | Price/comment streams |

### Available Channels

#### 1. User Channel
**Authentication**: Required (L2 credentials)
**Purpose**: Personal order and trade updates

**Subscription Message**:
```json
{
  "auth": {
    "apiKey": "your-api-key",
    "secret": "your-api-secret",
    "passphrase": "your-passphrase"
  },
  "markets": [],           // Empty = all markets
  "assets_ids": [],        // Empty = all assets
  "type": "USER"
}
```

**Event Types**:
- `order_created` - New order placed
- `order_matched` - Order matched (filled)
- `order_canceled` - Order canceled
- `trade_executed` - Trade executed

#### 2. Market Channel
**Authentication**: Not required
**Purpose**: Public market data updates

**Subscription Message**:
```json
{
  "markets": ["0x123..."],      // Market condition IDs
  "assets_ids": ["456789"],     // Token IDs
  "type": "MARKET"
}
```

**Event Types**:
- `book` - Order book update
- `price_change` - Price changed
- `tick_size_change` - Tick size changed
- `last_trade_price` - Last trade price update

### WebSocket Message Format

#### Order Update Event

```json
{
  "event_type": "order_matched",
  "timestamp": 1698765432000,
  "order": {
    "id": "0x123...",
    "market_id": "0xabc...",
    "asset_id": "456789",
    "side": "BUY",
    "price": "0.50",
    "size": "100.0",
    "filled": "100.0",
    "status": "MATCHED"
  }
}
```

#### Price Change Event

```json
{
  "event_type": "price_change",
  "timestamp": 1698765432000,
  "asset_id": "456789",
  "market_id": "0xabc...",
  "price": "0.52",
  "mid_price": "0.515",
  "best_bid": "0.51",
  "best_ask": "0.52"
}
```

### Python WebSocket Client (Community)

**Note**: Polymarket provides an official TypeScript WebSocket client. Python users can use third-party libraries or implement WebSocket connections manually.

```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f"Received: {data}")

def on_open(ws):
    subscription = {
        "type": "MARKET",
        "markets": ["0x123..."],
        "assets_ids": []
    }
    ws.send(json.dumps(subscription))

ws = websocket.WebSocketApp(
    "wss://ws-subscriptions-clob.polymarket.com/ws/",
    on_message=on_message,
    on_open=on_open
)

ws.run_forever()
```

---

## RATE LIMITS

Polymarket enforces rate limits using **Cloudflare's throttling system**. Requests over the limit are delayed/queued rather than immediately rejected.

### Rate Limit Tiers

#### General CLOB API
- **General endpoints**: 5,000 requests / 10 seconds
- **OK endpoints**: 50 requests / 10 seconds

#### Market Data Queries
- **General**: 80-200 requests / 10 seconds
- **Varies by endpoint**

#### Balance Operations
- **General**: 20-125 requests / 10 seconds

#### Ledger Endpoints
- **General**: 150-300 requests / 10 seconds

#### Trading Endpoints
- **Burst allowance**: 240-2,400 requests / 10 seconds
- **Sustained rate**: 5-40 requests / second

#### Data API
- **General**: 200 requests / 10 seconds
- **Alternative endpoint**: 1,200 requests / minute
  - **Violation penalty**: 10-minute block
- **Trades**: 75 requests / 10 seconds

#### Gamma Markets API
- **General**: 750 requests / 10 seconds
- **Comments/Events/Tags**: 100 requests / 10 seconds
- **Markets**: 125 requests / 10 seconds
- **Search**: 300 requests / 10 seconds

#### Other Services
- **Relayer**: 15 requests / minute
- **User P&L**: 100 requests / 10 seconds

### Rate Limit Best Practices

1. **Use WebSockets for real-time data** instead of polling
2. **Batch operations** where possible (e.g., batch order placement)
3. **Implement exponential backoff** for retries
4. **Cache market data** locally (markets don't change frequently)
5. **Monitor rate limit headers** in responses
6. **Use sliding window calculations** for burst limits

### Throttling Behavior

When rate limits are exceeded:
- Requests are **queued** not rejected
- Temporary bursts above sustained rates allowed
- Sliding time windows used for calculations
- Some endpoints have separate burst and sustained limits

---

## COSTS AND FEES

### Platform Fees

**Polymarket Platform Fees**: **0% (FREE)**

Polymarket does not charge trading fees. This is a key differentiator from traditional exchanges.

### Other Costs

#### 1. Liquidity Provider Fees
- **Not charged by Polymarket**
- Embedded in bid-ask spreads
- Liquidity providers earn from spreads
- **Estimated impact**: ~0.25-2% depending on market liquidity

#### 2. Network Fees (Polygon Gas)
- **Blockchain**: Polygon (low gas fees)
- **Typical cost**: $0.001 - $0.01 per transaction
- **Paid in**: MATIC (auto-converted from USDC for email wallets)

#### 3. On-Ramp/Off-Ramp Fees
- **USDC deposits**: Free (via Polymarket)
- **Coinbase/MoonPay**: May charge 1-3% fees
- **Bank transfers**: Vary by provider

#### 4. Maker/Taker Fees
- **Maker fee**: 0 basis points (0%)
- **Taker fee**: 0 basis points (0%)
- **Volume tiers**: Not applicable (always 0%)

### Cost Comparison

| Exchange Type | Trading Fee | Polymarket |
|---------------|-------------|------------|
| Centralized Crypto | 0.1-0.5% | 0% |
| Decentralized Crypto | 0.3-1.0% | 0% |
| Prediction Markets | 2-5% | 0% |

### Total Cost Estimate (Per Trade)

| Cost Component | Amount |
|----------------|--------|
| Trading fee | $0 |
| Spread (est.) | 0.5-2% of trade |
| Polygon gas | $0.001-$0.01 |
| **Total** | **~0.5-2% + minimal gas** |

### API Usage Costs

- **REST API**: Free (subject to rate limits)
- **WebSocket**: Free (subject to rate limits)
- **Gamma API**: Free (read-only, public data)
- **Data API**: Free (subject to rate limits)

---

## PYTHON SDK INTEGRATION

### Installation

```bash
pip install py-clob-client
```

**Requirements**:
- Python 3.9+
- Dependencies: web3, eth-account, requests, etc. (auto-installed)

### Quick Start

#### 1. Read-Only Client (No Authentication)

```python
from py_clob_client.client import ClobClient

# Initialize without authentication
client = ClobClient("https://clob.polymarket.com")

# Get server status
status = client.get_server_time()
print(f"Server time: {status}")

# Get markets (no auth required)
markets = client.get_simplified_markets()
for market in markets[:5]:
    print(f"{market['question']}")
```

#### 2. Trading Client (Authenticated)

```python
from py_clob_client.client import ClobClient

# Initialize with private key
client = ClobClient(
    host="https://clob.polymarket.com",
    key="<your-private-key>",  # Ethereum private key (64 hex chars)
    chain_id=137,              # Polygon mainnet
    signature_type=0,          # 0=EOA, 1=Email/Magic, 2=Browser
    funder=None                # Required for signature_type 1 or 2
)

# Create/derive API credentials
creds = client.create_or_derive_api_creds()
client.set_api_creds(creds)

# Save credentials for future use
print(f"API Key: {creds['apiKey']}")
print(f"API Secret: {creds['secret']}")
print(f"Passphrase: {creds['passphrase']}")
```

#### 3. Market Discovery

```python
# Get all markets
markets = client.get_simplified_markets()

# Filter markets
active_markets = [m for m in markets if m['active']]
crypto_markets = [m for m in markets if 'crypto' in m['question'].lower()]

# Get specific market details
market = markets[0]
print(f"Question: {market['question']}")
print(f"Tokens: {market['tokens']}")

# Get token ID for trading
token_id = market['tokens'][0]['token_id']
```

#### 4. Price Discovery

```python
# Get order book
order_book = client.get_order_book(token_id)
print(f"Best bid: {order_book['bids'][0]['price']}")
print(f"Best ask: {order_book['asks'][0]['price']}")

# Get midpoint price
midpoint = client.get_midpoint(token_id)
print(f"Midpoint: {midpoint}")

# Get spread
spread = client.get_spread(token_id)
print(f"Spread: {spread}")

# Get price for specific side
buy_price = client.get_price(token_id, "BUY")
sell_price = client.get_price(token_id, "SELL")
```

#### 5. Order Placement

```python
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

# Create limit order
order = OrderArgs(
    token_id=token_id,
    price=0.50,
    size=100.0,
    side=BUY
)

# Sign order
signed_order = client.create_order(order)

# Submit order
response = client.post_order(signed_order, OrderType.GTC)
print(f"Order ID: {response['orderID']}")
```

#### 6. Order Management

```python
from py_clob_client.clob_types import OpenOrderParams

# Get all open orders
params = OpenOrderParams(market=None)
orders = client.get_orders(params)

# Cancel specific order
order_id = orders[0]['id']
client.cancel(order_id)

# Cancel all orders
client.cancel_all()
```

#### 7. Position Monitoring

```python
# Get current positions
positions = client.get_positions()

for position in positions:
    print(f"Market: {position['title']}")
    print(f"Size: {position['size']}")
    print(f"P&L: ${position['cash_pnl']}")
    print(f"ROI: {position['percent_pnl']}%")
    print("---")
```

### Complete Trading Bot Example

```python
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL
import time

class PolymarketBot:
    def __init__(self, private_key: str, signature_type: int = 0, funder: str = None):
        self.client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=137,
            signature_type=signature_type,
            funder=funder
        )

        # Authenticate
        creds = self.client.create_or_derive_api_creds()
        self.client.set_api_creds(creds)

    def find_market(self, keyword: str):
        """Find markets matching keyword"""
        markets = self.client.get_simplified_markets()
        matches = [m for m in markets if keyword.lower() in m['question'].lower()]
        return matches

    def get_market_price(self, token_id: str):
        """Get current market price"""
        order_book = self.client.get_order_book(token_id)
        if order_book['bids'] and order_book['asks']:
            bid = float(order_book['bids'][0]['price'])
            ask = float(order_book['asks'][0]['price'])
            mid = (bid + ask) / 2
            return {'bid': bid, 'ask': ask, 'mid': mid, 'spread': ask - bid}
        return None

    def place_limit_order(self, token_id: str, price: float, size: float, side):
        """Place a limit order"""
        order = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side
        )
        signed = self.client.create_order(order)
        return self.client.post_order(signed, OrderType.GTC)

    def place_market_order(self, token_id: str, amount: float, side):
        """Place a market order"""
        order = MarketOrderArgs(
            token_id=token_id,
            amount=amount,
            side=side,
            order_type=OrderType.FOK
        )
        signed = self.client.create_market_order(order)
        return self.client.post_order(signed, OrderType.FOK)

    def get_positions(self):
        """Get current positions"""
        return self.client.get_positions()

    def monitor_position(self, market_id: str, take_profit: float = None, stop_loss: float = None):
        """Monitor position and exit at take profit or stop loss"""
        while True:
            positions = self.get_positions()
            position = next((p for p in positions if p['market_id'] == market_id), None)

            if not position:
                print("No position found")
                break

            pnl_pct = float(position['percent_pnl'])

            if take_profit and pnl_pct >= take_profit:
                print(f"Take profit hit: {pnl_pct}%")
                self.close_position(position)
                break

            if stop_loss and pnl_pct <= -stop_loss:
                print(f"Stop loss hit: {pnl_pct}%")
                self.close_position(position)
                break

            time.sleep(60)  # Check every minute

    def close_position(self, position):
        """Close a position by selling all shares"""
        token_id = position['asset']
        size = float(position['size'])

        return self.place_market_order(token_id, size, SELL)

# Usage
if __name__ == "__main__":
    bot = PolymarketBot(
        private_key="<your-private-key>",
        signature_type=0
    )

    # Find Bitcoin markets
    markets = bot.find_market("bitcoin")
    for market in markets[:3]:
        print(f"- {market['question']}")

    # Get prices
    token_id = markets[0]['tokens'][0]['token_id']
    prices = bot.get_market_price(token_id)
    print(f"Prices: {prices}")

    # Place order
    order_response = bot.place_limit_order(
        token_id=token_id,
        price=0.50,
        size=10.0,
        side=BUY
    )
    print(f"Order placed: {order_response}")
```

### SDK Configuration Options

#### Client Initialization Parameters

```python
ClobClient(
    host="https://clob.polymarket.com",    # CLOB API endpoint
    key="<private-key>",                    # Ethereum private key (optional for read-only)
    chain_id=137,                           # Polygon mainnet
    signature_type=0,                       # 0=EOA, 1=Email/Magic, 2=Browser
    funder=None,                            # Funder address (required for types 1 & 2)
    api_key=None,                           # Existing API key (optional)
    api_secret=None,                        # Existing API secret (optional)
    api_passphrase=None                     # Existing API passphrase (optional)
)
```

### Key SDK Methods Reference

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_server_time()` | None | Dict | Get server timestamp |
| `get_simplified_markets()` | None | List[Dict] | Get all markets |
| `get_order_book(token_id)` | token_id: str | Dict | Get order book |
| `get_midpoint(token_id)` | token_id: str | float | Get mid price |
| `get_price(token_id, side)` | token_id: str, side: str | float | Get execution price |
| `create_order(order)` | order: OrderArgs | SignedOrder | Create signed limit order |
| `create_market_order(order)` | order: MarketOrderArgs | SignedOrder | Create signed market order |
| `post_order(signed, type)` | signed: SignedOrder, type: OrderType | Dict | Submit order |
| `get_orders(params)` | params: OpenOrderParams | List[Dict] | Get active orders |
| `cancel(order_id)` | order_id: str | Dict | Cancel order |
| `cancel_all()` | None | Dict | Cancel all orders |
| `get_positions()` | None | List[Dict] | Get positions |
| `get_trades()` | None | List[Dict] | Get trade history |
| `create_or_derive_api_creds()` | None | Dict | Create/derive API credentials |
| `set_api_creds(creds)` | creds: Dict | None | Set API credentials |

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Research and Planning
- [x] Research Polymarket CLOB API architecture
- [x] Document authentication methods
- [x] Document API endpoints
- [x] Document data models
- [x] Document order placement flow
- [x] Document WebSocket feeds
- [x] Document rate limits
- [x] Document costs and fees
- [x] Create specification document

### Phase 2: Core Client Development
- [ ] Create `backend/polymarket_client/` module
- [ ] Implement `client.py` with ClobClient wrapper
- [ ] Implement `models.py` with data models (Market, Order, Position, Trade)
- [ ] Implement `exceptions.py` with custom exceptions
- [ ] Implement authentication management
- [ ] Implement order placement methods
- [ ] Implement market data fetching
- [ ] Implement position monitoring
- [ ] Add error handling and retries
- [ ] Add rate limiting logic

### Phase 3: Testing
- [ ] Create mock client for testing
- [ ] Write unit tests for client methods
- [ ] Write integration tests with Polymarket testnet (if available)
- [ ] Test authentication flow
- [ ] Test order placement (limit, market)
- [ ] Test order cancellation
- [ ] Test position monitoring
- [ ] Test error handling
- [ ] Test rate limiting

### Phase 4: Strategy Integration
- [ ] Create `freqtrade/strategies/LLM_Polymarket_Strategy.py`
- [ ] Adapt LLM signal provider for binary outcomes
- [ ] Implement market-specific indicators
- [ ] Integrate consensus signals
- [ ] Add position sizing for prediction markets
- [ ] Add backtesting configuration
- [ ] Test strategy with historical data

### Phase 5: Risk Management
- [ ] Create `backend/api/services/risk_manager.py`
- [ ] Calculate portfolio-wide risk (crypto + polymarket)
- [ ] Implement position limits
- [ ] Calculate market correlation
- [ ] Implement stop-loss recommendations
- [ ] Add risk scoring for LLM signals
- [ ] Create risk dashboard API endpoint

### Phase 6: API Integration
- [ ] Add Polymarket endpoints to Django REST API
- [ ] Implement market discovery endpoint
- [ ] Implement order placement endpoint
- [ ] Implement position monitoring endpoint
- [ ] Add proper serializers
- [ ] Add authentication middleware
- [ ] Update OpenAPI schema

### Phase 7: Documentation
- [ ] Create developer guide for Polymarket integration
- [ ] Document trading bot examples
- [ ] Document risk management strategies
- [ ] Create troubleshooting guide
- [ ] Add to main project documentation

---

## REFERENCES

### Official Documentation
- **Main Docs**: https://docs.polymarket.com/
- **CLOB Introduction**: https://docs.polymarket.com/developers/CLOB/introduction
- **Authentication**: https://docs.polymarket.com/developers/CLOB/authentication
- **Endpoints**: https://docs.polymarket.com/developers/CLOB/endpoints
- **WebSocket Overview**: https://docs.polymarket.com/developers/CLOB/websocket/wss-overview
- **Rate Limits**: https://docs.polymarket.com/quickstart/introduction/rate-limits
- **Gamma API**: https://docs.polymarket.com/developers/gamma-markets-api/overview
- **First Order Tutorial**: https://docs.polymarket.com/quickstart/orders/first-order

### GitHub Repositories
- **py-clob-client**: https://github.com/Polymarket/py-clob-client
- **clob-client (TypeScript)**: https://github.com/Polymarket/clob-client
- **python-order-utils**: https://github.com/Polymarket/python-order-utils
- **real-time-data-client**: https://github.com/Polymarket/real-time-data-client
- **Polymarket Agents**: https://github.com/Polymarket/agents

### API Endpoints
- **CLOB REST**: https://clob.polymarket.com/
- **Data API**: https://data-api.polymarket.com/
- **Gamma Markets**: https://gamma-api.polymarket.com/
- **CLOB WebSocket**: wss://ws-subscriptions-clob.polymarket.com/ws/
- **Real-Time Data**: wss://ws-live-data.polymarket.com

### Community Resources
- **PyPI Package**: https://pypi.org/project/py-clob-client/
- **API Tutorial Blog**: https://apidog.com/blog/polymarket-api/
- **Jeremy Whittaker Guides**:
  - Accessing Polymarket Data: https://jeremywhittaker.com/index.php/2024/08/20/accessing-polymarket-data-in-python/
  - Generating API Keys: https://jeremywhittaker.com/index.php/2024/08/28/generating-api-keys-for-polymarket-com/

### Security and Audits
- **ChainSecurity Audit**: Referenced in official docs
- **Smart Contract Source**: Available on GitHub (Polymarket organization)

### Related Standards
- **EIP-712**: Ethereum typed structured data hashing and signing
- **ERC-20**: USDC token standard
- **ERC-1155**: Conditional token standard (Outcome Tokens)

---

## APPENDIX A: ERROR HANDLING

### Common Error Codes

| HTTP Code | Error | Description | Resolution |
|-----------|-------|-------------|------------|
| 400 | Bad Request | Invalid order parameters | Validate order args before submission |
| 401 | Unauthorized | Invalid/missing credentials | Regenerate API credentials |
| 403 | Forbidden | Insufficient permissions | Check wallet permissions/allowances |
| 404 | Not Found | Order/market not found | Verify IDs are correct |
| 429 | Too Many Requests | Rate limit exceeded | Implement exponential backoff |
| 500 | Internal Server Error | Server-side issue | Retry with backoff |
| 503 | Service Unavailable | Service down | Wait and retry later |

### Python Exception Handling

```python
from py_clob_client.exceptions import PolyApiException

try:
    response = client.post_order(signed_order, OrderType.GTC)
except PolyApiException as e:
    if e.status_code == 429:
        print("Rate limit exceeded, backing off...")
        time.sleep(60)
        # Retry
    elif e.status_code == 401:
        print("Authentication failed, regenerating credentials...")
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        # Retry
    else:
        print(f"API error: {e}")
        raise
```

---

## APPENDIX B: INTEGRATION WITH THALAS TRADER

### LLM Signal Adaptation for Prediction Markets

Traditional crypto signals need adaptation for binary prediction markets:

#### Crypto Signal Format
```json
{
  "decision": "BUY",
  "confidence": 0.85,
  "reasoning": "Strong bullish momentum",
  "risk_level": "medium",
  "suggested_stop_loss": 45000,
  "suggested_take_profit": 52000
}
```

#### Adapted Prediction Market Signal
```json
{
  "decision": "BUY_YES",           // or BUY_NO, SELL_YES, SELL_NO, HOLD
  "confidence": 0.85,
  "outcome_probability": 0.65,     // Estimated probability of YES outcome
  "reasoning": "Market undervaluing YES outcome based on...",
  "risk_level": "medium",
  "suggested_entry_price": 0.50,
  "suggested_exit_price": 0.70,
  "edge": 0.15                      // Estimated edge (prob - price)
}
```

### Multi-LLM Consensus for Prediction Markets

Consensus voting should weight probability estimates:

```python
def aggregate_prediction_signals(signals):
    """Aggregate LLM signals for prediction markets"""

    # Extract probability estimates
    probabilities = [s['outcome_probability'] for s in signals]

    # Calculate consensus probability (weighted by confidence)
    weights = [s['confidence'] for s in signals]
    weighted_prob = sum(p * w for p, w in zip(probabilities, weights)) / sum(weights)

    # Get current market price
    market_price = get_market_price(token_id)

    # Calculate edge
    edge = weighted_prob - market_price

    # Decision logic
    if edge > 0.10:  # 10% edge threshold
        decision = "BUY_YES"
    elif edge < -0.10:
        decision = "BUY_NO"
    else:
        decision = "HOLD"

    return {
        'decision': decision,
        'consensus_probability': weighted_prob,
        'market_price': market_price,
        'edge': edge,
        'confidence': sum(weights) / len(weights),
        'agreement_score': calculate_agreement(probabilities)
    }
```

### Position Sizing for Prediction Markets

Kelly Criterion for optimal bet sizing:

```python
def kelly_position_size(edge, odds, bankroll, kelly_fraction=0.25):
    """
    Calculate Kelly Criterion position size

    edge: Estimated edge (probability - price)
    odds: Current market odds (price)
    bankroll: Total available capital
    kelly_fraction: Fraction of Kelly to use (default: 1/4 Kelly)
    """
    if edge <= 0:
        return 0

    # Kelly formula: (p * (b + 1) - 1) / b
    # where p = win probability, b = odds
    p = edge + odds
    b = (1 - odds) / odds

    kelly = (p * (b + 1) - 1) / b

    # Use fractional Kelly (more conservative)
    fractional_kelly = kelly * kelly_fraction

    # Calculate position size
    position_size = bankroll * fractional_kelly

    return max(0, position_size)
```

---

**END OF SPECIFICATION**

---

**Next Steps**:
1. Review and validate specification with development team
2. Begin Phase 2: Core Client Development
3. Set up development environment with Polymarket testnet credentials
4. Implement and test core client functionality
5. Integrate with Thalas Trader LLM consensus system
