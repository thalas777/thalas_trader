# Backend Quick Start Guide

## Setup (First Time)

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create .env file
cp .env.example .env
```

## Configuration

Edit `.env` file with your settings:

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key-change-this
DEBUG=True

# Freqtrade (optional - uses mock data if not available)
FREQTRADE_API_URL=http://localhost:8080
FREQTRADE_USERNAME=freqtrader
FREQTRADE_PASSWORD=your-password

# LLM (optional - for AI trading signals)
ANTHROPIC_API_KEY=sk-ant-your-key  # OR
OPENAI_API_KEY=sk-your-key
DEFAULT_LLM_PROVIDER=anthropic  # or openai
```

## Running the Server

```bash
source venv/bin/activate
python manage.py runserver
```

Server runs at: **http://localhost:8000**

## Testing

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_api_endpoints.py -v
```

### Run With Coverage
```bash
pytest --cov=api --cov=freqtrade_client --cov=llm_service
```

### Interactive API Testing
```bash
python test_api.py
```

## API Endpoints

### Summary
```bash
curl http://localhost:8000/api/v1/summary
```

### Bots
```bash
# List all bots
curl http://localhost:8000/api/v1/bots

# Get specific bot
curl http://localhost:8000/api/v1/bots/1

# Start bot
curl -X POST http://localhost:8000/api/v1/bots/1/start

# Stop bot
curl -X POST http://localhost:8000/api/v1/bots/1/stop
```

### Trades
```bash
# List trades
curl http://localhost:8000/api/v1/trades

# With pagination
curl "http://localhost:8000/api/v1/trades?limit=10&offset=0"

# Specific trade
curl http://localhost:8000/api/v1/trades/1
```

### Performance
```bash
curl http://localhost:8000/api/v1/performance
```

### LLM Signal Generation
```bash
# Health check
curl http://localhost:8000/api/v1/strategies/llm

# Generate signal
curl -X POST http://localhost:8000/api/v1/strategies/llm \
  -H "Content-Type: application/json" \
  -d '{
    "market_data": {
      "rsi": 45.2,
      "ema_short": 42500.0,
      "ema_long": 42300.0,
      "volume": 1250000
    },
    "pair": "BTC/USDT",
    "timeframe": "5m",
    "current_price": 42500.0
  }'
```

## API Documentation

Interactive documentation available at:

- **Swagger UI:** http://localhost:8000/api/schema/swagger-ui/
- **ReDoc:** http://localhost:8000/api/schema/redoc/

## Project Structure

```
backend/
├── api/                    # API endpoints
│   ├── views/
│   │   ├── summary.py      # Portfolio summary
│   │   ├── bots.py         # Bot management
│   │   ├── trades.py       # Trade history
│   │   ├── performance.py  # Performance data
│   │   └── strategies.py   # LLM integration
│   └── urls.py             # URL routing
│
├── freqtrade_client/       # Freqtrade API wrapper
│   └── client.py
│
├── llm_service/            # LLM orchestration
│   └── orchestrator.py
│
├── core/                   # Django settings
│   ├── settings.py
│   └── urls.py
│
├── tests/                  # Test suite
│   ├── test_api_endpoints.py
│   ├── test_freqtrade_client.py
│   └── test_llm_orchestrator.py
│
├── manage.py
├── requirements.txt
├── test_api.py             # Interactive test script
└── TESTING_REPORT.md       # Full test results
```

## Common Tasks

### Add New API Endpoint

1. Create view in `api/views/your_view.py`
2. Add route in `api/urls.py`
3. Write tests in `tests/test_your_view.py`
4. Run tests: `pytest`

### Change LLM Provider

Edit `.env`:
```bash
# For Claude
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-3-5-sonnet-20241022

# For GPT
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4
```

### Connect to Real Freqtrade

1. Start your Freqtrade instance with API enabled
2. Edit `.env`:
   ```bash
   FREQTRADE_API_URL=http://your-server:8080
   FREQTRADE_USERNAME=your-username
   FREQTRADE_PASSWORD=your-password
   ```
3. Restart Django server

## Troubleshooting

### Server won't start

```bash
# Check Python version (need 3.11+)
python3 --version

# Reinstall dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate
```

### Tests failing

```bash
# Install test dependencies
pip install pytest pytest-django pytest-cov

# Clear test database
rm db.sqlite3
python manage.py migrate

# Run tests verbosely
pytest -v
```

### LLM not working

1. Check API key is set in `.env`
2. Verify provider name (must be `anthropic` or `openai`)
3. Check health endpoint:
   ```bash
   curl http://localhost:8000/api/v1/strategies/llm
   ```

### Freqtrade connection failing

This is normal if Freqtrade isn't running. The backend will use mock data.

To verify:
```bash
curl http://localhost:8000/api/v1/summary
# Should still return data (mock if Freqtrade unavailable)
```

## Development Tips

### Watch Mode for Tests
```bash
pip install pytest-watch
ptw
```

### Auto-format Code
```bash
black .
isort .
```

### Check Code Quality
```bash
flake8 .
```

### Generate Coverage Report
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Next Steps

1. ✅ Backend is ready for frontend development
2. ✅ Add your LLM API keys to test AI features
3. ✅ Connect to real Freqtrade instance (optional)
4. 🚧 Proceed to frontend development

## Support

- See `TESTING_REPORT.md` for detailed test results
- Check API docs at http://localhost:8000/api/schema/swagger-ui/
- Review `PROJECT_CHARTER.md` for project roadmap
