# FREEDOM API Gateway

Production-ready FastAPI gateway service that provides secure, monitored access to the FREEDOM Platform knowledge base.

## Features

### Core Functionality
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **Knowledge Base Integration**: Routes requests to KB service with service discovery
- **Health Monitoring**: Comprehensive health checks for gateway and downstream services

### Security
- **API Key Authentication**: Required for all protected endpoints via `X-API-Key` header
- **CORS Protection**: Configurable origins for Castle GUI integration
- **Rate Limiting**: Configurable request rate limits to prevent abuse
- **Trusted Host Middleware**: Protection against host header attacks

### Monitoring & Observability
- **Structured Logging**: JSON logs with correlation IDs for request tracing
- **Prometheus Metrics**: Request duration, KB hits/misses, error rates
- **Performance Tracking**: Request timing and throughput monitoring
- **Health Checks**: Deep health validation of entire service stack

### Reliability
- **Graceful Shutdown**: Proper cleanup of connections and resources
- **Error Handling**: Consistent error responses with correlation tracking
- **Circuit Breaking**: Timeout handling for downstream services
- **Multi-worker**: Production deployment with multiple Uvicorn workers

## API Endpoints

### Health & Monitoring

#### `GET /health`
Comprehensive health check that validates:
- API Gateway status
- Knowledge Base service connectivity
- Database connection (via KB service)
- Service uptime and performance

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 3600.5,
  "version": "1.0.0",
  "kb_service_status": "healthy",
  "kb_service_response_time_ms": 45.2
}
```

#### `GET /metrics`
Prometheus-compatible metrics endpoint for monitoring:
- `gateway_requests_total`: Total requests by method/endpoint/status
- `gateway_request_duration_seconds`: Request duration histograms
- `gateway_kb_requests_total`: KB service requests by operation/status
- `gateway_kb_cache_hits_total`: Cache hit/miss ratios
- `gateway_active_connections`: Current active connections

### Knowledge Base Operations

#### `POST /kb/query`
Query the knowledge base with natural language.

**Authentication:** Required (`X-API-Key` header)
**Rate Limit:** 100 requests/minute

**Request:**
```json
{
  "query": "How to configure Kubernetes ingress with TLS?",
  "limit": 10,
  "similarity_threshold": 0.7,
  "technology_filter": "kubernetes"
}
```

**Response:**
```json
{
  "query": "How to configure Kubernetes ingress with TLS?",
  "results": [
    {
      "id": "spec-123",
      "technology_name": "kubernetes",
      "version": "1.28",
      "component_type": "ingress",
      "component_name": "nginx-ingress",
      "specification": {...},
      "source_url": "https://kubernetes.io/docs/...",
      "confidence_score": 0.95,
      "similarity_score": 0.87,
      "extracted_at": "2024-01-15T09:00:00Z"
    }
  ],
  "total_results": 5,
  "processing_time_ms": 234.5,
  "similarity_threshold_used": 0.7
}
```

#### `POST /kb/ingest`
Ingest new technical specifications into the knowledge base.

**Authentication:** Required (`X-API-Key` header)
**Rate Limit:** 10 requests/minute

**Request:**
```json
{
  "technology_name": "kubernetes",
  "version": "1.28",
  "component_type": "ingress",
  "component_name": "nginx-ingress",
  "specification": {
    "apiVersion": "networking.k8s.io/v1",
    "kind": "Ingress",
    "spec": {...}
  },
  "source_url": "https://kubernetes.io/docs/concepts/services-networking/ingress/",
  "confidence_score": 0.95
}
```

**Response:**
```json
{
  "success": true,
  "specification_id": "spec-456",
  "message": "Specification ingested successfully",
  "processing_time_ms": 1250.3
}
```

### Documentation
- **Interactive API Docs**: `/docs` (Swagger UI)
- **ReDoc Documentation**: `/redoc` (Alternative documentation)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FREEDOM_API_KEY` | `dev-key-change-in-production` | API key for authentication |
| `KB_SERVICE_URL` | `http://kb-service:8000` | Knowledge base service URL |
| `CORS_ORIGINS` | `http://localhost:3000,http://castle-gui:3000` | Allowed CORS origins |
| `RATE_LIMIT` | `100/minute` | Rate limit for most endpoints |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Security Configuration

1. **Generate a secure API key:**
   ```bash
   export FREEDOM_API_KEY=$(openssl rand -hex 32)
   ```

2. **Configure CORS origins** for your Castle GUI:
   ```bash
   export CORS_ORIGINS="https://castle.yourdomain.com,http://localhost:3000"
   ```

3. **Set appropriate rate limits** based on your usage:
   ```bash
   export RATE_LIMIT="200/minute"  # For high-traffic deployments
   ```

## Deployment

### Docker Compose (Recommended)

The API Gateway is included in the main FREEDOM Platform docker-compose.yml:

```bash
# Start the entire platform
docker-compose up -d

# Check API Gateway health
curl http://localhost:8080/health

# View logs
docker-compose logs -f api
```

### Standalone Docker

```bash
# Build the image
docker build -t freedom-api-gateway ./services/api

# Run with environment variables
docker run -d \
  --name freedom-api \
  -p 8080:8080 \
  -e FREEDOM_API_KEY=your-secure-key \
  -e KB_SERVICE_URL=http://your-kb-service:8000 \
  freedom-api-gateway
```

