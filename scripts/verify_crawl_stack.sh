#!/bin/bash
set -e

echo "🔍 Verifying Crawl Stack..."
echo "=========================="

# Check Redis
echo -n "Redis: "
redis-cli ping > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ FAILED"

# Check Router
echo -n "Router: "
curl -s http://localhost:8003/health > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ FAILED"

# Check queue stats
echo -e "\n📊 Queue Statistics:"
curl -s http://localhost:8003/stats | python3 -m json.tool

# Test router with simple scrape
echo -e "\n🧪 Testing Router (simple scrape)..."
curl -s -X POST http://localhost:8003/crawl \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","intent":"scrape"}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"✅ Routed to: {d.get('routed_to')}\")" \
  || echo "❌ Router failed"

# Test router with auth task
echo -e "\n🧪 Testing Router (auth task)..."
curl -s -X POST http://localhost:8003/crawl \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://app.example.com/login","intent":"login and scrape"}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"✅ Routed to: {d.get('routed_to')} (queued: {d.get('queued')})\")" \
  || echo "❌ Router failed"

# Check all containers
echo -e "\n📦 Docker Containers Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "freedom|NAMES"

echo -e "\n✅ Verification complete!"