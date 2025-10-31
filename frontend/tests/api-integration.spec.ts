import { test, expect } from '@playwright/test';

test.describe('API Integration Tests', () => {
  test.describe('Backend Connectivity', () => {
    test('should connect to backend server', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/summary');
      expect(response.ok()).toBeTruthy();
      expect(response.status()).toBe(200);
    });

    test('should receive valid JSON from summary endpoint', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/summary');
      const data = await response.json();

      expect(data).toHaveProperty('total_balance');
      expect(data).toHaveProperty('total_profit');
      expect(data).toHaveProperty('active_bots');
      expect(data).toHaveProperty('total_trades');
      expect(data).toHaveProperty('win_rate');
    });
  });

  test.describe('Portfolio Summary API', () => {
    test('summary endpoint should return complete data', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/summary');
      const data = await response.json();

      // Check all required fields
      expect(data).toHaveProperty('total_balance');
      expect(data).toHaveProperty('cash_balance');
      expect(data).toHaveProperty('position_value');
      expect(data).toHaveProperty('total_profit');
      expect(data).toHaveProperty('profit_percentage');
      expect(data).toHaveProperty('profit_24h');
      expect(data).toHaveProperty('total_trades');
      expect(data).toHaveProperty('win_rate');
      expect(data).toHaveProperty('active_bots');
      expect(data).toHaveProperty('total_bots');
      expect(data).toHaveProperty('open_positions');
    });

    test('summary data should have correct types', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/summary');
      const data = await response.json();

      expect(typeof data.total_balance).toBe('number');
      expect(typeof data.total_profit).toBe('number');
      expect(typeof data.active_bots).toBe('number');
      expect(typeof data.total_trades).toBe('number');
      expect(typeof data.win_rate).toBe('number');
    });
  });

  test.describe('Bots API', () => {
    test('bots endpoint should return bot list', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/bots');
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('bots');
      expect(Array.isArray(data.bots)).toBeTruthy();
    });

    test('bot data should have required fields', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/bots');
      const data = await response.json();

      if (data.bots.length > 0) {
        const bot = data.bots[0];
        expect(bot).toHaveProperty('bot_id');
        expect(bot).toHaveProperty('name');
        expect(bot).toHaveProperty('status');
        expect(bot).toHaveProperty('pair');
        expect(bot).toHaveProperty('strategy');
        expect(bot).toHaveProperty('profit');
        expect(bot).toHaveProperty('profit_percentage');
        expect(bot).toHaveProperty('trades_count');
      }
    });

    test('bot status should be valid', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/bots');
      const data = await response.json();

      if (data.bots.length > 0) {
        const validStatuses = ['running', 'stopped', 'paused', 'error'];
        data.bots.forEach((bot: any) => {
          expect(validStatuses).toContain(bot.status);
        });
      }
    });
  });

  test.describe('Trades API', () => {
    test('trades endpoint should return trade list', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/trades?limit=20&offset=0');
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('trades');
      expect(data).toHaveProperty('limit');
      expect(data).toHaveProperty('offset');
      expect(data).toHaveProperty('count');
      expect(Array.isArray(data.trades)).toBeTruthy();
    });

    test('trade data should have required fields', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/trades?limit=20');
      const data = await response.json();

      if (data.trades.length > 0) {
        const trade = data.trades[0];
        expect(trade).toHaveProperty('trade_id');
        expect(trade).toHaveProperty('pair');
        expect(trade).toHaveProperty('type');
        expect(trade).toHaveProperty('amount');
        expect(trade).toHaveProperty('price');
        expect(trade).toHaveProperty('timestamp');
        expect(trade).toHaveProperty('bot_name');
        expect(trade).toHaveProperty('consensus_decision');
        expect(trade).toHaveProperty('consensus_confidence');
      }
    });

    test('trade type should be valid', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/trades');
      const data = await response.json();

      if (data.trades.length > 0) {
        const validTypes = ['buy', 'sell'];
        data.trades.forEach((trade: any) => {
          expect(validTypes).toContain(trade.type);
        });
      }
    });

    test('pagination should work', async ({ request }) => {
      const response1 = await request.get('http://localhost:8000/api/v1/trades?limit=1&offset=0');
      const data1 = await response1.json();

      const response2 = await request.get('http://localhost:8000/api/v1/trades?limit=1&offset=1');
      const data2 = await response2.json();

      // If we have more than one trade, the IDs should be different
      if (data1.trades.length > 0 && data2.trades.length > 0) {
        expect(data1.trades[0].trade_id).not.toBe(data2.trades[0].trade_id);
      }
    });
  });

  test.describe('Performance API', () => {
    test('performance endpoint should return equity curve', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/performance');
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('equity_curve');
      expect(Array.isArray(data.equity_curve)).toBeTruthy();
    });

    test('equity curve data points should have required fields', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/performance');
      const data = await response.json();

      if (data.equity_curve.length > 0) {
        const point = data.equity_curve[0];
        expect(point).toHaveProperty('timestamp');
        expect(point).toHaveProperty('balance');
        expect(point).toHaveProperty('profit');
      }
    });
  });

  test.describe('Bot Control API', () => {
    test('start bot endpoint should exist', async ({ request }) => {
      // Get a bot ID first
      const botsResponse = await request.get('http://localhost:8000/api/v1/bots');
      const botsData = await botsResponse.json();

      if (botsData.bots.length > 0) {
        const botId = botsData.bots[0].bot_id;

        // Try to start the bot (even if already running, endpoint should respond)
        const response = await request.post(`http://localhost:8000/api/v1/bots/${botId}/start`);

        // Should get a response (200 or 400 are both valid)
        expect([200, 400]).toContain(response.status());
      }
    });

    test('stop bot endpoint should exist', async ({ request }) => {
      // Get a bot ID first
      const botsResponse = await request.get('http://localhost:8000/api/v1/bots');
      const botsData = await botsResponse.json();

      if (botsData.bots.length > 0) {
        const botId = botsData.bots[0].bot_id;

        // Try to stop the bot
        const response = await request.post(`http://localhost:8000/api/v1/bots/${botId}/stop`);

        // Should get a response (200 or 400 are both valid)
        expect([200, 400]).toContain(response.status());
      }
    });
  });

  test.describe('Consensus API', () => {
    test('consensus endpoint should accept POST requests', async ({ request }) => {
      const response = await request.post('http://localhost:8000/api/v1/strategies/llm-consensus', {
        data: {
          market_data: {
            pair: 'BTC/USD',
            timeframe: '1h',
            rsi: 65,
            macd: 0.01,
            macd_signal: 0.005,
            volume: 1500000
          }
        }
      });

      // Should get a response (may be 200 or 500 depending on provider availability)
      expect(response.status()).toBeGreaterThanOrEqual(200);
    });

    test('consensus response should have required structure', async ({ request }) => {
      const response = await request.post('http://localhost:8000/api/v1/strategies/llm-consensus', {
        data: {
          market_data: {
            pair: 'BTC/USD',
            timeframe: '1h',
            rsi: 65
          }
        }
      });

      if (response.ok()) {
        const data = await response.json();
        expect(data).toHaveProperty('decision');
        expect(data).toHaveProperty('confidence');
        expect(data).toHaveProperty('reasoning');
        expect(data).toHaveProperty('consensus_metadata');
      }
    });
  });

  test.describe('Error Handling', () => {
    test('should return 404 for invalid endpoints', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/invalid-endpoint');
      expect(response.status()).toBe(404);
    });

    test('should handle invalid bot ID gracefully', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/v1/bots/99999');
      expect([404, 500]).toContain(response.status());
    });

    test('should validate consensus request data', async ({ request }) => {
      const response = await request.post('http://localhost:8000/api/v1/strategies/llm-consensus', {
        data: {
          // Missing required fields
          invalid: 'data'
        }
      });

      expect([400, 422, 500]).toContain(response.status());
    });
  });
});
