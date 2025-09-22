'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Settings,
  Key,
  Wifi,
  Database,
  Save,
  RefreshCw,
  Eye,
  EyeOff,
  CheckCircle,
  AlertTriangle,
  Copy,
  Download,
  Upload
} from 'lucide-react'

interface SettingsConfig {
  apiUrl: string
  apiKey: string
  wsUrl: string
  queryDefaults: {
    limit: number
    similarityThreshold: number
  }
  notifications: {
    realTime: boolean
    healthAlerts: boolean
    taskCompletions: boolean
  }
}

export default function SettingsPage() {
  const [config, setConfig] = useState<SettingsConfig>({
    apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080',
    apiKey: process.env.NEXT_PUBLIC_API_KEY || 'dev-key-change-in-production',
    wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080',
    queryDefaults: {
      limit: 10,
      similarityThreshold: 0.7
    },
    notifications: {
      realTime: true,
      healthAlerts: true,
      taskCompletions: true
    }
  })

  const [showApiKey, setShowApiKey] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [testConnection, setTestConnection] = useState<{
    status: 'idle' | 'testing' | 'success' | 'error'
    message?: string
  }>({ status: 'idle' })

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedConfig = localStorage.getItem('castle-settings')
    if (savedConfig) {
      try {
        const parsed = JSON.parse(savedConfig)
        setConfig(prev => ({ ...prev, ...parsed }))
      } catch (error) {
        console.error('Failed to parse saved settings:', error)
      }
    }
  }, [])

  // Track changes
  useEffect(() => {
    const savedConfig = localStorage.getItem('castle-settings')
    const currentConfigStr = JSON.stringify(config)
    const savedConfigStr = savedConfig || JSON.stringify({})
    setHasChanges(currentConfigStr !== savedConfigStr)
  }, [config])

  const handleSaveSettings = () => {
    try {
      localStorage.setItem('castle-settings', JSON.stringify(config))
      setHasChanges(false)
      // Trigger a page reload to apply new settings
      window.location.reload()
    } catch {
      alert('Failed to save settings')
    }
  }

  const handleTestConnection = async () => {
    setTestConnection({ status: 'testing' })

    try {
      const response = await fetch(`${config.apiUrl}/health`, {
        headers: {
          'X-API-Key': config.apiKey
        }
      })

      if (response.ok) {
        setTestConnection({
          status: 'success',
          message: 'Connection successful'
        })
      } else {
        setTestConnection({
          status: 'error',
          message: `HTTP ${response.status}: ${response.statusText}`
        })
      }
    } catch (error) {
      setTestConnection({
        status: 'error',
        message: error instanceof Error ? error.message : 'Connection failed'
      })
    }

    // Clear status after 5 seconds
    setTimeout(() => {
      setTestConnection({ status: 'idle' })
    }, 5000)
  }

  const handleExportSettings = () => {
    const dataStr = JSON.stringify(config, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `castle-settings-${Date.now()}.json`
    link.click()
  }

  const handleImportSettings = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const importedConfig = JSON.parse(e.target?.result as string)
        setConfig(prev => ({ ...prev, ...importedConfig }))
      } catch (error) {
        alert('Invalid settings file')
      }
    }
    reader.readAsText(file)
  }

  const copyApiKey = () => {
    if (typeof window !== 'undefined') {
      navigator.clipboard.writeText(config.apiKey)
    }
  }

  const getConnectionBadge = () => {
    switch (testConnection.status) {
      case 'testing':
        return (
          <Badge variant="warning" className="flex items-center gap-1">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Testing...
          </Badge>
        )
      case 'success':
        return (
          <Badge variant="success" className="flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            Connected
          </Badge>
        )
      case 'error':
        return (
          <Badge variant="error" className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Failed
          </Badge>
        )
      default:
        return null
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">
            Configure Castle GUI and API connections
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleExportSettings}
            className="flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export
          </Button>
          <label className="cursor-pointer">
            <input
              type="file"
              accept=".json"
              onChange={handleImportSettings}
              className="hidden"
            />
            <Button variant="outline" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              Import
            </Button>
          </label>
          {hasChanges && (
            <Button onClick={handleSaveSettings} className="flex items-center gap-2">
              <Save className="h-4 w-4" />
              Save Changes
            </Button>
          )}
        </div>
      </div>

      {/* Connection Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wifi className="h-5 w-5" />
            Connection Settings
          </CardTitle>
          <CardDescription>
            Configure API endpoints and authentication
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium">API Base URL</label>
              <Input
                placeholder="http://localhost:8080"
                value={config.apiUrl}
                onChange={(e) => setConfig(prev => ({ ...prev, apiUrl: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground mt-1">
                The base URL for the FREEDOM API Gateway
              </p>
            </div>
            <div>
              <label className="text-sm font-medium">WebSocket URL</label>
              <Input
                placeholder="ws://localhost:8080"
                value={config.wsUrl}
                onChange={(e) => setConfig(prev => ({ ...prev, wsUrl: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground mt-1">
                WebSocket endpoint for real-time updates
              </p>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">API Key</label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  type={showApiKey ? 'text' : 'password'}
                  placeholder="Enter API key"
                  value={config.apiKey}
                  onChange={(e) => setConfig(prev => ({ ...prev, apiKey: e.target.value }))}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                </Button>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={copyApiKey}
                className="flex items-center gap-1"
              >
                <Copy className="h-3 w-3" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Authentication key for API access
            </p>
          </div>

          <div className="flex items-center gap-4 pt-2">
            <Button
              variant="outline"
              onClick={handleTestConnection}
              disabled={testConnection.status === 'testing'}
              className="flex items-center gap-2"
            >
              {testConnection.status === 'testing' ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Wifi className="h-4 w-4" />
              )}
              Test Connection
            </Button>
            {getConnectionBadge()}
            {testConnection.message && (
              <span className="text-sm text-muted-foreground">
                {testConnection.message}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Query Defaults */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Query Defaults
          </CardTitle>
          <CardDescription>
            Default parameters for knowledge base queries
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium">Default Result Limit</label>
              <Input
                type="number"
                min="1"
                max="50"
                value={config.queryDefaults.limit}
                onChange={(e) => setConfig(prev => ({
                  ...prev,
                  queryDefaults: {
                    ...prev.queryDefaults,
                    limit: parseInt(e.target.value) || 10
                  }
                }))}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Maximum number of results to return (1-50)
              </p>
            </div>
            <div>
              <label className="text-sm font-medium">Similarity Threshold</label>
              <Input
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={config.queryDefaults.similarityThreshold}
                onChange={(e) => setConfig(prev => ({
                  ...prev,
                  queryDefaults: {
                    ...prev.queryDefaults,
                    similarityThreshold: parseFloat(e.target.value) || 0.7
                  }
                }))}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Minimum similarity score for results (0.0-1.0)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Notifications
          </CardTitle>
          <CardDescription>
            Configure real-time notifications and alerts
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium">Real-time Updates</label>
                <p className="text-xs text-muted-foreground">
                  Enable WebSocket connections for live updates
                </p>
              </div>
              <input
                type="checkbox"
                checked={config.notifications.realTime}
                onChange={(e) => setConfig(prev => ({
                  ...prev,
                  notifications: {
                    ...prev.notifications,
                    realTime: e.target.checked
                  }
                }))}
                className="w-4 h-4"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium">Health Alerts</label>
                <p className="text-xs text-muted-foreground">
                  Show notifications when services go down
                </p>
              </div>
              <input
                type="checkbox"
                checked={config.notifications.healthAlerts}
                onChange={(e) => setConfig(prev => ({
                  ...prev,
                  notifications: {
                    ...prev.notifications,
                    healthAlerts: e.target.checked
                  }
                }))}
                className="w-4 h-4"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium">Task Completions</label>
                <p className="text-xs text-muted-foreground">
                  Notify when knowledge base queries finish
                </p>
              </div>
              <input
                type="checkbox"
                checked={config.notifications.taskCompletions}
                onChange={(e) => setConfig(prev => ({
                  ...prev,
                  notifications: {
                    ...prev.notifications,
                    taskCompletions: e.target.checked
                  }
                }))}
                className="w-4 h-4"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Environment Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Environment Information
          </CardTitle>
          <CardDescription>
            Current environment configuration and build info
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Application:</span>
              <span>FREEDOM Castle GUI</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Version:</span>
              <span>1.0.0</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Node Environment:</span>
              <span>{process.env.NODE_ENV || 'development'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Build Time:</span>
              <span>{new Date().toISOString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">User Agent:</span>
              <span className="truncate max-w-64" title={typeof window !== 'undefined' ? navigator.userAgent : 'SSR'}>
                {typeof window !== 'undefined' ? navigator.userAgent.split(' ')[0] + '...' : 'SSR'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Changes Banner */}
      {hasChanges && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-blue-600" />
                <span className="text-blue-800 font-medium">
                  You have unsaved changes
                </span>
              </div>
              <Button onClick={handleSaveSettings} className="flex items-center gap-2">
                <Save className="h-4 w-4" />
                Save Changes
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}