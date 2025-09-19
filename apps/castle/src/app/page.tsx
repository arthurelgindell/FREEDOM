'use client'

import { useQuery } from '@tanstack/react-query'
import { healthCheck } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/lib/utils'
import {
  Activity,
  Server,
  Database,
  Wifi,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock
} from 'lucide-react'
import Link from 'next/link'

export default function DashboardPage() {
  const {
    data: health,
    isLoading,
    isError,
    refetch,
    dataUpdatedAt
  } = useQuery({
    queryKey: ['health'],
    queryFn: healthCheck,
    refetchInterval: 10000, // Refetch every 10 seconds
    retry: 2,
  })

  const getSystemStatus = () => {
    if (isLoading) return { status: 'loading', color: 'warning', icon: Clock }
    if (isError) return { status: 'error', color: 'error', icon: AlertTriangle }
    if (health?.status === 'healthy') return { status: 'healthy', color: 'success', icon: CheckCircle }
    return { status: 'degraded', color: 'warning', icon: AlertTriangle }
  }

  const systemStatus = getSystemStatus()

  const services = [
    {
      name: 'API Gateway',
      status: health ? 'healthy' : (isError ? 'error' : 'unknown'),
      endpoint: 'localhost:8080',
      responseTime: health ? '< 50ms' : 'N/A'
    },
    {
      name: 'Knowledge Base',
      status: health?.kb_service_status || (isError ? 'error' : 'unknown'),
      endpoint: 'kb-service:8000',
      responseTime: health?.kb_service_response_time_ms ? `${health.kb_service_response_time_ms.toFixed(0)}ms` : 'N/A'
    },
    {
      name: 'PostgreSQL',
      status: health ? (health.kb_service_status === 'healthy' ? 'healthy' : 'degraded') : 'unknown',
      endpoint: 'postgres:5432',
      responseTime: 'N/A'
    },
    {
      name: 'MLX Server',
      status: 'unknown',
      endpoint: 'localhost:8000',
      responseTime: 'N/A'
    }
  ]

  const stats = [
    {
      name: 'System Uptime',
      value: health ? `${Math.floor(health.uptime_seconds / 60)} min` : 'N/A',
      icon: Clock,
      description: 'API Gateway uptime'
    },
    {
      name: 'Services Online',
      value: `${services.filter(s => s.status === 'healthy').length}/${services.length}`,
      icon: Server,
      description: 'Active services'
    },
    {
      name: 'KB Status',
      value: health?.kb_service_status || 'Unknown',
      icon: Database,
      description: 'Knowledge base health'
    },
    {
      name: 'Last Check',
      value: dataUpdatedAt ? formatDate(new Date(dataUpdatedAt)).split(' ')[1] : 'Never',
      icon: RefreshCw,
      description: 'Health check timestamp'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            FREEDOM Platform operational overview
          </p>
        </div>
        <Button
          onClick={() => refetch()}
          variant="outline"
          className="flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* System Status Alert */}
      {(isError || health?.status !== 'healthy') && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <CardTitle className="text-yellow-800">System Alert</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {isError ? (
              <p className="text-yellow-700">
                Unable to connect to API Gateway. Check if services are running.
              </p>
            ) : (
              <p className="text-yellow-700">
                System is in degraded state. Some services may be experiencing issues.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.name}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              System Status
            </CardTitle>
            <CardDescription>
              Overall platform health and performance
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="font-medium">Overall Status</span>
              <Badge
                variant={systemStatus.color as 'success' | 'warning' | 'error'}
                className="flex items-center gap-1"
              >
                <systemStatus.icon className="h-3 w-3" />
                {systemStatus.status}
              </Badge>
            </div>

            {health && (
              <>
                <div className="flex items-center justify-between">
                  <span>API Version</span>
                  <span className="text-muted-foreground">{health.version}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Last Health Check</span>
                  <span className="text-muted-foreground">
                    {formatDate(health.timestamp)}
                  </span>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Services Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Services
            </CardTitle>
            <CardDescription>
              Individual service health monitoring
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {services.map((service) => (
              <div key={service.name} className="flex items-center justify-between">
                <div className="flex flex-col">
                  <span className="font-medium">{service.name}</span>
                  <span className="text-xs text-muted-foreground">{service.endpoint}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">{service.responseTime}</span>
                  <Badge
                    variant={
                      service.status === 'healthy' ? 'success' :
                      service.status === 'error' ? 'error' : 'warning'
                    }
                    className="text-xs"
                  >
                    {service.status}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common operator tasks and monitoring tools
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            <Link href="/runs">
              <Button variant="outline" className="w-full justify-start">
                <Activity className="mr-2 h-4 w-4" />
                View Runs
              </Button>
            </Link>
            <Link href="/knowledge">
              <Button variant="outline" className="w-full justify-start">
                <Database className="mr-2 h-4 w-4" />
                Search KB
              </Button>
            </Link>
            <Link href="/services">
              <Button variant="outline" className="w-full justify-start">
                <Server className="mr-2 h-4 w-4" />
                Service Health
              </Button>
            </Link>
            <Link href="/settings">
              <Button variant="outline" className="w-full justify-start">
                <Wifi className="mr-2 h-4 w-4" />
                Settings
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
