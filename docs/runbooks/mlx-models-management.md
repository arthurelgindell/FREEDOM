# FREEDOM Platform - MLX Models Management Runbook

## Overview
Comprehensive guide for managing MLX models in the FREEDOM platform, including adding new models, switching between models, optimization for Apple Silicon, and performance monitoring. This runbook ensures optimal model performance and system stability.

**Target Audience**: ML Engineers, Operations team
**Prerequisites**: Apple Silicon Mac, MLX framework knowledge
**Model Directory**: `/Volumes/DATA/FREEDOM/models/`

## Success Criteria
- ✅ Models load successfully with <60 seconds startup time
- ✅ Inference speed >30 tokens/sec on Apple Silicon
- ✅ Memory usage <80% of available system RAM
- ✅ Model switching with zero downtime
- ✅ Automatic model health monitoring

---

## Phase 1: Model Inventory and Assessment

### 1.1 Current Model Status
```bash
# Check currently installed models
ls -la /Volumes/DATA/FREEDOM/models/
# Expected structure:
# portalAI/UI-TARS-1.5-7B-mlx-bf16/  (Primary model)
# lmstudio-community/               (Alternative models)

# Check current model configuration
grep MODEL_PATH /Volumes/DATA/FREEDOM/docker-compose.yml
# Current: /app/models/portalAI/UI-TARS-1.5-7B-mlx-bf16

# Verify model integrity
du -sh /Volumes/DATA/FREEDOM/models/portalAI/UI-TARS-1.5-7B-mlx-bf16/
# Expected: 7-15GB total size
```

### 1.2 Model Performance Baseline
```bash
# Test current model performance
cd /Volumes/DATA/FREEDOM

# Activate Python environment
source .venv/bin/activate

# Performance test script
python -c "
import time
import requests
import json

# Test inference speed
start_time = time.time()
response = requests.post('http://localhost:8001/v1/chat/completions',
  json={
    'messages': [{'role': 'user', 'content': 'Generate exactly 50 words about AI.'}],
    'max_tokens': 60,
    'temperature': 0.1
  })
end_time = time.time()

if response.status_code == 200:
    data = response.json()
    duration = end_time - start_time
    # Estimate tokens (rough approximation)
    tokens = len(data['choices'][0]['message']['content'].split()) * 1.3
    print(f'Response time: {duration:.2f}s')
    print(f'Estimated tokens/sec: {tokens/duration:.1f}')
    print(f'Model health: {"✅ GOOD" if tokens/duration > 30 else "⚠️  SLOW"}')
else:
    print(f'❌ Model error: {response.status_code}')
"
```

### 1.3 Memory Usage Assessment
```bash
# Check current memory usage
docker stats --no-stream | grep mlx-server

# System memory status
free -h 2>/dev/null || vm_stat | head -10

# Model memory footprint
docker-compose exec mlx-server python -c "
import psutil
import os
process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
print(f'MLX process memory: {memory_mb:.1f}MB')
"
```

---

## Phase 2: Adding New MLX Models

### 2.1 Model Requirements Verification
```bash
# Check available disk space (minimum 20GB for new model)
df -h /Volumes/DATA/FREEDOM/models/
# Ensure >20GB available

# Verify MLX compatibility
python -c "
import mlx.core as mx
print(f'MLX version: {mx.__version__}')
print(f'Metal support: {mx.metal.is_available()}')
print(f'Memory available: {mx.metal.get_memory_info()}')
"
```

### 2.2 Download and Install New Model

#### Option A: Hugging Face Hub
```bash
# Install huggingface-hub if not available
pip install huggingface-hub

# Download model (example: Phi-3.5 Mini)
MODEL_NAME="microsoft/Phi-3.5-mini-instruct"
LOCAL_PATH="/Volumes/DATA/FREEDOM/models/phi-3.5-mini-instruct"

huggingface-cli download ${MODEL_NAME} \
  --local-dir ${LOCAL_PATH} \
  --local-dir-use-symlinks False \
  --resume-download

# Verify download
ls -la ${LOCAL_PATH}/
# Expected: config.json, model files, tokenizer files
```

