'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api';
import { toast } from 'sonner';
import { Bot } from '@/lib/types';

interface SystemControlsProps {
  bots: Bot[];
  onUpdate: () => void;
}

export default function SystemControls({ bots, onUpdate }: SystemControlsProps) {
  const [isLoading, setIsLoading] = useState(false);

  const activeBotsCount = bots.filter(b => b.status === 'running').length;
  const allRunning = bots.length > 0 && activeBotsCount === bots.length;
  const someRunning = activeBotsCount > 0;

  const handleStartAll = async () => {
    if (bots.length === 0) {
      toast.error('No bots to start. Create a bot first.');
      return;
    }

    setIsLoading(true);
    try {
      const stoppedBots = bots.filter(b => b.status === 'stopped');

      const promises = stoppedBots.map(bot =>
        apiClient.startBot(bot.bot_id).catch(err => {
          console.error(`Failed to start bot ${bot.bot_id}:`, err);
          return null;
        })
      );

      await Promise.all(promises);

      toast.success(`Started ${stoppedBots.length} bot(s)`);
      onUpdate();
    } catch (error: any) {
      toast.error('Failed to start all bots');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopAll = async () => {
    setIsLoading(true);
    try {
      const runningBots = bots.filter(b => b.status === 'running');

      const promises = runningBots.map(bot =>
        apiClient.stopBot(bot.bot_id).catch(err => {
          console.error(`Failed to stop bot ${bot.bot_id}:`, err);
          return null;
        })
      );

      await Promise.all(promises);

      toast.success(`Stopped ${runningBots.length} bot(s)`);
      onUpdate();
    } catch (error: any) {
      toast.error('Failed to stop all bots');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 border border-blue-200 dark:border-gray-700 rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
            </svg>
            System Controls
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Manage all trading bots simultaneously
          </p>
        </div>

        <div className="flex gap-3">
          {/* Stop All Button */}
          <button
            onClick={handleStopAll}
            disabled={isLoading || !someRunning}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
            {isLoading ? 'Stopping...' : 'Stop All'}
          </button>

          {/* Start All Button */}
          <button
            onClick={handleStartAll}
            disabled={isLoading || allRunning}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {isLoading ? 'Starting...' : 'Start All'}
          </button>
        </div>
      </div>

      {/* Status Indicator */}
      <div className="mt-4 pt-4 border-t border-blue-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${someRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
              <span className="text-gray-700 dark:text-gray-300">
                {activeBotsCount} of {bots.length} bots active
              </span>
            </div>
          </div>

          {bots.length > 0 && (
            <div className="text-gray-600 dark:text-gray-400">
              Status: {allRunning ? '✅ All Running' : someRunning ? '⚠️ Partial' : '⏸️ All Stopped'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