### Local Development

```bash
cd services/api

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FREEDOM_API_KEY=dev-key
export KB_SERVICE_URL=http://localhost:8000

# Run the application
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## Testing

### Smoke Tests

Run comprehensive smoke tests to verify all functionality:

```bash
cd services/api

# Test against local instance
python test_smoke.py

# Test against specific endpoint
API_BASE_URL=http://your-gateway:8080 python test_smoke.py
```

The smoke tests verify:
- ✅ Health endpoint functionality and performance
- ✅ Prometheus metrics endpoint
- ✅ Authentication requirements
- ✅ KB query and ingest endpoints
- ✅ Rate limiting behavior
- ✅ CORS configuration
- ✅ Error handling
- ✅ OpenAPI documentation

### Manual Testing

#### Health Check
```bash
curl http://localhost:8080/health
```

#### Query with Authentication
```bash
curl -X POST http://localhost:8080/kb/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "kubernetes deployment configuration",
    "limit": 5
  }'
```

#### Metrics
```bash
curl http://localhost:8080/metrics
```

## Monitoring

### Prometheus Integration

Add this configuration to your Prometheus `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'freedom-api-gateway'
    static_configs:
      - targets: ['api:8080']
    metrics_path: /metrics
    scrape_interval: 15s
```

### Key Metrics to Monitor

- **Request Rate**: `rate(gateway_requests_total[5m])`
- **Error Rate**: `rate(gateway_requests_total{status=~"5.."}[5m])`
- **Response Time**: `histogram_quantile(0.95, rate(gateway_request_duration_seconds_bucket[5m]))`
- **KB Service Health**: `gateway_kb_requests_total{status="success"}`

### Log Analysis

Logs are structured JSON for easy parsing:

```bash
# Filter by correlation ID
docker logs freedom-api | jq 'select(.correlation_id == "uuid-here")'

# Monitor error rates
docker logs freedom-api | jq 'select(.level == "error")'

# Track performance
docker logs freedom-api | jq 'select(.processing_time_ms > 1000)'
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Castle GUI    │────│  API Gateway     │────│  KB Service     │
│   (Frontend)    │    │  (Port 8080)     │    │  (Port 8000)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Prometheus     │
                       │   (Metrics)      │
                       └──────────────────┘
```

### Request Flow

1. **Client Request** → API Gateway (with X-API-Key)
2. **Authentication** → Verify API key
3. **Rate Limiting** → Check request limits
4. **Correlation ID** → Generate tracking ID
5. **Logging** → Log request with correlation ID
6. **KB Service** → Forward to knowledge base
7. **Response** → Return with metrics and logging

### Security Layers

1. **API Key Authentication**: All protected endpoints require valid key
2. **CORS Protection**: Restrict origins to authorized domains
3. **Rate Limiting**: Prevent abuse with configurable limits
4. **Input Validation**: Pydantic models validate all input
5. **Error Handling**: No sensitive information in error responses

## Troubleshooting

### Common Issues

#### API Gateway won't start
```bash
# Check logs
docker-compose logs api

# Verify dependencies
docker-compose ps
```

#### KB Service connection failed
```bash
# Test KB service directly
curl http://localhost:8000/health

# Check network connectivity
docker-compose exec api ping kb-service
```

#### Authentication errors
```bash
# Verify API key
echo $FREEDOM_API_KEY

# Test with correct key
curl -H "X-API-Key: $FREEDOM_API_KEY" http://localhost:8080/health
```

#### Rate limiting issues
```bash
# Check current rate limit
docker-compose exec api env | grep RATE_LIMIT

# Adjust in docker-compose.yml or environment
```

### Performance Tuning

#### High Traffic Deployments
- Increase worker count in `run.sh`
- Adjust rate limits for your use case
- Monitor memory usage and CPU
- Consider Redis for distributed rate limiting

#### Memory Optimization
```dockerfile
# Add to Dockerfile for production
ENV UVICORN_WORKERS=2
ENV UVICORN_MAX_REQUESTS=1000
ENV UVICORN_MAX_REQUESTS_JITTER=50
```

## Development

### Adding New Endpoints

1. **Define Pydantic models** for request/response
2. **Add route function** with proper authentication
3. **Add metrics tracking** for the new endpoint
4. **Update smoke tests** to verify functionality
5. **Document in README** and OpenAPI

### Extending Middleware

1. **Create middleware class** following existing patterns
2. **Add to middleware stack** in correct order
3. **Test impact on performance**
4. **Add monitoring if needed**

### Contributing

1. Follow existing code patterns
2. Add comprehensive tests
3. Update documentation
4. Verify all smoke tests pass
5. Monitor performance impact

## Security Considerations

- **Never log API keys** - only log truncated versions
- **Use strong API keys** - minimum 32 characters, cryptographically random
- **Rotate API keys regularly** - implement key rotation schedule
- **Monitor for abuse** - track failed authentication attempts
- **Limit CORS origins** - only allow necessary domains
- **Use HTTPS in production** - terminate TLS at load balancer or reverse proxy

## License

Part of the FREEDOM Platform - see main project license.