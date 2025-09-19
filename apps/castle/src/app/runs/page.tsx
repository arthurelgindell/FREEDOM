'use client'

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { formatDate, truncateText } from '@/lib/utils'
import {
  PlayCircle,
  Clock,
  CheckCircle,
  XCircle,
  Plus,
  Search,
  Filter,
  Download,
  Eye,
  Trash2,
  RefreshCw
} from 'lucide-react'

// Mock data for runs - in production this would come from the API
interface TaskRun {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  query: string
  results?: Array<{ component: string; technology: string; confidence: number }>
  createdAt: string
  completedAt?: string
  duration?: number
  resultCount?: number
  error?: string
}

const mockRuns: TaskRun[] = [
  {
    id: '1',
    name: 'React Component Search',
    status: 'completed',
    query: 'Find React components for data visualization',
    results: [
      { component: 'Chart.js', technology: 'React', confidence: 0.95 },
      { component: 'D3.js', technology: 'JavaScript', confidence: 0.88 }
    ],
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    completedAt: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    duration: 5000,
    resultCount: 2
  },
  {
    id: '2',
    name: 'API Integration Query',
    status: 'running',
    query: 'Find REST API integration patterns for microservices',
    createdAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
  },
  {
    id: '3',
    name: 'Database Schema Search',
    status: 'failed',
    query: 'PostgreSQL schema for user management',
    createdAt: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    completedAt: new Date(Date.now() - 1000 * 60 * 58).toISOString(),
    error: 'Connection timeout to knowledge base service'
  }
]

export default function RunsPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [showNewRun, setShowNewRun] = useState(false)
  const [newRunQuery, setNewRunQuery] = useState('')
  const [newRunName, setNewRunName] = useState('')

  // Mock query - in production this would fetch from API
  const { data: runs = mockRuns, isLoading, refetch } = useQuery({
    queryKey: ['runs'],
    queryFn: async () => {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500))
      return mockRuns
    },
    refetchInterval: 5000, // Refetch every 5 seconds to update running tasks
  })

  // Mock mutation for creating new runs
  const createRunMutation = useMutation({
    mutationFn: async (data: { name: string; query: string }) => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      return {
        id: Math.random().toString(36).substr(2, 9),
        ...data,
        status: 'pending' as const,
        createdAt: new Date().toISOString()
      }
    },
    onSuccess: () => {
      setShowNewRun(false)
      setNewRunQuery('')
      setNewRunName('')
      refetch()
    }
  })

  const filteredRuns = runs.filter(run => {
    const matchesSearch = run.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         run.query.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterStatus === 'all' || run.status === filterStatus
    return matchesSearch && matchesFilter
  })

  const getStatusBadge = (status: TaskRun['status']) => {
    switch (status) {
      case 'completed':
        return (
          <Badge variant="success" className="flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            Completed
          </Badge>
        )
      case 'running':
        return (
          <Badge variant="warning" className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Running
          </Badge>
        )
      case 'failed':
        return (
          <Badge variant="error" className="flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        )
      default:
        return (
          <Badge variant="secondary" className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Pending
          </Badge>
        )
    }
  }

  const handleCreateRun = () => {
    if (newRunName.trim() && newRunQuery.trim()) {
      createRunMutation.mutate({
        name: newRunName.trim(),
        query: newRunQuery.trim()
      })
    }
  }

  const runningRuns = runs.filter(run => run.status === 'running').length
  const completedRuns = runs.filter(run => run.status === 'completed').length
  const failedRuns = runs.filter(run => run.status === 'failed').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Task Runs</h1>
          <p className="text-muted-foreground">
            Execute knowledge base queries and view results
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => refetch()}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={() => setShowNewRun(true)}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            New Run
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
            <PlayCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runs.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <Clock className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runningRuns}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{completedRuns}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{failedRuns}</div>
          </CardContent>
        </Card>
      </div>

      {/* New Run Form */}
      {showNewRun && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Run</CardTitle>
            <CardDescription>
              Submit a new knowledge base query task
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Run Name</label>
              <Input
                placeholder="e.g., React Component Search"
                value={newRunName}
                onChange={(e) => setNewRunName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Query</label>
              <Textarea
                placeholder="Enter your knowledge base query..."
                value={newRunQuery}
                onChange={(e) => setNewRunQuery(e.target.value)}
                rows={3}
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleCreateRun}
                disabled={!newRunName.trim() || !newRunQuery.trim() || createRunMutation.isPending}
                className="flex items-center gap-2"
              >
                {createRunMutation.isPending ? (
                  <Clock className="h-4 w-4 animate-spin" />
                ) : (
                  <PlayCircle className="h-4 w-4" />
                )}
                {createRunMutation.isPending ? 'Creating...' : 'Create Run'}
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowNewRun(false)}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search runs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="border border-input rounded-md px-3 py-1 text-sm"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Runs List */}
      <div className="space-y-4">
        {filteredRuns.map((run) => (
          <Card key={run.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-lg">{run.name}</CardTitle>
                  {getStatusBadge(run.status)}
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm">
                    <Eye className="h-4 w-4" />
                  </Button>
                  {run.results && (
                    <Button variant="ghost" size="sm">
                      <Download className="h-4 w-4" />
                    </Button>
                  )}
                  <Button variant="ghost" size="sm">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <CardDescription>
                {truncateText(run.query, 120)}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Created:</span>
                    <span>{formatDate(run.createdAt)}</span>
                  </div>
                  {run.completedAt && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Completed:</span>
                      <span>{formatDate(run.completedAt)}</span>
                    </div>
                  )}
                  {run.duration && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Duration:</span>
                      <span>{(run.duration / 1000).toFixed(2)}s</span>
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  {run.resultCount !== undefined && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Results:</span>
                      <span>{run.resultCount} items</span>
                    </div>
                  )}
                  {run.error && (
                    <div className="text-sm text-red-600">
                      <span className="font-medium">Error:</span> {run.error}
                    </div>
                  )}
                </div>
              </div>

              {/* Results Preview */}
              {run.results && run.results.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-medium mb-2">Results Preview</h4>
                  <div className="space-y-2">
                    {run.results.slice(0, 2).map((result, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-muted rounded">
                        <span className="font-medium">{result.component}</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{result.technology}</Badge>
                          <span className="text-sm text-muted-foreground">
                            {(result.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ))}
                    {run.results.length > 2 && (
                      <div className="text-sm text-muted-foreground text-center py-2">
                        + {run.results.length - 2} more results
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}

        {filteredRuns.length === 0 && (
          <Card>
            <CardContent className="text-center py-8">
              <PlayCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No runs found</h3>
              <p className="text-muted-foreground mb-4">
                {searchTerm || filterStatus !== 'all'
                  ? 'Try adjusting your search or filter criteria'
                  : 'Create your first knowledge base query run to get started'
                }
              </p>
              {!searchTerm && filterStatus === 'all' && (
                <Button onClick={() => setShowNewRun(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create First Run
                </Button>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}