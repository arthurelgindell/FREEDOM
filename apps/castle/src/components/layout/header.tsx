'use client'

import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { healthCheck } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import {
  Wifi,
  WifiOff,
  Settings,
  Bell,
  Menu,
  X
} from 'lucide-react'
import Link from 'next/link'

interface HeaderProps {
  onMobileMenuToggle?: () => void
  isMobileMenuOpen?: boolean
}

export function Header({ onMobileMenuToggle, isMobileMenuOpen }: HeaderProps) {
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'error'>('disconnected')

  const { data: health, isError } = useQuery({
    queryKey: ['health'],
    queryFn: healthCheck,
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 2,
  })

  useEffect(() => {
    if (isError) {
      setConnectionStatus('error')
    } else if (health) {
      setConnectionStatus('connected')
    } else {
      setConnectionStatus('disconnected')
    }
  }, [health, isError])

  const getStatusBadge = () => {
    switch (connectionStatus) {
      case 'connected':
        return (
          <Badge variant="success" className="flex items-center gap-1">
            <Wifi className="h-3 w-3" />
            Online
          </Badge>
        )
      case 'error':
        return (
          <Badge variant="error" className="flex items-center gap-1">
            <WifiOff className="h-3 w-3" />
            Error
          </Badge>
        )
      default:
        return (
          <Badge variant="warning" className="flex items-center gap-1">
            <WifiOff className="h-3 w-3" />
            Connecting...
          </Badge>
        )
    }
  }

  const getSystemHealth = () => {
    if (!health) return null

    const isHealthy = health.status === 'healthy'
    return (
      <div className="hidden md:flex items-center gap-2 text-sm">
        <span className="text-muted-foreground">System:</span>
        <Badge variant={isHealthy ? 'success' : 'warning'}>
          {health.status}
        </Badge>
        <span className="text-muted-foreground">•</span>
        <span className="text-muted-foreground">
          KB: <span className={health.kb_service_status === 'healthy' ? 'text-green-600' : 'text-yellow-600'}>
            {health.kb_service_status}
          </span>
        </span>
      </div>
    )
  }

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center px-4 gap-4">
        {/* Mobile menu toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onMobileMenuToggle}
        >
          {isMobileMenuOpen ? (
            <X className="h-5 w-5" />
          ) : (
            <Menu className="h-5 w-5" />
          )}
        </Button>

        {/* Logo and title */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">F</span>
            </div>
            <div>
              <h1 className="text-lg font-semibold">FREEDOM Castle</h1>
              <p className="text-xs text-muted-foreground hidden sm:block">Operator Cockpit</p>
            </div>
          </div>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* System status */}
        {getSystemHealth()}

        {/* Connection status */}
        <div className="flex items-center gap-2">
          {getStatusBadge()}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="hidden md:flex">
            <Bell className="h-4 w-4" />
          </Button>
          <Link href="/settings">
            <Button variant="ghost" size="icon">
              <Settings className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Health details card (when there are issues) */}
      {health && health.status !== 'healthy' && (
        <div className="border-t bg-yellow-50 px-4 py-2">
          <Card className="bg-yellow-100 border-yellow-200">
            <div className="p-3">
              <div className="flex items-center gap-2 text-sm">
                <Badge variant="warning">Warning</Badge>
                <span>System is in degraded state</span>
                {health.kb_service_response_time_ms && (
                  <span className="text-muted-foreground">
                    • KB response: {health.kb_service_response_time_ms.toFixed(0)}ms
                  </span>
                )}
              </div>
            </div>
          </Card>
        </div>
      )}
    </header>
  )
}