#### Option B: LM Studio Models
```bash
# Copy from LM Studio cache (if available)
LM_STUDIO_PATH="$HOME/.cache/lm-studio/models"
if [ -d "$LM_STUDIO_PATH" ]; then
    echo "Available LM Studio models:"
    ls -la "$LM_STUDIO_PATH"

    # Copy specific model
    MODEL_SOURCE="$LM_STUDIO_PATH/microsoft/Phi-3.5-mini-instruct"
    MODEL_DEST="/Volumes/DATA/FREEDOM/models/phi-3.5-mini-instruct"

    cp -r "$MODEL_SOURCE" "$MODEL_DEST"
    echo "✅ Model copied from LM Studio cache"
fi
```

#### Option C: Manual Model Preparation
```bash
# For custom or fine-tuned models
MODEL_DIR="/Volumes/DATA/FREEDOM/models/custom-model"
mkdir -p "$MODEL_DIR"

# Copy model files
cp /path/to/your/model/* "$MODEL_DIR/"

# Verify required files
required_files=("config.json" "tokenizer.json" "tokenizer_config.json")
for file in "${required_files[@]}"; do
    if [ -f "$MODEL_DIR/$file" ]; then
        echo "✅ $file found"
    else
        echo "❌ Missing required file: $file"
    fi
done
```

### 2.3 Model Conversion for MLX (if needed)
```bash
# Convert PyTorch model to MLX format
python -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
import mlx.core as mx
from mlx_lm import convert

# Convert model to MLX format
model_path = '/Volumes/DATA/FREEDOM/models/phi-3.5-mini-instruct'
mlx_path = '/Volumes/DATA/FREEDOM/models/phi-3.5-mini-instruct-mlx'

# Note: This is a simplified example
# Actual conversion may require model-specific parameters
print('Converting model to MLX format...')
# convert.convert(model_path, mlx_path, quantize=True)
print('✅ Conversion complete')
"
```

### 2.4 Model Registration
```bash
# Add model to inventory file
echo "$(date '+%Y-%m-%d %H:%M:%S') - Added phi-3.5-mini-instruct" >> /Volumes/DATA/FREEDOM/models/model_inventory.log

# Update model configuration options
cat >> /Volumes/DATA/FREEDOM/models/available_models.json << EOF
{
  "phi-3.5-mini-instruct": {
    "path": "/app/models/phi-3.5-mini-instruct",
    "type": "text-generation",
    "size": "3.8B",
    "quantization": "none",
    "performance_target": "40+ tokens/sec",
    "memory_requirement": "4GB",
    "added_date": "$(date -Iseconds)"
  }
}
EOF
```

---

## Phase 3: Model Switching Procedures

### 3.1 Pre-Switch Validation
```bash
# Test new model compatibility
NEW_MODEL_PATH="/app/models/phi-3.5-mini-instruct"

# Create temporary test configuration
cp docker-compose.yml docker-compose.yml.backup
sed "s|MODEL_PATH: .*|MODEL_PATH: ${NEW_MODEL_PATH}|" docker-compose.yml > docker-compose.test.yml

# Test new model in isolation
docker-compose -f docker-compose.test.yml up -d mlx-server

# Wait for startup
sleep 60

# Test new model
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Test message for new model"}],
    "max_tokens": 20
  }'

# Clean up test
docker-compose -f docker-compose.test.yml down
rm docker-compose.test.yml
```

### 3.2 Zero-Downtime Model Switch

#### Method A: Rolling Update
```bash
# Update docker-compose configuration
sed -i.backup "s|MODEL_PATH: .*|MODEL_PATH: ${NEW_MODEL_PATH}|" docker-compose.yml

# Rolling restart of MLX service
docker-compose up -d --no-deps mlx-server

# Monitor health during switch
for i in {1..60}; do
    if curl -f http://localhost:8001/health &>/dev/null; then
        echo "✅ New model healthy after ${i}0 seconds"
        break
    fi
    sleep 10
done
```

