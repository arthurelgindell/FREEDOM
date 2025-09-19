#!/bin/bash
set -e

# FREEDOM Knowledge Base Service Runner
# Bulletproof startup with verification

echo "🚀 Starting FREEDOM Knowledge Base Service"
echo "=========================================="

# Check environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY environment variable is required"
    exit 1
fi

echo "✅ Environment check passed"

# Start services with Docker Compose
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to become healthy..."
timeout=60
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo "✅ Services are healthy"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo "   Waiting... (${elapsed}s/${timeout}s)"
done

if [ $elapsed -ge $timeout ]; then
    echo "❌ Services failed to become healthy within $timeout seconds"
    docker-compose logs
    exit 1
fi

# Run smoke tests
echo "🧪 Running smoke tests..."
python test_smoke.py

if [ $? -eq 0 ]; then
    echo "🎉 FREEDOM Knowledge Base Service is operational!"
    echo "📡 Service available at: http://localhost:8000"
    echo "📚 API docs at: http://localhost:8000/docs"
else
    echo "🔥 Smoke tests failed - service is not operational"
    docker-compose logs
    exit 1
fi