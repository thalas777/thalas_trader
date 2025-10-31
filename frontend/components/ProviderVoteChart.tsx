'use client';

import { ProviderResponse } from '@/lib/types';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ProviderVoteChartProps {
  providers: ProviderResponse[];
  voteBreakdown: { [key: string]: number };
}

const DECISION_COLORS: { [key: string]: string } = {
  BUY: '#10b981',   // green
  SELL: '#ef4444',  // red
  HOLD: '#f59e0b',  // yellow/orange
};

const PROVIDER_COLORS: { [key: string]: string } = {
  anthropic: '#10b981',
  openai: '#3b82f6',
  gemini: '#8b5cf6',
  grok: '#ec4899',
};

export default function ProviderVoteChart({ providers, voteBreakdown }: ProviderVoteChartProps) {
  // Prepare data for pie chart (vote distribution)
  const pieData = Object.entries(voteBreakdown).map(([decision, count]) => ({
    name: decision,
    value: count,
    color: DECISION_COLORS[decision] || '#6b7280',
  }));

  // Prepare data for bar chart (confidence levels)
  const barData = providers.map(p => ({
    name: p.provider.charAt(0).toUpperCase() + p.provider.slice(1),
    confidence: (p.confidence * 100).toFixed(1),
    decision: p.decision,
    color: PROVIDER_COLORS[p.provider.toLowerCase()] || '#6b7280',
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Pie Chart - Vote Distribution */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Vote Distribution</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={(props: any) => {
                const { name, percent } = props;
                return `${name} ${(percent * 100).toFixed(0)}%`;
              }}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              {pieData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Bar Chart - Confidence Levels */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Provider Confidence Levels</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={barData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis domain={[0, 100]} label={{ value: 'Confidence %', angle: -90, position: 'insideLeft' }} />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white dark:bg-gray-700 p-3 rounded shadow-lg border border-gray-200 dark:border-gray-600">
                      <p className="font-semibold text-gray-900 dark:text-white">{data.name}</p>
                      <p className="text-sm text-gray-600 dark:text-gray-300">Decision: <span className="font-medium">{data.decision}</span></p>
                      <p className="text-sm text-gray-600 dark:text-gray-300">Confidence: <span className="font-medium">{data.confidence}%</span></p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="confidence" fill="#3b82f6">
              {barData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Provider Details Table */}
      <div className="lg:col-span-2 bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Individual Provider Responses</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Provider</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Decision</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Confidence</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Risk</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Latency</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Reasoning</th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {providers.map((provider, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div
                        className="w-3 h-3 rounded-full mr-2"
                        style={{ backgroundColor: PROVIDER_COLORS[provider.provider.toLowerCase()] || '#6b7280' }}
                      />
                      <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                        {provider.provider}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                      style={{
                        backgroundColor: `${DECISION_COLORS[provider.decision]}20`,
                        color: DECISION_COLORS[provider.decision]
                      }}
                    >
                      {provider.decision}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {(provider.confidence * 100).toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      provider.risk_level === 'low' ? 'bg-green-100 text-green-800' :
                      provider.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {provider.risk_level}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {provider.latency.toFixed(2)}s
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">
                    {provider.reasoning.substring(0, 100)}...
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