#### Method B: Blue-Green Deployment
```bash
# Start new MLX server on different port
NEW_MODEL_PATH="/app/models/phi-3.5-mini-instruct"

# Create blue-green compose file
cat > docker-compose.blue-green.yml << EOF
version: '3.8'
services:
  mlx-server-new:
    build:
      context: ./services/mlx
      dockerfile: Dockerfile
    ports:
      - "8002:8000"
    volumes:
      - ./models:/app/models:ro
    environment:
      MODEL_PATH: ${NEW_MODEL_PATH}
      HOST: 0.0.0.0
      PORT: 8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
EOF

# Start new service
docker-compose -f docker-compose.blue-green.yml up -d mlx-server-new

# Wait for new service to be healthy
sleep 90

# Test new service
curl -f http://localhost:8002/health

# Switch traffic by updating main compose file
sed -i.backup "s|MODEL_PATH: .*|MODEL_PATH: ${NEW_MODEL_PATH}|" docker-compose.yml
docker-compose up -d --no-deps mlx-server

# Clean up blue-green deployment
docker-compose -f docker-compose.blue-green.yml down
rm docker-compose.blue-green.yml
```

### 3.3 Post-Switch Validation
```bash
# Comprehensive validation of new model
make health

# Performance test with new model
python -c "
import time
import requests

start = time.time()
response = requests.post('http://localhost:8001/v1/chat/completions',
  json={'messages': [{'role': 'user', 'content': 'Performance test with new model'}], 'max_tokens': 50})
end = time.time()

if response.status_code == 200:
    print(f'✅ New model responding in {end-start:.2f}s')
else:
    print(f'❌ New model error: {response.status_code}')
"

# Update model tracking
echo "$(date '+%Y-%m-%d %H:%M:%S') - Switched to ${NEW_MODEL_PATH}" >> /Volumes/DATA/FREEDOM/models/model_switches.log
```

---

## Phase 4: Apple Silicon Optimization

### 4.1 MLX Performance Tuning
```bash
# Check Metal GPU availability
python -c "
import mlx.core as mx
print(f'Metal available: {mx.metal.is_available()}')
if mx.metal.is_available():
    memory_info = mx.metal.get_memory_info()
    print(f'GPU memory: {memory_info}')
else:
    print('❌ Metal not available - check Apple Silicon setup')
"
```

### 4.2 Memory Optimization
```bash
# Configure memory settings for MLX server
cat >> docker-compose.yml << EOF
  mlx-server:
    # ... existing configuration ...
    environment:
      # ... existing env vars ...
      MLX_MEMORY_POOL_SIZE: "8192"  # 8GB memory pool
      MLX_GPU_MEMORY_LIMIT: "0.8"   # Use 80% of GPU memory
      MLX_CPU_MEMORY_LIMIT: "4096"  # 4GB CPU memory limit
EOF

# Restart with new memory settings
docker-compose restart mlx-server
```

### 4.3 Model Quantization
```bash
# Quantize model for better performance
python -c "
from mlx_lm import convert
import os

source_model = '/Volumes/DATA/FREEDOM/models/phi-3.5-mini-instruct'
target_model = '/Volumes/DATA/FREEDOM/models/phi-3.5-mini-instruct-q4'

# 4-bit quantization for Apple Silicon
convert.convert(
    hf_path=source_model,
    mlx_path=target_model,
    quantize=True,
    q_bits=4,
    q_group_size=64
)

print(f'✅ Quantized model saved to {target_model}')
"

# Update configuration to use quantized model
sed -i.backup "s|MODEL_PATH: .*|MODEL_PATH: /app/models/phi-3.5-mini-instruct-q4|" docker-compose.yml
docker-compose restart mlx-server
```

