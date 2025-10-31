'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface PerformanceDataPoint {
  timestamp: string;
  balance: number;
  profit: number;
}

interface PerformanceChartProps {
  data: PerformanceDataPoint[];
  isLoading?: boolean;
}

export default function PerformanceChart({ data, isLoading }: PerformanceChartProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-6 animate-pulse"></div>
        <div className="h-80 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
        <div className="text-6xl mb-4">📈</div>
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          No Performance Data
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Performance charts will appear once you have trading data
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Performance</h2>
      </div>

      <div className="p-6">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatDate}
              stroke="#9CA3AF"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              yAxisId="left"
              tickFormatter={formatCurrency}
              stroke="#9CA3AF"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tickFormatter={formatCurrency}
              stroke="#9CA3AF"
              style={{ fontSize: '12px' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '8px',
                color: '#F3F4F6',
              }}
              labelFormatter={formatDate}
              formatter={(value: number) => formatCurrency(value)}
            />
            <Legend
              wrapperStyle={{
                paddingTop: '20px',
              }}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="balance"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={{ fill: '#3B82F6', r: 4 }}
              activeDot={{ r: 6 }}
              name="Portfolio Balance"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="profit"
              stroke="#10B981"
              strokeWidth={2}
              dot={{ fill: '#10B981', r: 4 }}
              activeDot={{ r: 6 }}
              name="Cumulative Profit"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="p-6 border-t border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Current Balance</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(data[data.length - 1]?.balance || 0)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Total Profit</div>
            <div
              className={`text-xl font-bold ${
                (data[data.length - 1]?.profit || 0) >= 0
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-red-600 dark:text-red-400'
              }`}
            >
              {formatCurrency(data[data.length - 1]?.profit || 0)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Data Points</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">{data.length}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
