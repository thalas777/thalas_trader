import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-4">
            Welcome to Thalas Trader
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 mb-2">
            Multi-LLM Consensus Trading System
          </p>
          <p className="text-lg text-gray-500 dark:text-gray-500">
            Powered by Grok, Gemini, and DeepSeek
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Dashboard Card */}
          <Link href="/dashboard">
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-blue-900/20 p-8 rounded-xl shadow-lg hover:shadow-xl transition-all border border-blue-200 dark:border-blue-800 cursor-pointer">
              <div className="text-5xl mb-4">📊</div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
                Trading Dashboard
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Monitor your bots, view performance metrics, and manage trading operations in real-time.
              </p>
              <div className="flex items-center text-blue-600 dark:text-blue-400 font-semibold">
                Open Dashboard
                <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </Link>

          {/* Consensus Card */}
          <Link href="/consensus">
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-gray-800 dark:to-purple-900/20 p-8 rounded-xl shadow-lg hover:shadow-xl transition-all border border-purple-200 dark:border-purple-800 cursor-pointer">
              <div className="text-5xl mb-4">🤖</div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
                Consensus Signals
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Request trading signals with multi-LLM consensus voting and confidence scoring.
              </p>
              <div className="flex items-center text-purple-600 dark:text-purple-400 font-semibold">
                Get Signals
                <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </Link>
        </div>

        <div className="mt-16 text-center">
          <div className="inline-flex items-center gap-4 bg-white dark:bg-gray-800 px-6 py-4 rounded-lg shadow-md">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-gray-600 dark:text-gray-400">System Online</span>
            </div>
            <div className="h-4 w-px bg-gray-300 dark:bg-gray-700"></div>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              3 LLM Providers Active
            </span>
          </div>
        </div>
      </div>
    </main>
  );
}