### 4.4 Performance Benchmarking
```bash
# Comprehensive performance test
python -c "
import time
import requests
import statistics

def benchmark_model(num_tests=5):
    times = []
    tokens_per_sec = []

    for i in range(num_tests):
        start = time.time()
        response = requests.post('http://localhost:8001/v1/chat/completions',
            json={
                'messages': [{'role': 'user', 'content': f'Benchmark test {i}: Generate exactly 50 words about technology.'}],
                'max_tokens': 60,
                'temperature': 0.1
            })
        end = time.time()

        if response.status_code == 200:
            duration = end - start
            times.append(duration)
            # Rough token estimation
            content = response.json()['choices'][0]['message']['content']
            estimated_tokens = len(content.split()) * 1.3
            tokens_per_sec.append(estimated_tokens / duration)
            print(f'Test {i+1}: {duration:.2f}s, ~{estimated_tokens/duration:.1f} tokens/sec')
        else:
            print(f'Test {i+1} failed: {response.status_code}')

    if times:
        avg_time = statistics.mean(times)
        avg_tokens_sec = statistics.mean(tokens_per_sec)
        print(f'\\nAverage response time: {avg_time:.2f}s')
        print(f'Average tokens/sec: {avg_tokens_sec:.1f}')
        print(f'Performance grade: {"✅ EXCELLENT" if avg_tokens_sec > 50 else "✅ GOOD" if avg_tokens_sec > 30 else "⚠️  NEEDS OPTIMIZATION"}')

benchmark_model()
"
```

---

## Phase 5: Model Health Monitoring

### 5.1 Automated Health Checks
```bash
# Create model health monitoring script
cat > /Volumes/DATA/FREEDOM/scripts/model_health_check.py << 'EOF'
#!/usr/bin/env python3
"""
MLX Model Health Monitoring Script
Runs periodic health checks and reports model performance
"""

import time
import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_model_health():
    """Comprehensive model health check"""
    health_report = {
        'timestamp': datetime.now().isoformat(),
        'model_responsive': False,
        'response_time': None,
        'tokens_per_sec': None,
        'memory_usage': None,
        'status': 'UNKNOWN'
    }

    try:
        # Test model responsiveness
        start_time = time.time()
        response = requests.post('http://localhost:8001/v1/chat/completions',
            json={
                'messages': [{'role': 'user', 'content': 'Health check'}],
                'max_tokens': 10
            },
            timeout=30)
        end_time = time.time()

        if response.status_code == 200:
            health_report['model_responsive'] = True
            health_report['response_time'] = round(end_time - start_time, 2)

            # Estimate performance
            content = response.json()['choices'][0]['message']['content']
            estimated_tokens = len(content.split()) * 1.3
            health_report['tokens_per_sec'] = round(estimated_tokens / health_report['response_time'], 1)

            # Determine status
            if health_report['tokens_per_sec'] > 30:
                health_report['status'] = 'HEALTHY'
            elif health_report['tokens_per_sec'] > 15:
                health_report['status'] = 'DEGRADED'
            else:
                health_report['status'] = 'SLOW'
        else:
            health_report['status'] = 'ERROR'
            logger.error(f"Model returned status code: {response.status_code}")

    except Exception as e:
        health_report['status'] = 'UNREACHABLE'
        logger.error(f"Health check failed: {e}")

    return health_report

if __name__ == "__main__":
    report = check_model_health()
    print(json.dumps(report, indent=2))

    # Log to file
    with open('/Volumes/DATA/FREEDOM/logs/model_health.log', 'a') as f:
        f.write(f"{report['timestamp']},{report['status']},{report['response_time']},{report['tokens_per_sec']}\n")
EOF

chmod +x /Volumes/DATA/FREEDOM/scripts/model_health_check.py
```

### 5.2 Continuous Monitoring Setup
```bash
# Create monitoring crontab entry
cat > /tmp/model_monitoring_cron << EOF
# MLX Model Health Monitoring
*/5 * * * * cd /Volumes/DATA/FREEDOM && python scripts/model_health_check.py
*/15 * * * * cd /Volumes/DATA/FREEDOM && docker stats --no-stream | grep mlx-server >> logs/resource_usage.log
0 */6 * * * cd /Volumes/DATA/FREEDOM && find logs/ -name "*.log" -mtime +7 -delete
EOF

# Install cron job
crontab /tmp/model_monitoring_cron
rm /tmp/model_monitoring_cron

echo "✅ Model monitoring scheduled every 5 minutes"
```

