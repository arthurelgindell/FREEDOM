'use client'

import { useQuery } from '@tanstack/react-query'
import { healthCheck, getMetrics } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { formatDate } from '@/lib/utils'
import {
  Server,
  Activity,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock,
  Cpu,
  HardDrive,
  Network,
  Zap,
  BarChart3,
  Eye,
  Settings
} from 'lucide-react'

interface ServiceMetrics {
  name: string
  status: 'healthy' | 'degraded' | 'error' | 'unknown'
  endpoint: string
  responseTime?: number
  uptime?: number
  cpu?: number
  memory?: number
  connections?: number
  requests?: number
  errors?: number
  description: string
  version?: string
  lastCheck?: string
}

export default function ServicesPage() {
  const {
    data: health,
    isLoading,
    isError,
    refetch,
    dataUpdatedAt
  } = useQuery({
    queryKey: ['health'],
    queryFn: healthCheck,
    refetchInterval: 15000, // Refetch every 15 seconds
    retry: 2,
  })

  const { data: metricsData } = useQuery({
    queryKey: ['metrics'],
    queryFn: getMetrics,
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 1,
    enabled: false, // Disable by default
    meta: {
      errorMessage: 'Failed to fetch metrics'
    }
  })

  // Mock additional service data - in production this would come from service discovery
  const services: ServiceMetrics[] = [
    {
      name: 'API Gateway',
      status: health ? 'healthy' : (isError ? 'error' : 'unknown'),
      endpoint: 'http://localhost:8080',
      responseTime: health ? 25 : undefined,
      uptime: health?.uptime_seconds,
      cpu: 15,
      memory: 45,
      connections: 12,
      requests: 1547,
      errors: 3,
      description: 'Main API gateway handling all incoming requests',
      version: health?.version || 'Unknown',
      lastCheck: health?.timestamp
    },
    {
      name: 'Knowledge Base Service',
      status: (health?.kb_service_status as ServiceMetrics['status']) || 'unknown',
      endpoint: 'http://kb-service:8000',
      responseTime: health?.kb_service_response_time_ms,
      uptime: health ? health.uptime_seconds - 30 : undefined,
      cpu: 8,
      memory: 32,
      connections: 5,
      requests: 234,
      errors: 0,
      description: 'Vector database and knowledge processing service',
      version: '1.0.0',
      lastCheck: health?.timestamp
    },
    {
      name: 'PostgreSQL Database',
      status: health ? (health.kb_service_status === 'healthy' ? 'healthy' : 'degraded') : 'unknown',
      endpoint: 'postgres:5432',
      responseTime: 12,
      uptime: health ? health.uptime_seconds + 120 : undefined,
      cpu: 22,
      memory: 68,
      connections: 15,
      requests: 892,
      errors: 1,
      description: 'Primary database for knowledge storage and metadata',
      version: '15.0',
      lastCheck: health?.timestamp
    },
    {
      name: 'MLX Server',
      status: 'unknown',
      endpoint: 'http://localhost:8000',
      responseTime: undefined,
      cpu: 0,
      memory: 0,
      connections: 0,
      requests: 0,
      errors: 0,
      description: 'Local MLX inference server for AI processing',
      version: 'Unknown',
      lastCheck: undefined
    }
  ]

  const getStatusBadge = (status: ServiceMetrics['status']) => {
    switch (status) {
      case 'healthy':
        return (
          <Badge variant="success" className="flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            Healthy
          </Badge>
        )
      case 'degraded':
        return (
          <Badge variant="warning" className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Degraded
          </Badge>
        )
      case 'error':
        return (
          <Badge variant="error" className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Error
          </Badge>
        )
      default:
        return (
          <Badge variant="secondary" className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Unknown
          </Badge>
        )
    }
  }

  const getStatusColor = (status: ServiceMetrics['status']): string => {
    switch (status) {
      case 'healthy': return 'text-green-600'
      case 'degraded': return 'text-yellow-600'
      case 'error': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'Unknown'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  const healthyServices = services.filter(s => s.status === 'healthy').length
  const totalServices = services.length
  const avgResponseTime = services
    .filter(s => s.responseTime)
    .reduce((acc, s) => acc + (s.responseTime || 0), 0) / services.filter(s => s.responseTime).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Service Health</h1>
          <p className="text-muted-foreground">
            Monitor and manage all FREEDOM platform services
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

      {/* Overall System Status */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Services Online</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{healthyServices}/{totalServices}</div>
            <p className="text-xs text-muted-foreground">
              {((healthyServices / totalServices) * 100).toFixed(0)}% operational
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {avgResponseTime ? `${avgResponseTime.toFixed(0)}ms` : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              System response time
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {services.reduce((acc, s) => acc + (s.requests || 0), 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Since last restart
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Last Update</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dataUpdatedAt ? formatDate(new Date(dataUpdatedAt)).split(' ')[1] : 'Never'}
            </div>
            <p className="text-xs text-muted-foreground">
              Health check time
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Service Details */}
      <div className="grid gap-6 lg:grid-cols-2">
        {services.map((service) => (
          <Card key={service.name}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg bg-muted ${getStatusColor(service.status)}`}>
                    <Server className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{service.name}</CardTitle>
                    <CardDescription>{service.description}</CardDescription>
                  </div>
                </div>
                {getStatusBadge(service.status)}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Basic Info */}
              <div className="grid gap-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Endpoint:</span>
                  <span className="font-mono text-xs">{service.endpoint}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Version:</span>
                  <span>{service.version}</span>
                </div>
                {service.responseTime && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Response Time:</span>
                    <span>{service.responseTime}ms</span>
                  </div>
                )}
                {service.uptime && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Uptime:</span>
                    <span>{formatUptime(service.uptime)}</span>
                  </div>
                )}
                {service.lastCheck && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Check:</span>
                    <span>{formatDate(service.lastCheck)}</span>
                  </div>
                )}
              </div>

              {/* Resource Usage */}
              {(service.cpu !== undefined || service.memory !== undefined) && (
                <div className="space-y-2">
                  <h4 className="font-medium text-sm">Resource Usage</h4>
                  <div className="grid gap-2 text-sm">
                    {service.cpu !== undefined && (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Cpu className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">CPU:</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500 transition-all"
                              style={{ width: `${service.cpu}%` }}
                            />
                          </div>
                          <span>{service.cpu}%</span>
                        </div>
                      </div>
                    )}
                    {service.memory !== undefined && (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <HardDrive className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">Memory:</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500 transition-all"
                              style={{ width: `${service.memory}%` }}
                            />
                          </div>
                          <span>{service.memory}%</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Activity Stats */}
              {(service.connections !== undefined || service.requests !== undefined) && (
                <div className="space-y-2">
                  <h4 className="font-medium text-sm">Activity</h4>
                  <div className="grid gap-2 text-sm">
                    {service.connections !== undefined && (
                      <div className="flex justify-between">
                        <div className="flex items-center gap-2">
                          <Network className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">Connections:</span>
                        </div>
                        <span>{service.connections}</span>
                      </div>
                    )}
                    {service.requests !== undefined && (
                      <div className="flex justify-between">
                        <div className="flex items-center gap-2">
                          <Activity className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">Requests:</span>
                        </div>
                        <span>{service.requests.toLocaleString()}</span>
                      </div>
                    )}
                    {service.errors !== undefined && (
                      <div className="flex justify-between">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">Errors:</span>
                        </div>
                        <span className={service.errors > 0 ? 'text-red-600' : 'text-green-600'}>
                          {service.errors}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <Button variant="outline" size="sm" className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  View Logs
                </Button>
                <Button variant="outline" size="sm" className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Metrics
                </Button>
                <Button variant="outline" size="sm" className="flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  Config
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Metrics Raw Data */}
      {metricsData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Raw Metrics Data
            </CardTitle>
            <CardDescription>
              Prometheus metrics from the API Gateway
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-4 rounded overflow-x-auto max-h-96">
              {typeof metricsData === 'string' ? metricsData.slice(0, 2000) : JSON.stringify(metricsData, null, 2).slice(0, 2000)}
              {(typeof metricsData === 'string' ? metricsData.length : JSON.stringify(metricsData, null, 2).length) > 2000 && '\n... (truncated)'}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* System Alert */}
      {(isError || healthyServices < totalServices) && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <CardTitle className="text-yellow-800">Service Alert</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {isError ? (
              <p className="text-yellow-700">
                Unable to retrieve health information from the API Gateway.
                Check if the service is running and accessible.
              </p>
            ) : (
              <p className="text-yellow-700">
                {totalServices - healthyServices} service(s) are not in healthy state.
                Review individual service status and take corrective action if needed.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}