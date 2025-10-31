'use client';

import { useEffect, useState } from 'react';
import useSWR from 'swr';
import { apiClient } from '@/lib/api';
import { ProviderHealth } from '@/lib/types';

export default function ProviderHealthStatus() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const { data: providers, error, isLoading } = useSWR<ProviderHealth[]>(
    'provider-health',
    () => apiClient.getProviderHealth(),
    {
      refreshInterval: 30000, // Refresh every 30 seconds
      revalidateOnFocus: true,
    }
  );

  if (!mounted) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Provider Health Status</h3>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600 dark:text-gray-400">Loading provider status...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Provider Health Status</h3>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
          <p className="text-sm text-red-800 dark:text-red-300">Failed to load provider health status</p>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return {
          bg: 'bg-green-100 dark:bg-green-900/20',
          text: 'text-green-800 dark:text-green-300',
          border: 'border-green-200 dark:border-green-800',
          dot: 'bg-green-500',
        };
      case 'degraded':
        return {
          bg: 'bg-yellow-100 dark:bg-yellow-900/20',
          text: 'text-yellow-800 dark:text-yellow-300',
          border: 'border-yellow-200 dark:border-yellow-800',
          dot: 'bg-yellow-500',
        };
      case 'unavailable':
        return {
          bg: 'bg-red-100 dark:bg-red-900/20',
          text: 'text-red-800 dark:text-red-300',
          border: 'border-red-200 dark:border-red-800',
          dot: 'bg-red-500',
        };
      default:
        return {
          bg: 'bg-gray-100 dark:bg-gray-700',
          text: 'text-gray-800 dark:text-gray-300',
          border: 'border-gray-200 dark:border-gray-600',
          dot: 'bg-gray-500',
        };
    }
  };

  const healthyCount = providers?.filter(p => p.status === 'healthy').length || 0;
  const totalCount = providers?.length || 0;

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Provider Health Status</h3>
        <div className="flex items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {healthyCount} / {totalCount} Healthy
          </span>
          <div className="ml-2 relative">
            <div className={`w-3 h-3 rounded-full ${healthyCount === totalCount ? 'bg-green-500' : healthyCount > 0 ? 'bg-yellow-500' : 'bg-red-500'}`}>
              <div className={`absolute inset-0 rounded-full ${healthyCount === totalCount ? 'bg-green-500' : healthyCount > 0 ? 'bg-yellow-500' : 'bg-red-500'} animate-ping opacity-75`}></div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {providers && providers.length > 0 ? (
          providers.map((provider, idx) => {
            const colors = getStatusColor(provider.status);
            return (
              <div
                key={idx}
                className={`${colors.bg} ${colors.border} border rounded-lg p-4 transition-all hover:shadow-md`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className={`font-semibold ${colors.text} capitalize`}>
                    {provider.name}
                  </h4>
                  <div className={`w-2 h-2 rounded-full ${colors.dot}`}></div>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Status:{' '}
                    <span className={`font-medium ${colors.text} capitalize`}>
                      {provider.status}
                    </span>
                  </p>
                  {provider.latency && (
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      Latency:{' '}
                      <span className={`font-medium ${colors.text}`}>
                        {provider.latency.toFixed(2)}s
                      </span>
                    </p>
                  )}
                  {provider.last_check && (
                    <p className="text-xs text-gray-500 dark:text-gray-500">
                      Last check: {new Date(provider.last_check).toLocaleTimeString()}
                    </p>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div className="col-span-full text-center py-8">
            <p className="text-gray-500 dark:text-gray-400">No provider data available</p>
          </div>
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>Auto-refreshing every 30s</span>
          <span>Last updated: {new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}
