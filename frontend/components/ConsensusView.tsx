'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api';
import { ConsensusRequest, ConsensusResult, ConsensusSignal } from '@/lib/types';
import ConsensusRequestForm from './ConsensusRequestForm';
import ProviderVoteChart from './ProviderVoteChart';
import ProviderHealthStatus from './ProviderHealthStatus';
import ConsensusSignalFeed from './ConsensusSignalFeed';

export default function ConsensusView() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ConsensusResult | null>(null);
  const [signalHistory, setSignalHistory] = useState<ConsensusSignal[]>([]);

  const handleSubmit = async (request: ConsensusRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const consensusResult = await apiClient.getConsensus(request);
      setResult(consensusResult);

      // Add to signal history
      const newSignal: ConsensusSignal = {
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        pair: request.market_data.pair,
        timeframe: request.market_data.timeframe,
        decision: consensusResult.decision,
        confidence: consensusResult.confidence,
        agreement_score: consensusResult.consensus_metadata.agreement_score,
        risk_level: consensusResult.risk_level,
      };
      setSignalHistory(prev => [newSignal, ...prev].slice(0, 20)); // Keep last 20 signals
    } catch (err: any) {
      console.error('Error getting consensus:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to get consensus. Please check if the backend is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'BUY':
        return 'text-green-600 dark:text-green-400';
      case 'SELL':
        return 'text-red-600 dark:text-red-400';
      case 'HOLD':
        return 'text-yellow-600 dark:text-yellow-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="space-y-6">
      {/* Provider Health Status */}
      <ProviderHealthStatus />

      {/* Request Form */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Request Consensus Signal</h2>
        <ConsensusRequestForm onSubmit={handleSubmit} isLoading={isLoading} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="text-sm font-medium text-red-800 dark:text-red-300">Error</h3>
              <p className="mt-1 text-sm text-red-700 dark:text-red-400">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Consensus Result Display */}
      {result && (
        <div className="space-y-6">
          {/* Summary Card */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 p-6 rounded-lg shadow-lg border border-blue-200 dark:border-gray-700">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Consensus Result</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Decision</p>
                <p className={`text-3xl font-bold ${getDecisionColor(result.decision)}`}>
                  {result.decision}
                </p>
              </div>

              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Confidence</p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                  {(result.confidence * 100).toFixed(1)}%
                </p>
              </div>

              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Agreement</p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                  {(result.consensus_metadata.agreement_score * 100).toFixed(0)}%
                </p>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow mb-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Reasoning</p>
              <p className="text-gray-900 dark:text-white">{result.reasoning}</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow">
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Risk Level</p>
                <p className={`font-semibold capitalize ${
                  result.risk_level === 'low' ? 'text-green-600' :
                  result.risk_level === 'medium' ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {result.risk_level}
                </p>
              </div>

              {result.suggested_stop_loss && (
                <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Stop Loss</p>
                  <p className="font-semibold text-gray-900 dark:text-white">
                    ${result.suggested_stop_loss.toFixed(2)}
                  </p>
                </div>
              )}

              {result.suggested_take_profit && (
                <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Take Profit</p>
                  <p className="font-semibold text-gray-900 dark:text-white">
                    ${result.suggested_take_profit.toFixed(2)}
                  </p>
                </div>
              )}

              <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow">
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Providers</p>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {result.consensus_metadata.participating_providers} / {result.consensus_metadata.total_providers}
                </p>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-gray-600 dark:text-gray-400">Total Latency</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {result.consensus_metadata.total_latency.toFixed(2)}s
                  </p>
                </div>
                <div>
                  <p className="text-gray-600 dark:text-gray-400">Total Cost</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    ${result.consensus_metadata.total_cost.toFixed(4)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-600 dark:text-gray-400">Tokens Used</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {result.consensus_metadata.total_tokens.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Vote Visualization */}
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Provider Analysis</h2>
            <ProviderVoteChart
              providers={result.consensus_metadata.provider_responses}
              voteBreakdown={result.consensus_metadata.vote_breakdown}
            />
          </div>
        </div>
      )}

      {/* Signal History */}
      {signalHistory.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Signal History</h2>
          <ConsensusSignalFeed signals={signalHistory} />
        </div>
      )}
    </div>
  );
}
