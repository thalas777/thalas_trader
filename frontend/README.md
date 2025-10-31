# Thalas Trader Frontend

Multi-LLM consensus trading dashboard built with Next.js 14, TypeScript, and Tailwind CSS.

## Tech Stack

- **Framework**: Next.js 14.2.33 (App Router)
- **Language**: TypeScript (Strict Mode)
- **Styling**: Tailwind CSS with custom theme
- **Data Fetching**: SWR + Axios
- **Charts**: Recharts
- **Date Utilities**: date-fns

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout with navigation
│   ├── page.tsx           # Dashboard page
│   └── consensus/         # Consensus signals page
│       └── page.tsx
├── components/            # React components
│   ├── Dashboard.tsx      # Main dashboard component
│   ├── ConsensusView.tsx  # Consensus visualization
│   ├── layout/           # Layout components
│   │   └── Navigation.tsx
│   └── ui/               # Shared UI components
├── lib/                   # Utilities and API client
│   ├── api/
│   │   ├── client.ts     # API client for backend
│   │   ├── types.ts      # TypeScript interfaces
│   │   └── index.ts
│   ├── hooks/            # Custom React hooks
│   └── utils/            # Utility functions
├── public/               # Static assets
├── .env.local.example    # Environment variables template
└── tailwind.config.ts    # Tailwind configuration

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Thalas Trader backend running (default: http://localhost:8000)

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.local.example .env.local

# Edit .env.local to set your backend URL
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
# Start development server
npm run dev

# Open http://localhost:3000
```

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Features

### Dashboard (/)
- Portfolio summary with P/L metrics
- Active bots status table
- Recent trades feed
- Performance charts

### Consensus Signals (/consensus)
- Multi-LLM consensus request form
- Provider health status
- Vote distribution visualization
- Individual provider responses
- Consensus signal history

## API Integration

The frontend connects to the Thalas Trader backend API:

### Endpoints Used
- `GET /api/v1/portfolio/summary` - Portfolio metrics
- `GET /api/v1/bots` - Bot status
- `GET /api/v1/trades` - Trade history
- `GET /api/v1/portfolio/performance` - Performance data
- `POST /api/v1/strategies/llm-consensus` - LLM consensus signals

### API Client

The API client is located at `/lib/api/client.ts`:

```typescript
import { apiClient } from '@/lib/api/client';

// Get portfolio summary
const summary = await apiClient.getSummary();

// Get consensus signal
const signal = await apiClient.getConsensusSignal('BTC/USDT', '1h');
```

## Tailwind Theme

Custom color palette for trading dashboards:

- **Primary**: Blue shades for primary UI elements
- **Success**: Green for profitable trades/signals
- **Danger**: Red for losses/risks
- **Warning**: Yellow/orange for warnings
- **Neutral**: Gray scale for dark mode support

## Environment Variables

```bash
# Backend API URL (required)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: WebSocket URL for real-time updates
# NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Build Output

Production build generates optimized static pages:

```
Route (app)              Size     First Load JS
┌ ○ /                    175 B    96.2 kB
├ ○ /_not-found          873 B    88.2 kB
└ ○ /consensus           130 kB   218 kB
+ First Load JS shared   87.3 kB
```

## Development Notes

- **TypeScript strict mode** is enabled for type safety
- **SWR** is used for data fetching with automatic revalidation
- **Recharts** provides responsive charts
- **Responsive design** works on mobile and desktop
- **Dark mode** support via Tailwind CSS

## Next Steps

1. **Task 4.2**: Dashboard UI components (PortfolioSummary, BotStatusTable, TradesFeed, PerformanceChart)
2. **Task 4.3**: Consensus visualization components (ProviderVoteChart, ProviderHealthStatus, ConsensusSignalFeed)
3. **Task 4.4**: Real-time data polling with SWR
4. **Task 4.5**: E2E testing with Playwright

## License

Part of the Thalas Trader project.
