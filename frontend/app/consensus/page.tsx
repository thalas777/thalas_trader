import type { Metadata } from 'next';
import ConsensusView from '@/components/ConsensusView';

export const metadata: Metadata = {
  title: 'Consensus Signals - Thalas Trader',
  description: 'Multi-LLM consensus trading signals powered by Anthropic, OpenAI, Gemini, and Grok',
};

export default function ConsensusPage() {
  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            Multi-LLM Consensus Trading Signals
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400">
            Get trading decisions powered by multiple AI providers with consensus voting
          </p>
        </div>

        <ConsensusView />
      </div>
    </main>
  );
}
