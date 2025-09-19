import axios, { AxiosInstance, AxiosResponse } from 'axios'

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev-key-change-in-production'

// Create axios instance
export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
})

// Request interceptor for correlation IDs
api.interceptors.request.use(
  (config) => {
    const correlationId = crypto.randomUUID()
    config.headers['x-correlation-id'] = correlationId
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      console.error('Authentication failed - check API key')
    } else if (error.response?.status === 503) {
      console.error('Service unavailable - backend may be down')
    }
    return Promise.reject(error)
  }
)

// API types
export interface HealthResponse {
  status: string
  timestamp: string
  uptime_seconds: number
  version: string
  kb_service_status: string
  kb_service_response_time_ms?: number
}

export interface QueryRequest {
  query: string
  limit?: number
  similarity_threshold?: number
  technology_filter?: string
}

export interface QueryResult {
  component_name: string
  technology_name: string
  version: string
  component_type: string
  specification: Record<string, unknown>
  source_url: string
  confidence_score: number
  similarity_score: number
}

export interface QueryResponse {
  results: QueryResult[]
  total_results: number
  query_embedding_time_ms: number
  search_time_ms: number
  total_time_ms: number
}

export interface IngestRequest {
  technology_name: string
  version: string
  component_type: string
  component_name: string
  specification: Record<string, unknown>
  source_url: string
  confidence_score?: number
}

export interface IngestResponse {
  specification_id: string
  message: string
  processing_time_ms: number
}

// API functions
export const healthCheck = async (): Promise<HealthResponse> => {
  const response = await api.get('/health')
  return response.data
}

export const queryKnowledgeBase = async (request: QueryRequest): Promise<QueryResponse> => {
  const response = await api.post('/kb/query', request)
  return response.data
}

export const ingestSpecification = async (request: IngestRequest): Promise<IngestResponse> => {
  const response = await api.post('/kb/ingest', request)
  return response.data
}

export const getMetrics = async (): Promise<string> => {
  const response = await api.get('/metrics')
  return response.data
}