'use client';

import { useState, useEffect } from 'react';
import useSWR from 'swr';
import { apiClient } from '@/lib/api';
import { toast } from 'sonner';
import PortfolioSummary from './PortfolioSummary';
import BotStatusTable from './BotStatusTable';
import TradesFeed from './TradesFeed';
import PerformanceChart from './PerformanceChart';
import SystemControls from './SystemControls';
import { ConnectionStatus } from './ConnectionStatus';

export default function Dashboard() {
  const [tradesLimit, setTradesLimit] = useState(20);

  // Fetch portfolio summary
  const {
    data: portfolioData,
    error: portfolioError,
    mutate: mutatePortfolio,
  } = useSWR('portfolio', () => apiClient.getPortfolioSummary(), {
    refreshInterval: 30000, // Refresh every 30 seconds
    onError: (error) => {
      console.error('Error fetching portfolio:', error);
    },
  });

  // Fetch bots
  const {
    data: botsData,
    error: botsError,
    mutate: mutateBots,
  } = useSWR('bots', () => apiClient.getBots(), {
    refreshInterval: 30000,
    onError: (error) => {
      console.error('Error fetching bots:', error);
    },
  });

  // Fetch trades
  const {
    data: tradesData,
    error: tradesError,
    mutate: mutateTrades,
  } = useSWR(['trades', tradesLimit], () => apiClient.getTrades(tradesLimit, 0), {
    refreshInterval: 30000,
    onError: (error) => {
      console.error('Error fetching trades:', error);
    },
  });

  // Fetch performance data
  const {
    data: performanceData,
    error: performanceError,
  } = useSWR('performance', () => apiClient.getPerformance(), {
    refreshInterval: 60000, // Refresh every minute
    onError: (error) => {
      console.error('Error fetching performance:', error);
    },
  });

  // Show connection errors
  useEffect(() => {
    if (portfolioError || botsError || tradesError || performanceError) {
      const error = portfolioError || botsError || tradesError || performanceError;
      if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
        toast.error('Cannot connect to backend server. Please ensure it is running.');
      }
    }
  }, [portfolioError, botsError, tradesError, performanceError]);

  const handleBotUpdate = () => {
    mutateBots();
    mutatePortfolio();
  };

  const handleLoadMoreTrades = () => {
    setTradesLimit((prev) => prev + 20);
  };

  // Prepare performance chart data from portfolio and trades
  const performanceChartData = performanceData?.equity_curve || [];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Trading Dashboard
              </h1>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Multi-LLM Consensus Trading System
              </p>
            </div>
            <ConnectionStatus />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Portfolio Summary */}
          <PortfolioSummary
            data={portfolioData || {
              total_balance: 0,
              cash_balance: 0,
              position_value: 0,
              total_profit: 0,
              profit_percentage: 0,
              profit_24h: 0,
              total_trades: 0,
              win_rate: 0,
              active_bots: 0,
              total_bots: 0,
              open_positions: 0,
            }}
            isLoading={!portfolioData && !portfolioError}
          />

          {/* System Controls */}
          <SystemControls
            bots={botsData || []}
            onUpdate={() => {
              mutateBots();
              mutatePortfolio();
            }}
          />

          {/* Performance Chart */}
          <PerformanceChart
            data={performanceChartData}
            isLoading={!performanceData && !performanceError}
          />

          {/* Bots Table */}
          <BotStatusTable
            bots={botsData || []}
            onBotUpdate={handleBotUpdate}
            isLoading={!botsData && !botsError}
          />

          {/* Trades Feed */}
          <TradesFeed
            trades={tradesData?.trades || []}
            isLoading={!tradesData && !tradesError}
            onLoadMore={handleLoadMoreTrades}
            hasMore={(tradesData?.trades.length || 0) >= tradesLimit}
          />
        </div>
      </div>

      {/* Quick Actions FAB */}
      <div className="fixed bottom-8 right-8 flex flex-col gap-4">
        <button
          onClick={() => {
            mutatePortfolio();
            mutateBots();
            mutateTrades();
          }}
          className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-full shadow-lg hover:shadow-xl transition-all"
          title="Refresh All Data"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
