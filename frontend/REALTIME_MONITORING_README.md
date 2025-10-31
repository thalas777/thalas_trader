# Real-time Monitoring Implementation Guide

## Overview

This document describes the real-time monitoring system implemented for the Thalas Trader frontend dashboard. The system provides live data updates, connection status monitoring, toast notifications, and optional WebSocket support.

## Architecture

### Components

1. **API Client** (`lib/api-client.ts`)
2. **useLiveData Hook** (`lib/hooks/useLiveData.ts`)
3. **Connection Status** (`components/ConnectionStatus.tsx`)
4. **Toast Notifications** (`components/ToastNotification.tsx`)
5. **WebSocket Client** (`lib/websocket.ts`) - Optional

## Features

### 1. SWR-Based Live Data Polling

The `useLiveData` hook provides automatic data fetching and caching using SWR:

```typescript
import { useLiveData } from '@/lib/hooks/useLiveData'

function MyComponent() {
  const { data, error, isLoading } = useLiveData<Trade[]>(
    '/api/v1/portfolio/trades',
    { refreshInterval: 30000 } // Refresh every 30 seconds
  )

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>
  return <div>{/* Render data */}</div>
}
```

**Features:**
- Automatic polling at configurable intervals (default: 30s)
- Automatic retry with exponential backoff (3 retries, 5s interval)
- Request deduplication (2s window)
- Revalidation on focus and reconnect
- Type-safe with TypeScript generics

### 2. Connection Status Indicator

Real-time connection health monitoring with visual feedback:

```typescript
import { ConnectionStatus, ConnectionStatusFull } from '@/components/ConnectionStatus'

// Compact version (for navbar)
<ConnectionStatus showLabel={false} showTimestamp={true} />

// Full version (for dashboard)
<ConnectionStatusFull />
```

**States:**
- 🟢 **Green**: Connected and refreshing normally
- 🟡 **Yellow**: Slow connection (>2 minutes since last update)
- 🔴 **Red**: Disconnected or error

**Features:**
- Animated ping effect during data fetch
- Last update timestamp with relative time
- Provider health status display
- Dark mode support

### 3. Toast Notifications

Elegant toast notifications using Sonner:

```typescript
import {
  showTradeNotification,
  showConsensusSignalNotification,
  showSuccessNotification,
  showErrorNotification
} from '@/components/ToastNotification'

// Show trade notification
showTradeNotification({
  id: '123',
  symbol: 'BTC/USDT',
  side: 'BUY',
  size: 0.1,
  price: 45000,
  pnl: 500
})

// Show consensus signal
showConsensusSignalNotification({
  decision: 'BUY',
  confidence: 0.85,
  symbol: 'ETH/USDT',
  reasoning: 'Strong bullish momentum...'
})

// Show success message
showSuccessNotification('Order Placed', 'Your order has been executed')
```

**Features:**
- Auto-monitoring of new trades and signals
- Backend connection status notifications
- Configurable duration and position
- Rich content with icons and descriptions
- Dark mode support

### 4. WebSocket Client (Optional)

Real-time updates via WebSocket with automatic reconnection:

```typescript
import { getWebSocket } from '@/lib/websocket'

const ws = getWebSocket()

// Connect
ws.connect()

// Subscribe to messages
const unsubscribe = ws.onMessage((message) => {
  console.log('Received:', message)
  if (message.type === 'trade') {
    showTradeNotification(message.data)
  }
})

// Send message
ws.send('subscribe', { channel: 'trades' })

// Cleanup
unsubscribe()
ws.disconnect()
```

**Features:**
- Automatic reconnection with exponential backoff
- Connection status tracking
- Message handler subscription system
- Graceful error handling
- Falls back to polling if WebSocket unavailable

## Setup

### 1. Environment Variables

Create `.env.local`:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# WebSocket URL (optional)
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### 2. Root Layout Integration

The notification system is already integrated in `app/layout.tsx`:

```typescript
import { NotificationSystem } from "@/components/ToastNotification"

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <NotificationSystem />
        {children}
      </body>
    </html>
  )
}
```

## Usage Examples

### Example 1: Portfolio Metrics with Live Updates

```typescript
'use client'

import { useLiveData } from '@/lib/hooks/useLiveData'

export function PortfolioMetrics() {
  const { data, error, isLoading } = useLiveData<any>(
    '/api/v1/portfolio/metrics',
    { refreshInterval: 30000 }
  )

  if (isLoading) return <div>Loading metrics...</div>
  if (error) return <div>Error loading metrics</div>

  return (
    <div>
      <h2>Portfolio Value: ${data.total_value}</h2>
      <p>Total P&L: ${data.total_pnl}</p>
      <p>Active Positions: {data.active_positions}</p>
    </div>
  )
}
```

### Example 2: Trades Feed with Notifications

```typescript
'use client'

import { useTrades } from '@/lib/hooks/useLiveData'

export function TradesFeed() {
  const { data: trades, error } = useTrades(50, 10000) // 50 trades, refresh every 10s

  if (error) return <div>Error loading trades</div>

  return (
    <div>
      <h2>Recent Trades</h2>
      {trades?.map(trade => (
        <div key={trade.id}>
          {trade.side} {trade.symbol} @ ${trade.price}
        </div>
      ))}
    </div>
  )
}
```

### Example 3: Custom Refresh Interval

