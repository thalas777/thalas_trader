import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Welcome to Thalas Trader
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
            Multi-LLM Consensus Trading Bot with Anthropic, OpenAI, Gemini, and Grok
          </p>
          <Link
            href="/consensus"
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
          >
            View Consensus Signals
          </Link>
        </div>
      </div>
    </main>
  );
}
