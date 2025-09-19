'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { queryKnowledgeBase, ingestSpecification, QueryRequest, IngestRequest } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { truncateText } from '@/lib/utils'
import {
  Search,
  Upload,
  Database,
  ExternalLink,
  Star,
  Clock,
  CheckCircle,
  AlertCircle,
  Download,
  Eye,
  Copy
} from 'lucide-react'

export default function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<'search' | 'ingest'>('search')

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchLimit, setSearchLimit] = useState(10)
  const [searchThreshold, setSearchThreshold] = useState(0.7)
  const [technologyFilter, setTechnologyFilter] = useState('')

  // Ingest state
  const [ingestData, setIngestData] = useState({
    technology_name: '',
    version: '',
    component_type: '',
    component_name: '',
    specification: '{}',
    source_url: '',
    confidence_score: 1.0
  })

  // Search mutation
  const searchMutation = useMutation({
    mutationFn: (request: QueryRequest) => queryKnowledgeBase(request),
  })

  // Ingest mutation
  const ingestMutation = useMutation({
    mutationFn: (request: IngestRequest) => ingestSpecification(request),
    onSuccess: () => {
      // Reset form on success
      setIngestData({
        technology_name: '',
        version: '',
        component_type: '',
        component_name: '',
        specification: '{}',
        source_url: '',
        confidence_score: 1.0
      })
    }
  })

  const handleSearch = () => {
    if (searchQuery.trim()) {
      const request: QueryRequest = {
        query: searchQuery.trim(),
        limit: searchLimit,
        similarity_threshold: searchThreshold,
        ...(technologyFilter && { technology_filter: technologyFilter })
      }
      searchMutation.mutate(request)
    }
  }

  const handleIngest = () => {
    try {
      const specification = JSON.parse(ingestData.specification)
      const request: IngestRequest = {
        ...ingestData,
        specification,
        confidence_score: ingestData.confidence_score
      }
      ingestMutation.mutate(request)
    } catch (error) {
      alert('Invalid JSON in specification field')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const exportResults = () => {
    if (searchMutation.data) {
      const dataStr = JSON.stringify(searchMutation.data, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `knowledge-search-${Date.now()}.json`
      link.click()
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
          <p className="text-muted-foreground">
            Search existing knowledge and ingest new specifications
          </p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 bg-muted p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('search')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'search'
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Search className="inline-block mr-2 h-4 w-4" />
          Search
        </button>
        <button
          onClick={() => setActiveTab('ingest')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'ingest'
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Upload className="inline-block mr-2 h-4 w-4" />
          Ingest
        </button>
      </div>

      {/* Search Tab */}
      {activeTab === 'search' && (
        <div className="space-y-6">
          {/* Search Form */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                Knowledge Search
              </CardTitle>
              <CardDescription>
                Query the knowledge base for components, specifications, and documentation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="md:col-span-2">
                  <label className="text-sm font-medium">Search Query</label>
                  <Textarea
                    placeholder="Enter your search query... (e.g., 'React components for data visualization')"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    rows={3}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Technology Filter</label>
                  <Input
                    placeholder="e.g., React, Python, JavaScript"
                    value={technologyFilter}
                    onChange={(e) => setTechnologyFilter(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Result Limit</label>
                  <Input
                    type="number"
                    min="1"
                    max="50"
                    value={searchLimit}
                    onChange={(e) => setSearchLimit(parseInt(e.target.value) || 10)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Similarity Threshold</label>
                  <Input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={searchThreshold}
                    onChange={(e) => setSearchThreshold(parseFloat(e.target.value) || 0.7)}
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={handleSearch}
                  disabled={!searchQuery.trim() || searchMutation.isPending}
                  className="flex items-center gap-2"
                >
                  {searchMutation.isPending ? (
                    <Clock className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                  {searchMutation.isPending ? 'Searching...' : 'Search'}
                </Button>
                {searchMutation.data && (
                  <Button
                    variant="outline"
                    onClick={exportResults}
                    className="flex items-center gap-2"
                  >
                    <Download className="h-4 w-4" />
                    Export Results
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Search Results */}
          {searchMutation.data && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    Search Results
                  </CardTitle>
                  <Badge variant="outline">
                    {searchMutation.data.total_results} results in {searchMutation.data.total_time_ms}ms
                  </Badge>
                </div>
                <CardDescription>
                  Found {searchMutation.data.total_results} matching components and specifications
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {searchMutation.data.results.map((result, index) => (
                    <div key={index} className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg">{result.component_name}</h3>
                          <p className="text-muted-foreground">{result.technology_name} v{result.version}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{result.component_type}</Badge>
                          <div className="flex items-center gap-1">
                            <Star className="h-4 w-4 text-yellow-500" />
                            <span className="text-sm">{(result.similarity_score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      </div>

                      {/* Specification Preview */}
                      <div className="bg-muted p-3 rounded">
                        <h4 className="font-medium mb-2">Specification</h4>
                        <pre className="text-xs text-muted-foreground overflow-x-auto">
                          {JSON.stringify(result.specification, null, 2).slice(0, 200)}
                          {JSON.stringify(result.specification, null, 2).length > 200 && '...'}
                        </pre>
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>Confidence: {(result.confidence_score * 100).toFixed(0)}%</span>
                          <span>Source: {truncateText(result.source_url, 40)}</span>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => copyToClipboard(JSON.stringify(result.specification, null, 2))}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(result.source_url, '_blank')}
                          >
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Search Error */}
          {searchMutation.isError && (
            <Card className="border-red-200 bg-red-50">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-red-600" />
                  <CardTitle className="text-red-800">Search Failed</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-red-700">
                  {searchMutation.error?.message || 'An error occurred while searching the knowledge base'}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Ingest Tab */}
      {activeTab === 'ingest' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Ingest Specification
              </CardTitle>
              <CardDescription>
                Add new component specifications to the knowledge base
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium">Technology Name</label>
                  <Input
                    placeholder="e.g., React, Python, PostgreSQL"
                    value={ingestData.technology_name}
                    onChange={(e) => setIngestData(prev => ({ ...prev, technology_name: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Version</label>
                  <Input
                    placeholder="e.g., 18.2.0, 3.11, 15.0"
                    value={ingestData.version}
                    onChange={(e) => setIngestData(prev => ({ ...prev, version: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Component Type</label>
                  <Input
                    placeholder="e.g., component, library, framework"
                    value={ingestData.component_type}
                    onChange={(e) => setIngestData(prev => ({ ...prev, component_type: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Component Name</label>
                  <Input
                    placeholder="e.g., Button, Chart, DataTable"
                    value={ingestData.component_name}
                    onChange={(e) => setIngestData(prev => ({ ...prev, component_name: e.target.value }))}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-sm font-medium">Source URL</label>
                  <Input
                    placeholder="https://..."
                    value={ingestData.source_url}
                    onChange={(e) => setIngestData(prev => ({ ...prev, source_url: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Confidence Score</label>
                  <Input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={ingestData.confidence_score}
                    onChange={(e) => setIngestData(prev => ({ ...prev, confidence_score: parseFloat(e.target.value) || 1.0 }))}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-sm font-medium">Specification (JSON)</label>
                  <Textarea
                    placeholder='{"props": {"title": "string", "onClick": "function"}, "description": "..."}'
                    value={ingestData.specification}
                    onChange={(e) => setIngestData(prev => ({ ...prev, specification: e.target.value }))}
                    rows={8}
                    className="font-mono text-sm"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={handleIngest}
                  disabled={ingestMutation.isPending || !ingestData.technology_name || !ingestData.component_name}
                  className="flex items-center gap-2"
                >
                  {ingestMutation.isPending ? (
                    <Clock className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  {ingestMutation.isPending ? 'Ingesting...' : 'Ingest Specification'}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Ingest Success */}
          {ingestMutation.isSuccess && (
            <Card className="border-green-200 bg-green-50">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  <CardTitle className="text-green-800">Specification Ingested Successfully</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-green-700">
                  Specification ID: {ingestMutation.data?.specification_id}
                </p>
                <p className="text-green-700">
                  Processing time: {ingestMutation.data?.processing_time_ms}ms
                </p>
              </CardContent>
            </Card>
          )}

          {/* Ingest Error */}
          {ingestMutation.isError && (
            <Card className="border-red-200 bg-red-50">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-red-600" />
                  <CardTitle className="text-red-800">Ingest Failed</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-red-700">
                  {ingestMutation.error?.message || 'An error occurred while ingesting the specification'}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}