```typescript
'use client'

import { useState } from 'react'
import { useLiveData } from '@/lib/hooks/useLiveData'

export function CustomRefresh() {
  const [interval, setInterval] = useState(30000)

  const { data } = useLiveData('/api/v1/data', {
    refreshInterval: interval
  })

  return (
    <div>
      <button onClick={() => setInterval(10000)}>Fast (10s)</button>
      <button onClick={() => setInterval(30000)}>Normal (30s)</button>
      <button onClick={() => setInterval(60000)}>Slow (60s)</button>
    </div>
  )
}
```

## Configuration

### useLiveData Options

```typescript
interface UseLiveDataOptions {
  refreshInterval?: number        // Default: 30000 (30s)
  enabled?: boolean               // Default: true
  revalidateOnFocus?: boolean     // Default: true
  revalidateOnReconnect?: boolean // Default: true
  errorRetryCount?: number        // Default: 3
  errorRetryInterval?: number     // Default: 5000 (5s)
  dedupingInterval?: number       // Default: 2000 (2s)
}
```

### WebSocket Options

```typescript
interface WebSocketOptions {
  url?: string                    // Default: NEXT_PUBLIC_WS_URL
  reconnectInterval?: number      // Default: 5000 (5s)
  maxReconnectAttempts?: number   // Default: 10
}
```

## Best Practices

### 1. Choose Appropriate Refresh Intervals

```typescript
// High-frequency data (trades, prices)
const { data } = useLiveData('/api/v1/trades', { refreshInterval: 10000 }) // 10s

// Medium-frequency data (portfolio metrics)
const { data } = useLiveData('/api/v1/portfolio', { refreshInterval: 30000 }) // 30s

// Low-frequency data (health checks)
const { data } = useLiveData('/api/v1/health', { refreshInterval: 60000 }) // 60s
```

### 2. Handle Loading and Error States

```typescript
const { data, error, isLoading, isValidating } = useLiveData('/api/v1/data')

if (isLoading) {
  return <LoadingSpinner />
}

if (error) {
  return <ErrorMessage error={error} />
}

return (
  <div>
    {isValidating && <RefreshIndicator />}
    <DataDisplay data={data} />
  </div>
)
```

### 3. Use SWR Mutation for Optimistic Updates

```typescript
const { data, mutate } = useLiveData('/api/v1/positions')

async function closePosition(id: string) {
  // Optimistic update
  mutate(
    data?.filter(p => p.id !== id),
    false // Don't revalidate immediately
  )

  // Make API call
  await apiClient.closePosition(id)

  // Revalidate
  mutate()
}
```

### 4. Cleanup on Unmount

```typescript
useEffect(() => {
  const ws = getWebSocket()
  ws.connect()

  const unsubscribe = ws.onMessage(handleMessage)

  return () => {
    unsubscribe()
    ws.disconnect()
  }
}, [])
```

## Demo

Visit `/demo` to see all real-time monitoring features in action:

```bash
npm run dev
# Navigate to http://localhost:3000/demo
```

The demo page showcases:
- Live data polling with configurable intervals
- Connection status indicator
- Toast notifications (trigger with "Test Notifications" button)
- Error handling and fallback states

## Testing

### Manual Testing

1. Start the backend:
   ```bash
   cd backend && python manage.py runserver
   ```

2. Start the frontend:
   ```bash
   cd frontend && npm run dev
   ```

3. Open http://localhost:3000/demo

4. Test scenarios:
   - Normal operation: Backend running → Green status, data refreshing
   - Slow connection: Stop backend for 2+ minutes → Yellow status
   - Disconnected: Stop backend → Red status, error notifications
   - Reconnection: Restart backend → Green status, success notification

### Testing with Mock Data

Update the fetcher in `lib/hooks/useLiveData.ts`:

```typescript
async function fetcher(endpoint: string) {
  // Return mock data for testing
  if (endpoint.includes('/trades')) {
    return [
      { id: '1', symbol: 'BTC/USDT', side: 'BUY', price: 45000 },
      { id: '2', symbol: 'ETH/USDT', side: 'SELL', price: 3000 },
    ]
  }
  return null
}
```

## Performance Considerations

1. **Request Deduplication**: SWR prevents duplicate requests within 2s window
2. **Caching**: SWR caches responses to reduce unnecessary requests
3. **Conditional Fetching**: Use `enabled` option to disable polling when not needed
4. **Cleanup**: Components automatically cleanup subscriptions on unmount

## Troubleshooting

### Issue: Data not refreshing

**Solution**: Check that `refreshInterval` is set and `enabled` is true:

```typescript
const { data } = useLiveData('/api/v1/data', {
  refreshInterval: 30000,
  enabled: true
})
```

### Issue: Too many requests

**Solution**: Increase `refreshInterval` or use `dedupingInterval`:

```typescript
const { data } = useLiveData('/api/v1/data', {
  refreshInterval: 60000,      // Slower refresh
  dedupingInterval: 5000       // Longer dedup window
})
```

### Issue: WebSocket not connecting

**Solution**: Check environment variable and fallback to polling:

```bash
# .env.local
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### Issue: Notifications not showing

**Solution**: Ensure `NotificationSystem` is in root layout:

```typescript
// app/layout.tsx
import { NotificationSystem } from '@/components/ToastNotification'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <NotificationSystem />
        {children}
      </body>
    </html>
  )
}
```

## Next Steps

1. Integrate with full dashboard (Task 4.2)
2. Add consensus visualization real-time updates (Task 4.3)
3. Implement WebSocket backend endpoints
4. Add E2E tests for real-time features (Task 4.5)

## Resources

- [SWR Documentation](https://swr.vercel.app/)
- [Sonner Documentation](https://sonner.emilkowal.ski/)
- [Next.js 14 Documentation](https://nextjs.org/docs)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
