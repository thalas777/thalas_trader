'use client';

import { Trade } from '@/lib/types';
import { formatDistanceToNow } from 'date-fns';

interface TradesFeedProps {
  trades: Trade[];
  isLoading?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

export default function TradesFeed({ trades, isLoading, onLoadMore, hasMore }: TradesFeedProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatAmount = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 4,
      maximumFractionDigits: 8,
    }).format(value);
  };

  const getTradeTypeStyle = (type: string) => {
    if (type === 'buy') {
      return {
        bg: 'bg-green-50 dark:bg-green-900/20',
        border: 'border-green-200 dark:border-green-800',
        text: 'text-green-600 dark:text-green-400',
        icon: '🟢',
      };
    }
    return {
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      text: 'text-red-600 dark:text-red-400',
      icon: '🔴',
    };
  };

  if (isLoading && trades.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-32 animate-pulse"></div>
        </div>
        <div className="p-6 space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
        <div className="text-6xl mb-4">📊</div>
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          No Trades Yet
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Trades will appear here once your bots start trading
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Recent Trades</h2>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {trades.length} trade{trades.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="p-6 space-y-4 max-h-[600px] overflow-y-auto">
        {trades.map((trade) => {
          const typeStyle = getTradeTypeStyle(trade.type);
          const hasProfit = trade.profit !== null && trade.profit !== undefined;

          return (
            <div
              key={trade.trade_id}
              className={`p-4 rounded-lg border ${typeStyle.border} ${typeStyle.bg} hover:shadow-md transition-shadow`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{typeStyle.icon}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-lg font-bold uppercase ${typeStyle.text}`}>
                        {trade.type}
                      </span>
                      <span className="text-lg font-mono font-semibold text-gray-900 dark:text-white">
                        {trade.pair}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {trade.bot_name}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {formatDistanceToNow(new Date(trade.timestamp), { addSuffix: true })}
                  </div>
                  <div className="text-xs text-gray-400 dark:text-gray-500">
                    {new Date(trade.timestamp).toLocaleString()}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Amount</div>
                  <div className="text-sm font-mono text-gray-900 dark:text-white">
                    {formatAmount(trade.amount)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Price</div>
                  <div className="text-sm font-semibold text-gray-900 dark:text-white">
                    {formatCurrency(trade.price)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Value</div>
                  <div className="text-sm font-semibold text-gray-900 dark:text-white">
                    {formatCurrency(trade.amount * trade.price)}
                  </div>
                </div>
                {hasProfit && (
                  <div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">P&L</div>
                    <div
                      className={`text-sm font-bold ${
                        (trade.profit || 0) >= 0
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {formatCurrency(trade.profit || 0)}
                      {trade.profit_percentage && (
                        <span className="text-xs ml-1">
                          ({(trade.profit || 0) >= 0 ? '+' : ''}
                          {trade.profit_percentage.toFixed(2)}%)
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-4">
                    <span className="text-gray-600 dark:text-gray-400">
                      Decision: <span className="font-semibold">{trade.consensus_decision}</span>
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">
                      Confidence:{' '}
                      <span className="font-semibold">
                        {(trade.consensus_confidence * 100).toFixed(1)}%
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {hasMore && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-center">
          <button
            onClick={onLoadMore}
            disabled={isLoading}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
}
