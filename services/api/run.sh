#!/bin/bash
set -e

# FREEDOM API Gateway Startup Script
# Handles graceful startup and health verification

echo "🚀 Starting FREEDOM API Gateway..."

# Check if required environment variables are set
if [ -z "$FREEDOM_API_KEY" ]; then
    echo "⚠️  WARNING: FREEDOM_API_KEY not set, using default development key"
    export FREEDOM_API_KEY="dev-key-change-in-production"
fi

if [ -z "$KB_SERVICE_URL" ]; then
    echo "ℹ️  KB_SERVICE_URL not set, using default"
    export KB_SERVICE_URL="http://kb-service:8000"
fi

# Set defaults for other variables
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000,http://castle-gui:3000}"
export RATE_LIMIT="${RATE_LIMIT:-100/minute}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo "Configuration:"
echo "  - API Key: ${FREEDOM_API_KEY:0:8}..."
echo "  - KB Service: $KB_SERVICE_URL"
echo "  - CORS Origins: $CORS_ORIGINS"
echo "  - Rate Limit: $RATE_LIMIT"
echo "  - Log Level: $LOG_LEVEL"

# Start the application
echo "📡 Starting API Gateway on port 8080..."

# Use exec to replace the shell process and handle signals properly
exec python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 4 \
    --access-log \
    --log-level "${LOG_LEVEL,,}"