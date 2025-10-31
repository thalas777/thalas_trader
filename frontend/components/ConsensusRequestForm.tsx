'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { ConsensusRequest } from '@/lib/types';

interface ConsensusRequestFormProps {
  onSubmit: (request: ConsensusRequest) => void;
  isLoading: boolean;
}

export default function ConsensusRequestForm({ onSubmit, isLoading }: ConsensusRequestFormProps) {
  const [pairs, setPairs] = useState<string[]>([]);
  const [timeframes, setTimeframes] = useState<string[]>([]);
  const [formData, setFormData] = useState({
    pair: 'BTC/USDT',
    timeframe: '1h',
    rsi: '50',
    macd: '0',
    macd_signal: '0',
    ema_fast: '0',
    ema_slow: '0',
    volume: '1000000',
    volume_sma: '1000000',
    bb_upper: '0',
    bb_middle: '0',
    bb_lower: '0',
    atr: '0',
  });
  const [useCustomWeights, setUseCustomWeights] = useState(false);
  const [providerWeights, setProviderWeights] = useState({
    anthropic: '1.0',
    openai: '1.0',
    gemini: '0.8',
    grok: '0.7',
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [pairsData, timeframesData] = await Promise.all([
          apiClient.getTradingPairs(),
          apiClient.getTimeframes(),
        ]);
        setPairs(pairsData);
        setTimeframes(timeframesData);
      } catch (error) {
        console.error('Error fetching form data:', error);
      }
    };
    fetchData();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const request: ConsensusRequest = {
      market_data: {
        pair: formData.pair,
        timeframe: formData.timeframe,
        rsi: parseFloat(formData.rsi) || undefined,
        macd: parseFloat(formData.macd) || undefined,
        macd_signal: parseFloat(formData.macd_signal) || undefined,
        ema_fast: parseFloat(formData.ema_fast) || undefined,
        ema_slow: parseFloat(formData.ema_slow) || undefined,
        volume: parseFloat(formData.volume) || undefined,
        volume_sma: parseFloat(formData.volume_sma) || undefined,
        bb_upper: parseFloat(formData.bb_upper) || undefined,
        bb_middle: parseFloat(formData.bb_middle) || undefined,
        bb_lower: parseFloat(formData.bb_lower) || undefined,
        atr: parseFloat(formData.atr) || undefined,
      },
    };

    if (useCustomWeights) {
      request.provider_weights = {
        anthropic: parseFloat(providerWeights.anthropic),
        openai: parseFloat(providerWeights.openai),
        gemini: parseFloat(providerWeights.gemini),
        grok: parseFloat(providerWeights.grok),
      };
    }

    onSubmit(request);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleWeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setProviderWeights(prev => ({ ...prev, [name]: value }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Trading Pair */}
        <div>
          <label htmlFor="pair" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Trading Pair
          </label>
          <select
            id="pair"
            name="pair"
            value={formData.pair}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          >
            {pairs.map(pair => (
              <option key={pair} value={pair}>{pair}</option>
            ))}
          </select>
        </div>

        {/* Timeframe */}
        <div>
          <label htmlFor="timeframe" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Timeframe
          </label>
          <select
            id="timeframe"
            name="timeframe"
            value={formData.timeframe}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          >
            {timeframes.map(tf => (
              <option key={tf} value={tf}>{tf}</option>
            ))}
          </select>
        </div>

        {/* RSI */}
        <div>
          <label htmlFor="rsi" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            RSI (0-100)
          </label>
          <input
            type="number"
            id="rsi"
            name="rsi"
            value={formData.rsi}
            onChange={handleInputChange}
            min="0"
            max="100"
            step="0.1"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>

        {/* MACD */}
        <div>
          <label htmlFor="macd" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            MACD
          </label>
          <input
            type="number"
            id="macd"
            name="macd"
            value={formData.macd}
            onChange={handleInputChange}
            step="0.01"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>

        {/* MACD Signal */}
        <div>
          <label htmlFor="macd_signal" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            MACD Signal
          </label>
          <input
            type="number"
            id="macd_signal"
            name="macd_signal"
            value={formData.macd_signal}
            onChange={handleInputChange}
            step="0.01"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>

        {/* Volume */}
        <div>
          <label htmlFor="volume" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Volume
          </label>
          <input
            type="number"
            id="volume"
            name="volume"
            value={formData.volume}
            onChange={handleInputChange}
            step="1000"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>
      </div>

      {/* Custom Provider Weights */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
        <div className="flex items-center mb-4">
          <input
            type="checkbox"
            id="useCustomWeights"
            checked={useCustomWeights}
            onChange={(e) => setUseCustomWeights(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="useCustomWeights" className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Use Custom Provider Weights
          </label>
        </div>

        {useCustomWeights && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(providerWeights).map(([provider, weight]) => (
              <div key={provider}>
                <label htmlFor={provider} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 capitalize">
                  {provider}
                </label>
                <input
                  type="number"
                  id={provider}
                  name={provider}
                  value={weight}
                  onChange={handleWeightChange}
                  min="0"
                  max="2"
                  step="0.1"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Submit Button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isLoading}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          {isLoading ? (
            <span className="flex items-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </span>
          ) : (
            'Get Consensus'
          )}
        </button>
      </div>
    </form>
  );
}