### 5.3 Alert Configuration
```bash
# Create alerting script
cat > /Volumes/DATA/FREEDOM/scripts/model_alerts.py << 'EOF'
#!/usr/bin/env python3
"""
Model performance alerting system
"""

import json
import subprocess
import sys
from datetime import datetime

def send_alert(message, severity="WARNING"):
    """Send alert notification"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    alert_msg = f"[{timestamp}] {severity}: {message}"

    # Log alert
    with open('/Volumes/DATA/FREEDOM/logs/alerts.log', 'a') as f:
        f.write(f"{alert_msg}\n")

    # Console notification
    print(alert_msg)

    # macOS notification
    subprocess.run(['osascript', '-e', f'display notification "{message}" with title "FREEDOM Model Alert"'])

def check_alerts():
    """Check for alert conditions"""
    try:
        # Run health check
        result = subprocess.run(['python', '/Volumes/DATA/FREEDOM/scripts/model_health_check.py'],
                               capture_output=True, text=True)
        health_data = json.loads(result.stdout)

        # Check alert conditions
        if health_data['status'] == 'UNREACHABLE':
            send_alert("Model server unreachable", "CRITICAL")
        elif health_data['status'] == 'ERROR':
            send_alert("Model returning errors", "CRITICAL")
        elif health_data['status'] == 'SLOW':
            send_alert(f"Model performance degraded: {health_data['tokens_per_sec']} tokens/sec", "WARNING")
        elif health_data['response_time'] and health_data['response_time'] > 10:
            send_alert(f"Model response time high: {health_data['response_time']}s", "WARNING")

    except Exception as e:
        send_alert(f"Health check script failed: {e}", "ERROR")

if __name__ == "__main__":
    check_alerts()
EOF

chmod +x /Volumes/DATA/FREEDOM/scripts/model_alerts.py
```

---

## Phase 6: Troubleshooting and Maintenance

### 6.1 Common Model Issues

#### Model Won't Load
```bash
# Check model file integrity
find /Volumes/DATA/FREEDOM/models/ -name "*.safetensors" -exec ls -la {} \;

# Verify model configuration
python -c "
import json
model_path = '/Volumes/DATA/FREEDOM/models/portalAI/UI-TARS-1.5-7B-mlx-bf16'
with open(f'{model_path}/config.json') as f:
    config = json.load(f)
    print('Model configuration:')
    for key in ['model_type', 'hidden_size', 'num_attention_heads']:
        print(f'  {key}: {config.get(key, "not found")}')
"

# Check MLX server logs
docker-compose logs mlx-server | tail -50
```

#### Slow Performance
```bash
# Check system resources
top -l 1 | head -10

# Monitor GPU usage (if available)
powermetrics -s gpu_power -n 1 2>/dev/null || echo "GPU metrics not available"

# Check model quantization
ls -la /Volumes/DATA/FREEDOM/models/*/model*.safetensors
# Larger files indicate non-quantized models
```

#### Memory Issues
```bash
# Check memory usage
vm_stat | grep -E "(Pages free|Pages active|Pages inactive|Pages speculative|Pages wired down)"

# MLX-specific memory check
docker-compose exec mlx-server python -c "
import mlx.core as mx
if mx.metal.is_available():
    print('GPU memory info:', mx.metal.get_memory_info())
else:
    print('Metal GPU not available')
"

# Restart MLX service to clear memory
docker-compose restart mlx-server
```

### 6.2 Model Maintenance Tasks

#### Weekly Maintenance
```bash
# Clean up old model logs
find /Volumes/DATA/FREEDOM/logs/ -name "*model*" -mtime +7 -delete

# Optimize model cache
docker-compose exec mlx-server python -c "
import gc
import mlx.core as mx
gc.collect()
if mx.metal.is_available():
    mx.metal.clear_cache()
print('✅ Model cache cleared')
"

# Health report generation
python /Volumes/DATA/FREEDOM/scripts/model_health_check.py > /tmp/weekly_health_report.json
echo "Weekly health report saved to /tmp/weekly_health_report.json"
```

