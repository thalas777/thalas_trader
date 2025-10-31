# Thalas Trader - Consensus Frontend

Multi-LLM consensus trading signals visualization dashboard built with Next.js 14, TypeScript, Tailwind CSS, and Recharts.

## Features

### Consensus Visualization Components

1. **ConsensusView** - Main orchestrator component
   - Manages state and API communication
   - Displays consensus results with full metadata
   - Maintains signal history (last 20 signals)
   - Comprehensive error handling

2. **ConsensusRequestForm** - Request consensus signals
   - Trading pair selection (BTC/USDT, ETH/USDT, etc.)
   - Timeframe selection (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
   - Market indicators: RSI, MACD, EMA, Volume, Bollinger Bands, ATR
   - Optional custom provider weights (Anthropic, OpenAI, Gemini, Grok)
   - Loading states and validation

3. **ProviderVoteChart** - Vote visualization
   - Pie chart showing vote distribution (BUY/SELL/HOLD)
   - Bar chart showing confidence levels by provider
   - Provider response table with decision, confidence, risk level, latency, reasoning
   - Color-coded: BUY (green), SELL (red), HOLD (yellow/orange)
   - Provider-specific colors: Anthropic (green), OpenAI (blue), Gemini (purple), Grok (pink)

4. **ProviderHealthStatus** - Real-time health monitoring
   - Auto-refresh every 30 seconds via SWR
   - Status indicators: healthy/degraded/unavailable
   - Latency metrics
   - Color-coded status cards
   - Last check timestamp

5. **ConsensusSignalFeed** - Signal history
   - Displays recent consensus signals
   - Filters: decision type (ALL/BUY/SELL/HOLD), timeframe
   - Formatted timestamps (relative time)
   - Agreement scores and confidence levels
   - Risk level indicators

## Technology Stack

- **Next.js 14** - App Router, React Server Components
- **TypeScript** - Type-safe development
- **Tailwind CSS 4** - Utility-first styling with dark mode
- **Recharts** - Charts and data visualization
- **SWR** - Real-time data fetching and caching
- **Axios** - HTTP client for API calls

## Project Structure

```
frontend/
├── app/
│   ├── consensus/
│   │   └── page.tsx          # Consensus signals page
│   ├── layout.tsx             # Root layout with navigation
│   ├── page.tsx               # Homepage
│   └── globals.css            # Global styles
├── components/
│   ├── layout/
│   │   └── Navigation.tsx     # Top navigation bar
│   ├── ConsensusView.tsx      # Main consensus component
│   ├── ConsensusRequestForm.tsx  # Request form
│   ├── ProviderVoteChart.tsx  # Vote visualization
│   ├── ProviderHealthStatus.tsx  # Provider health
│   ├── ConsensusSignalFeed.tsx   # Signal history
│   └── ToastNotification.tsx  # Notification system
└── lib/
    ├── api.ts                 # API client
    └── types.ts               # TypeScript interfaces
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend running at `http://localhost:8000` (or configure `NEXT_PUBLIC_API_URL`)

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Visit http://localhost:3000

### Build

```bash
npm run build
npm run start
```

## Configuration

### Environment Variables

Create `.env.local` file:

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### API Endpoints Used

- `POST /api/v1/strategies/llm-consensus` - Get consensus signal
- `GET /api/v1/strategies/llm-consensus` - Get provider health

## Usage

### 1. Navigate to Consensus Page

Go to `/consensus` or click "Consensus Signals" in navigation.

### 2. Fill Request Form

- Select trading pair (e.g., BTC/USDT)
- Select timeframe (e.g., 1h)
- Enter market indicators:
  - RSI: 0-100 (e.g., 50)
  - MACD: decimal (e.g., 0)
  - MACD Signal: decimal (e.g., 0)
  - EMA Fast/Slow: decimal
  - Volume: number
  - Bollinger Bands: upper/middle/lower
  - ATR: decimal
- Optionally set custom provider weights (0-2)

### 3. Submit Request

Click "Get Consensus" button. The system will:
- Query all enabled LLM providers in parallel
- Aggregate responses using weighted voting
- Display comprehensive results

### 4. View Results

**Summary Section:**
- Decision: BUY/SELL/HOLD with color coding
- Confidence: 0-100%
- Agreement: Provider agreement score
- Risk Level: low/medium/high
- Stop Loss & Take Profit suggestions
- Metadata: latency, cost, tokens used

**Visualization Section:**
- Pie chart: Vote distribution
- Bar chart: Confidence levels by provider
- Table: Individual provider responses

**Signal History:**
- Recent signals with filters
- Click-to-filter by decision or timeframe

### 5. Monitor Provider Health

Top section shows real-time provider status:
- Green: Healthy
- Yellow: Degraded
- Red: Unavailable

Auto-refreshes every 30 seconds.

## API Response Format

```typescript
{
  "decision": "BUY" | "SELL" | "HOLD",
  "confidence": 0.82,
  "reasoning": "Consensus (3/4 providers agree): Strong bullish signals...",
  "risk_level": "low" | "medium" | "high",
  "suggested_stop_loss": 42000.00,
  "suggested_take_profit": 45000.00,
  "consensus_metadata": {
    "total_providers": 4,
    "participating_providers": 4,
    "agreement_score": 0.75,
    "weighted_confidence": 0.82,
    "vote_breakdown": {
      "BUY": 3,
      "HOLD": 1
    },
    "weighted_vote_breakdown": {
      "BUY": 2.8,
      "HOLD": 0.8
    },
    "provider_responses": [
      {
        "provider": "anthropic",
        "decision": "BUY",
        "confidence": 0.85,
        "reasoning": "Strong bullish momentum...",
        "risk_level": "low",
        "cost": 0.0015,
        "tokens_used": 250,
        "latency": 1.2
      }
      // ... more providers
    ],
    "total_latency": 2.5,
    "total_cost": 0.0045,
    "total_tokens": 850
  }
}
```

## Styling

The application uses Tailwind CSS with:
- Dark mode support (automatic/system preference)
- Responsive breakpoints (mobile, tablet, desktop)
- Custom color palette for decisions and providers
- Smooth transitions and hover effects

### Decision Colors

- **BUY**: Green (#10b981)
- **SELL**: Red (#ef4444)
- **HOLD**: Yellow/Orange (#f59e0b)

### Provider Colors

- **Anthropic**: Green (#10b981)
- **OpenAI**: Blue (#3b82f6)
- **Gemini**: Purple (#8b5cf6)
- **Grok**: Pink (#ec4899)

## Troubleshooting

### Backend Connection Failed

**Error:** "Failed to get consensus. Please check if the backend is running."

**Solution:**
1. Verify backend is running: `http://localhost:8000`
2. Check `.env.local` has correct `NEXT_PUBLIC_API_URL`
3. Ensure CORS is configured in backend
4. Check browser console for detailed error

### Provider Health Shows Unavailable

**Possible causes:**
1. Backend not running
2. No API keys configured for providers
3. Provider API temporarily down
4. Rate limit exceeded

**Solution:**
- Check backend logs
- Verify environment variables for provider API keys
- Wait and retry (auto-refresh every 30s)

### TypeScript Errors

Run type checking:

```bash
npx tsc --noEmit
```

### Build Errors

Clear cache and rebuild:

```bash
rm -rf .next
npm run build
```

## Development Notes

- All components use `'use client'` directive for client-side interactivity
- SWR handles caching and revalidation automatically
- Form state managed with React hooks
- Error boundaries catch and display errors gracefully
- Responsive design works on mobile/tablet/desktop

## Testing

### Manual Testing

1. Start backend: `cd backend && python manage.py runserver`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to http://localhost:3000/consensus
4. Test consensus request with sample data
5. Verify charts render correctly
6. Test filters on signal history
7. Check provider health updates
8. Test responsive design (resize browser)

### Integration Testing

The frontend is ready for integration with the backend at:
- `/api/v1/strategies/llm-consensus` (POST) - consensus generation
- `/api/v1/strategies/llm-consensus` (GET) - health check

Ensure backend is running with:
- Provider factory initialized
- At least one provider enabled with valid API key
- CORS configured for frontend origin

## Next Steps

1. Start backend server
2. Configure provider API keys in backend
3. Run frontend in development mode
4. Test consensus generation
5. Monitor provider health
6. Review signal history

## Support

For issues or questions:
- Check backend logs: `backend/logs/`
- Check browser console for frontend errors
- Verify API endpoint responses
- Review INTEGRATION_PLAN.md for architecture

## License

Part of Thalas Trader - Multi-LLM Consensus Trading Bot
