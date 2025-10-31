# Thalas Trader
## Freqtrade LLM Trading Super-Dashboard

Enterprise-grade trading platform integrating Freqtrade with AI-powered signal generation. This project provides a complete full-stack solution featuring a Next.js frontend, Django backend API, and groundbreaking LLM integration for intelligent trading strategies.

### System Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Next.js   │ ───> │    Django    │ ───> │  Freqtrade  │
│  Dashboard  │ <─── │   REST API   │ <─── │   Engine    │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  LLM APIs    │
                     │ Claude/GPT   │
                     └──────────────┘
```
### Key Features

**Dashboard & Monitoring**
- Real-time portfolio performance metrics (P/L, active bots, trade volume)
- Interactive performance charts with historical data
- Live bot status monitoring with detailed metrics
- Recent trades feed with profit/loss tracking
- Responsive design for mobile and desktop

**AI-Powered Trading**
- LLM integration for trading signal generation
- Support for Claude (Anthropic) and GPT (OpenAI)
- Configurable prompt engineering templates
- Real-time market analysis with AI reasoning

**Bot Management**
- Start/stop individual bots via API
- Strategy assignment and configuration
- Error monitoring and alerting
- Performance analytics per bot

**Developer Experience**
- Comprehensive REST API with OpenAPI documentation
- Automated testing suite (E2E, integration, unit)
- Docker-ready deployment
- Modular, extensible architecture
### Technology Stack

**Frontend**
- Next.js 14 - React framework with SSR and API routes
- React 18 - Component-based UI library
- TypeScript - Type-safe JavaScript
- Tailwind CSS - Utility-first styling
- Recharts - Data visualization
- SWR - Data fetching and caching

**Backend**
- Django 5.0 - Web framework
- Django REST Framework - API toolkit
- Python 3.11+ - Programming language
- PostgreSQL - Database (optional, defaults to SQLite)

**AI Integration**
- Anthropic Claude API - Primary LLM provider
- OpenAI GPT API - Alternative LLM provider
- Custom prompt templates - Optimized for trading signals

**Testing & QA**
- Playwright - E2E testing
- Pytest - Backend unit/integration tests
- Jest - Frontend unit tests
- Docker - Containerization
### Getting Started

#### Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm/yarn
- Freqtrade instance (or run in demo mode)
- API keys for Anthropic Claude or OpenAI (for LLM features)

#### Installation

**1. Clone the repository**
```bash
git clone https://github.com/your_username/thalas_trader.git
cd thalas_trader
```

**2. Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Start the server
python manage.py runserver
```

Backend will be available at `http://localhost:8000`

**3. Frontend Setup**
```bash
cd frontend
npm install

# Create environment file
cp .env.local.example .env.local
# Edit .env.local with your API URL

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:3000`

**4. Freqtrade LLM Adapter Setup**
```bash
cd freqtrade
pip install -r requirements.txt

# Copy adapter to your Freqtrade strategies folder
cp adapters/llm_signal_provider.py /path/to/your/freqtrade/user_data/strategies/
cp strategies/LLM_Momentum_Strategy.py /path/to/your/freqtrade/user_data/strategies/
```

#### Configuration

Create `.env` files with the following variables:

**backend/.env**
```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Freqtrade Configuration
FREQTRADE_API_URL=http://localhost:8080
FREQTRADE_USERNAME=freqtrader
FREQTRADE_PASSWORD=your-password

# LLM API Keys
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
```

**frontend/.env.local**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
### Project Structure

```
thalas_trader/
├── backend/                    # Django REST API
│   ├── api/                    # API app
│   │   ├── views/              # API endpoints
│   │   ├── serializers/        # Data serialization
│   │   ├── services/           # Business logic
│   │   └── models/             # Database models
│   ├── core/                   # Core Django settings
│   ├── freqtrade_client/       # Freqtrade API wrapper
│   ├── llm_service/            # LLM orchestration
│   └── manage.py
│
├── frontend/                   # Next.js Application
│   ├── app/                    # Next.js 14 app directory
│   ├── components/             # React components
│   │   ├── Dashboard.tsx
│   │   ├── BotStatusTable.tsx
│   │   ├── PerformanceChart.tsx
│   │   └── ...
│   ├── lib/                    # Utilities & API clients
│   ├── hooks/                  # Custom React hooks
│   └── public/                 # Static assets
│
├── freqtrade/                  # Freqtrade Integration
│   ├── adapters/               # LLM signal provider
│   │   └── llm_signal_provider.py
│   └── strategies/             # Example strategies
│       └── LLM_Momentum_Strategy.py
│
├── tests/                      # Testing suite
│   ├── e2e/                    # Playwright E2E tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test data
│
├── docker/                     # Docker configurations
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── docker-compose.yml
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── DEPLOYMENT.md
│
└── PROJECT_CHARTER.md          # Development roadmap
```
### API Documentation

Once the backend is running, access interactive API documentation:

- **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`

#### Key Endpoints

- `GET /api/v1/summary` - Portfolio summary metrics
- `GET /api/v1/bots` - List all bots and their status
- `POST /api/v1/bots/{id}/start` - Start a specific bot
- `POST /api/v1/bots/{id}/stop` - Stop a specific bot
- `GET /api/v1/trades` - Paginated trade history
- `GET /api/v1/performance` - Historical performance data
- `POST /api/v1/strategies/llm` - LLM signal generation endpoint

### Testing

**Backend Tests**
```bash
cd backend
pytest
pytest --cov=api  # With coverage
```

**Frontend Tests**
```bash
cd frontend
npm test
npm run test:watch  # Watch mode
```

**E2E Tests**
```bash
cd tests/e2e
npx playwright install  # First time only
npx playwright test
npx playwright test --ui  # Interactive mode
```

### Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment guides.

**Quick Docker Deployment**
```bash
docker-compose up -d
```

### Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Status

🚧 **Active Development** - See [PROJECT_CHARTER.md](PROJECT_CHARTER.md) for current progress.
License
Distributed under the MIT License. See LICENSE for more information.
