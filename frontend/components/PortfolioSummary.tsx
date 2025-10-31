'use client';

import { PortfolioSummary as PortfolioData } from '@/lib/types';

interface PortfolioSummaryProps {
  data: PortfolioData;
  isLoading?: boolean;
}

export default function PortfolioSummary({ data, isLoading }: PortfolioSummaryProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-3"></div>
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
          </div>
        ))}
      </div>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const getProfitColor = (value: number) => {
    if (value > 0) return 'text-green-600 dark:text-green-400';
    if (value < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const metrics = [
    {
      label: 'Total Balance',
      value: formatCurrency(data.total_balance),
      subtitle: `Cash: ${formatCurrency(data.cash_balance)}`,
      icon: '💰',
    },
    {
      label: 'Position Value',
      value: formatCurrency(data.position_value),
      subtitle: `${data.open_positions} open position${data.open_positions !== 1 ? 's' : ''}`,
      icon: '📊',
    },
    {
      label: 'Total P&L',
      value: formatCurrency(data.total_profit),
      subtitle: formatPercent(data.profit_percentage),
      valueColor: getProfitColor(data.total_profit),
      icon: '📈',
    },
    {
      label: '24h P&L',
      value: formatCurrency(data.profit_24h),
      subtitle: 'Last 24 hours',
      valueColor: getProfitColor(data.profit_24h),
      icon: '⚡',
    },
    {
      label: 'Win Rate',
      value: `${data.win_rate.toFixed(1)}%`,
      subtitle: `${data.total_trades} total trades`,
      icon: '🎯',
    },
    {
      label: 'Active Bots',
      value: `${data.active_bots}/${data.total_bots}`,
      subtitle: 'Currently running',
      icon: '🤖',
    },
    {
      label: 'Total Trades',
      value: data.total_trades.toString(),
      subtitle: 'All time',
      icon: '🔄',
    },
    {
      label: 'Open Positions',
      value: data.open_positions.toString(),
      subtitle: 'Active trades',
      icon: '📍',
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Portfolio Overview</h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Updated: {new Date().toLocaleTimeString()}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric, index) => (
          <div
            key={index}
            className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200 dark:border-gray-700"
          >
            <div className="flex items-start justify-between mb-2">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                {metric.label}
              </p>
              <span className="text-2xl">{metric.icon}</span>
            </div>
            <p
              className={`text-2xl font-bold mb-1 ${
                metric.valueColor || 'text-gray-900 dark:text-white'
              }`}
            >
              {metric.value}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">{metric.subtitle}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
