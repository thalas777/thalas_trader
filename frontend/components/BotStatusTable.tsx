'use client';

import { Bot } from '@/lib/types';
import { apiClient } from '@/lib/api';
import { useState } from 'react';
import { toast } from 'sonner';
import CreateBotModal from './CreateBotModal';

interface BotStatusTableProps {
  bots: Bot[];
  onBotUpdate?: () => void;
  isLoading?: boolean;
}

export default function BotStatusTable({ bots, onBotUpdate, isLoading }: BotStatusTableProps) {
  const [actionLoading, setActionLoading] = useState<{ [key: number]: boolean }>({});
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const handleStartBot = async (botId: number) => {
    setActionLoading({ ...actionLoading, [botId]: true });
    try {
      const result = await apiClient.startBot(botId);
      toast.success(`Bot started: ${result.message}`);
      onBotUpdate?.();
    } catch (error: any) {
      toast.error(`Failed to start bot: ${error.message}`);
    } finally {
      setActionLoading({ ...actionLoading, [botId]: false });
    }
  };

  const handleStopBot = async (botId: number) => {
    setActionLoading({ ...actionLoading, [botId]: true });
    try {
      const result = await apiClient.stopBot(botId);
      toast.success(`Bot stopped: ${result.message}`);
      onBotUpdate?.();
    } catch (error: any) {
      toast.error(`Failed to stop bot: ${error.message}`);
    } finally {
      setActionLoading({ ...actionLoading, [botId]: false });
    }
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      running: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      stopped: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
      paused: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    };

    return (
      <span
        className={`px-3 py-1 rounded-full text-xs font-semibold uppercase ${
          styles[status as keyof typeof styles] || styles.stopped
        }`}
      >
        {status}
      </span>
    );
  };

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

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-32 animate-pulse"></div>
        </div>
        <div className="p-6 space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (bots.length === 0) {
    return (
      <div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
          <div className="text-6xl mb-4">🤖</div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No Bots Running
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Create your first trading bot to get started
          </p>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            Create Bot
          </button>
        </div>
        <CreateBotModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSuccess={() => onBotUpdate?.()}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Trading Bots</h2>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Bot
          </button>
        </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-900/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Bot Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Pair
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Strategy
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Profit
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Trades
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {bots.map((bot) => (
              <tr
                key={bot.bot_id}
                className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {bot.name}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(bot.status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900 dark:text-white font-mono">
                    {bot.pair}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {bot.strategy}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <div className={`text-sm font-semibold ${getProfitColor(bot.profit)}`}>
                    {formatCurrency(bot.profit)}
                  </div>
                  <div className={`text-xs ${getProfitColor(bot.profit)}`}>
                    {formatPercent(bot.profit_percentage)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {bot.trades_count}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                  <div className="flex justify-end gap-2">
                    {bot.status === 'running' ? (
                      <button
                        onClick={() => handleStopBot(bot.bot_id)}
                        disabled={actionLoading[bot.bot_id]}
                        className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {actionLoading[bot.bot_id] ? '...' : 'Stop'}
                      </button>
                    ) : (
                      <button
                        onClick={() => handleStartBot(bot.bot_id)}
                        disabled={actionLoading[bot.bot_id]}
                        className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {actionLoading[bot.bot_id] ? '...' : 'Start'}
                      </button>
                    )}
                    <button className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors">
                      Details
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </div>

      <CreateBotModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => onBotUpdate?.()}
      />
    </div>
  );
}
