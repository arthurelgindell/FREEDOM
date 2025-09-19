#!/bin/bash
# Daily morning health check script
cd /Volumes/DATA/FREEDOM

echo "=========================================="
echo "FREEDOM Platform Daily Health Check"
echo "Date: $(date)"
echo "=========================================="

# 1. Service Status Check
echo "1. Checking Service Status..."
docker-compose ps
echo ""

# 2. Health Endpoints
echo "2. Testing Health Endpoints..."
make health
echo ""

# 3. Resource Usage
echo "3. System Resources..."
docker stats --no-stream
echo ""

# 4. Database Health
echo "4. Database Status..."
docker-compose exec postgres pg_isready -U freedom -d freedom_kb
docker-compose exec postgres psql -U freedom -d freedom_kb -c "SELECT COUNT(*) as documents FROM documents;"
echo ""

# 5. MLX Performance Test
echo "5. MLX Performance Check..."
python -c "
import time, requests
start = time.time()
try:
    response = requests.post('http://localhost:8001/v1/chat/completions',
        json={'messages': [{'role': 'user', 'content': 'Daily health check'}], 'max_tokens': 10},
        timeout=30)
    end = time.time()
    if response.status_code == 200:
        print(f'✅ MLX responding in {end-start:.2f}s')
    else:
        print(f'❌ MLX error: {response.status_code}')
except Exception as e:
    print(f'❌ MLX unreachable: {e}')
"
echo ""

# 6. Storage Check
echo "6. Storage Status..."
df -h /Volumes/DATA/FREEDOM
echo ""

# 7. Recent Errors
echo "7. Recent Error Check..."
docker-compose logs --since=24h | grep -i error | tail -5
echo ""

echo "Daily health check completed at $(date)"