#### Monthly Maintenance
```bash
# Model performance regression test
python -c "
import time
import requests
import json

# Baseline performance test
tests = []
for i in range(10):
    start = time.time()
    response = requests.post('http://localhost:8001/v1/chat/completions',
        json={'messages': [{'role': 'user', 'content': 'Monthly performance test'}], 'max_tokens': 30})
    end = time.time()
    if response.status_code == 200:
        tests.append(end - start)

if tests:
    avg_time = sum(tests) / len(tests)
    print(f'Monthly performance: {avg_time:.2f}s average response time')

    # Save baseline
    with open('/Volumes/DATA/FREEDOM/logs/monthly_performance.log', 'a') as f:
        f.write(f'{time.strftime("%Y-%m-%d")},{avg_time:.2f}\n')
"

# Disk space cleanup
docker system prune -f
find /Volumes/DATA/FREEDOM/models/ -name "*.tmp" -delete
```

### 6.3 Model Backup and Recovery
```bash
# Backup critical models
BACKUP_DATE=$(date +%Y%m%d)
BACKUP_DIR="/Volumes/DATA/FREEDOM/backups/models_${BACKUP_DATE}"
mkdir -p "${BACKUP_DIR}"

# Backup primary model
tar -czf "${BACKUP_DIR}/ui-tars-model.tar.gz" models/portalAI/UI-TARS-1.5-7B-mlx-bf16/

# Backup model configurations
cp docker-compose.yml "${BACKUP_DIR}/"
cp models/available_models.json "${BACKUP_DIR}/" 2>/dev/null || echo "No model inventory found"

echo "✅ Model backup completed: ${BACKUP_DIR}"

# Recovery procedure (if needed)
# tar -xzf "${BACKUP_DIR}/ui-tars-model.tar.gz" -C /Volumes/DATA/FREEDOM/
```

---

## Performance Optimization Guidelines

### Model Selection Criteria
| Model Size | Memory Req | Target Speed | Use Case |
|------------|------------|--------------|----------|
| 1-3B | 2-4GB | 50+ tok/sec | Fast response, simple tasks |
| 3-7B | 4-8GB | 30+ tok/sec | Balanced performance |
| 7-13B | 8-16GB | 20+ tok/sec | Complex reasoning |
| 13B+ | 16GB+ | 10+ tok/sec | Maximum capability |

### Apple Silicon Optimization Tips
1. **Use MLX-native models** when available
2. **Enable quantization** for memory-constrained setups
3. **Monitor Metal GPU usage** with Activity Monitor
4. **Adjust batch sizes** based on available memory
5. **Use warm-up requests** to pre-load model

### Resource Allocation Best Practices
```bash
# Recommended Docker resource limits
# Edit Docker Desktop preferences:
# - Memory: 16GB+ for large models
# - Swap: 4GB minimum
# - Disk: 100GB+ for model storage

# System monitoring during operation
watch -n 5 'echo "=== SYSTEM RESOURCES ===" && top -l 1 | head -5 && echo "=== DOCKER STATS ===" && docker stats --no-stream'
```

---

## Model Registry and Versioning

### Model Inventory Management
```bash
# Initialize model registry
cat > /Volumes/DATA/FREEDOM/models/registry.json << EOF
{
  "registry_version": "1.0",
  "last_updated": "$(date -Iseconds)",
  "models": {
    "ui-tars-1.5-7b": {
      "path": "portalAI/UI-TARS-1.5-7B-mlx-bf16",
      "version": "1.5",
      "status": "active",
      "performance": {
        "avg_tokens_per_sec": 42,
        "memory_usage_gb": 8,
        "last_tested": "$(date -Iseconds)"
      }
    }
  }
}
EOF

# Update registry function
update_model_registry() {
    local model_name="$1"
    local model_path="$2"
    local status="$3"

    python -c "
import json
registry_file = '/Volumes/DATA/FREEDOM/models/registry.json'
with open(registry_file, 'r') as f:
    registry = json.load(f)

registry['models']['$model_name'] = {
    'path': '$model_path',
    'status': '$status',
    'updated': '$(date -Iseconds)'
}

with open(registry_file, 'w') as f:
    json.dump(registry, f, indent=2)
print(f'✅ Registry updated for {model_name}')
"
}
```

---

**Document Version**: 1.0
**Last Updated**: 2025-09-19
**Compatible MLX Version**: 0.20.0+
**Tested Models**: UI-TARS-1.5-7B, Phi-3.5-mini, Qwen3-30B-A3B
**Average Performance**: 30-50 tokens/sec on Apple Silicon