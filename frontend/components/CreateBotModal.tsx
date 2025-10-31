'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api';
import { toast } from 'sonner';

interface CreateBotModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CreateBotModal({ isOpen, onClose, onSuccess }: CreateBotModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    pair: 'BTC/USD',
    strategy: 'LLM_Consensus_Strategy',
    initialBalance: '10000',
    positionSize: '0.15',
  });
  const [autoMode, setAutoMode] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const tradingPairs = [
    'BTC/USD',
    'ETH/USD',
    'BNB/USD',
    'SOL/USD',
    'ADA/USD',
    'XRP/USD',
    'DOT/USD',
    'AVAX/USD',
  ];

  const strategies = [
    { value: 'LLM_Consensus_Strategy', label: 'Multi-LLM Consensus' },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    console.log('🔵 Form submission started');
    console.log('Form data:', formData);
    console.log('Auto mode:', autoMode);

    if (!formData.name.trim()) {
      console.log('❌ Bot name is empty');
      toast.error('Please enter a bot name');
      return;
    }

    setIsSubmitting(true);
    console.log('🔄 Submitting bot creation...');

    try {
      const botData: any = {
        name: formData.name,
        strategy: formData.strategy,
        initial_balance: parseFloat(formData.initialBalance),
        position_size: parseFloat(formData.positionSize),
        auto_mode: autoMode,
      };

      // Only include pair if not in auto mode
      if (!autoMode) {
        botData.pair = formData.pair;
      }

      console.log('📤 Sending bot data:', botData);

      const response = await apiClient.createBot(botData);

      console.log('✅ Bot created successfully:', response);

      const modeText = autoMode ? 'with autonomous pair selection' : 'successfully';
      toast.success(`Bot "${formData.name}" created ${modeText}!`);
      onSuccess();
      handleClose();
    } catch (error: any) {
      console.error('❌ Bot creation failed:', error);
      console.error('Error response:', error.response);
      console.error('Error message:', error.message);
      const errorMessage = error.response?.data?.error || error.message || 'Failed to create bot';
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
      console.log('🏁 Form submission completed');
    }
  };

  const handleClose = () => {
    setFormData({
      name: '',
      pair: 'BTC/USD',
      strategy: 'LLM_Consensus_Strategy',
      initialBalance: '10000',
      positionSize: '0.15',
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Create New Trading Bot
            </h2>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Bot Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Bot Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., My BTC Bot"
                required
              />
            </div>

            {/* Auto Mode Toggle */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="text-2xl">🤖</div>
                  <div>
                    <div className="font-semibold text-gray-900 dark:text-white">
                      Autonomous Trading Mode
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      Let AI analyze markets and select best trading pairs automatically
                    </div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={autoMode}
                    onChange={(e) => setAutoMode(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-14 h-8 bg-gray-300 dark:bg-gray-600 rounded-full peer peer-checked:bg-blue-600 transition-colors"></div>
                  <div className="absolute left-1 top-1 w-6 h-6 bg-white rounded-full transition-transform peer-checked:translate-x-6"></div>
                </div>
              </label>
            </div>

            {/* Trading Pair - Only show if not in auto mode */}
            {!autoMode && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Trading Pair *
                </label>
                <select
                  value={formData.pair}
                  onChange={(e) => setFormData({ ...formData, pair: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {tradingPairs.map((pair) => (
                    <option key={pair} value={pair}>
                      {pair}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Auto Mode Info */}
            {autoMode && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div className="text-sm text-blue-900 dark:text-blue-200">
                    <p className="font-semibold mb-1">How Autonomous Mode Works:</p>
                    <ul className="list-disc list-inside space-y-1 text-blue-800 dark:text-blue-300">
                      <li>Bot scans multiple trading pairs in real-time</li>
                      <li>Multi-LLM consensus evaluates market opportunities</li>
                      <li>Automatically selects and trades the best opportunities</li>
                      <li>Can switch between pairs based on market conditions</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Strategy */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Strategy *
              </label>
              <select
                value={formData.strategy}
                onChange={(e) => setFormData({ ...formData, strategy: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {strategies.map((strategy) => (
                  <option key={strategy.value} value={strategy.value}>
                    {strategy.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Initial Balance */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Initial Balance (USD) *
              </label>
              <input
                type="number"
                step="0.01"
                min="100"
                value={formData.initialBalance}
                onChange={(e) => setFormData({ ...formData, initialBalance: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Starting balance for paper trading
              </p>
            </div>

            {/* Position Size */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Position Size (0.01 - 1.0) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max="1.0"
                value={formData.positionSize}
                onChange={(e) => setFormData({ ...formData, positionSize: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Percentage of balance to use per trade (e.g., 0.15 = 15%)
              </p>
            </div>

            {/* Info Box */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex">
                <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                <div className="text-sm text-blue-700 dark:text-blue-300">
                  Bot will use Multi-LLM consensus (Grok, Gemini, DeepSeek) for trading decisions
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={handleClose}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? 'Creating...' : 'Create Bot'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
