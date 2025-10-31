/**
 * Connection Status Indicator
 * Displays connection health and last update time
 */

'use client'

import { useEffect, useState } from 'react'
import { useConsensusHealth } from '@/lib/hooks/useLiveData'

export type ConnectionState = 'connected' | 'slow' | 'disconnected'

export interface ConnectionStatusProps {
  className?: string
  showLabel?: boolean
  showTimestamp?: boolean
}

export function ConnectionStatus({
  className = '',
  showLabel = true,
  showTimestamp = true,
}: ConnectionStatusProps) {
  const { data, error, isValidating } = useConsensusHealth(60000)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')

  useEffect(() => {
    console.log('🔵 [ConnectionStatus] State update:', {
      hasData: !!data,
      hasError: !!error,
      isValidating,
      data,
      error
    })
    if (data && !error) {
      console.log('✅ [ConnectionStatus] Setting connected state')
      setLastUpdate(new Date())
      setConnectionState('connected')
    } else if (error) {
      console.log('❌ [ConnectionStatus] Setting disconnected state due to error:', error)
      setConnectionState('disconnected')
    } else {
      console.log('⏳ [ConnectionStatus] No data yet, staying disconnected')
    }
  }, [data, error, isValidating])

  // Determine if connection is slow (more than 2 minutes since last update)
  useEffect(() => {
    const interval = setInterval(() => {
      if (lastUpdate) {
        const timeSinceUpdate = Date.now() - lastUpdate.getTime()
        if (timeSinceUpdate > 120000) {
          // 2 minutes
          setConnectionState('slow')
        }
      }
    }, 10000) // Check every 10 seconds

    return () => clearInterval(interval)
  }, [lastUpdate])

  const getStatusColor = () => {
    switch (connectionState) {
      case 'connected':
        return 'bg-green-500'
      case 'slow':
        return 'bg-yellow-500'
      case 'disconnected':
        return 'bg-red-500'
    }
  }

  const getStatusText = () => {
    switch (connectionState) {
      case 'connected':
        return 'Connected'
      case 'slow':
        return 'Slow Connection'
      case 'disconnected':
        return 'Disconnected'
    }
  }

  const formatTimestamp = (date: Date | null) => {
    if (!date) return 'Never'

    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSecs = Math.floor(diffMs / 1000)
    const diffMins = Math.floor(diffSecs / 60)

    if (diffSecs < 60) {
      return `${diffSecs}s ago`
    } else if (diffMins < 60) {
      return `${diffMins}m ago`
    } else {
      return date.toLocaleTimeString()
    }
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Status Indicator */}
      <div className="relative">
        <div
          className={`h-3 w-3 rounded-full ${getStatusColor()} transition-colors duration-300`}
        />
        {isValidating && (
          <div
            className={`absolute inset-0 h-3 w-3 rounded-full ${getStatusColor()} animate-ping`}
          />
        )}
      </div>

      {/* Status Label */}
      {showLabel && (
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {getStatusText()}
        </span>
      )}

      {/* Last Update Timestamp */}
      {showTimestamp && lastUpdate && (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Updated {formatTimestamp(lastUpdate)}
        </span>
      )}
    </div>
  )
}

/**
 * Compact version for header/navbar
 */
export function ConnectionStatusCompact() {
  return (
    <ConnectionStatus
      className="px-3 py-1 rounded-full bg-gray-100 dark:bg-gray-800"
      showLabel={false}
      showTimestamp={true}
    />
  )
}

/**
 * Full version for dashboard
 */
export function ConnectionStatusFull() {
  const { data } = useConsensusHealth()

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <h3 className="text-sm font-semibold mb-3">System Status</h3>

      <ConnectionStatus showLabel showTimestamp className="mb-3" />

      {data && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-xs text-gray-600 dark:text-gray-400">
            <div className="flex justify-between mb-1">
              <span>Providers:</span>
              <span className="font-medium">
                {data.providers?.length || 0} active
              </span>
            </div>
            {data.providers?.map((provider: any, idx: number) => (
              <div key={idx} className="flex justify-between text-xs ml-2">
                <span>{provider.name || 'Unknown'}:</span>
                <span
                  className={
                    provider.status === 'healthy'
                      ? 'text-green-600'
                      : 'text-red-600'
                  }
                >
                  {provider.status || 'unknown'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
