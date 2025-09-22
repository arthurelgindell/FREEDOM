#!/bin/bash
# Studio Air Fabric - Quick Status Check

echo "========================================="
echo "    Studio Air Fabric Status Check      "
echo "========================================="
echo ""

# Check ALPHA
echo "📍 ALPHA Node (192.168.1.172):"
source ~/saf-venv-39/bin/activate 2>/dev/null
if ray status 2>/dev/null | grep -q "Active:"; then
    echo "   ✅ Ray is running"
    ray status 2>/dev/null | grep "CPU" | head -1
else
    echo "   ❌ Ray is not running"
fi

# Check BETA
echo ""
echo "📍 BETA Node (192.168.1.42):"
ssh -o ConnectTimeout=5 arthurdell@beta "ps aux | grep ray | grep -v grep" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Ray is running"
else
    echo "   ❌ Ray is not running"
fi

# Check Dashboard
echo ""
echo "📊 Dashboard:"
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.172:8265 > /tmp/dash_status 2>/dev/null
if [ "$(cat /tmp/dash_status)" = "200" ]; then
    echo "   ✅ Available at http://192.168.1.172:8265"
else
    echo "   ❌ Not accessible"
fi

# Cluster Summary
echo ""
echo "📈 Cluster Summary:"
source ~/saf-venv-39/bin/activate 2>/dev/null
python3 -c "
import ray
try:
    ray.init(address='auto', ignore_reinit_error=True)
    nodes = ray.nodes()
    alive = len([n for n in nodes if n['Alive']])
    cpus = ray.cluster_resources().get('CPU', 0)
    memory = ray.cluster_resources().get('memory', 0) / (1024**3)
    print(f'   Nodes: {alive}')
    print(f'   Total CPUs: {int(cpus)}')
    print(f'   Total Memory: {memory:.1f} GB')
    ray.shutdown()
except:
    print('   Cluster not available')
" 2>/dev/null

echo ""
echo "========================================="
echo "Use './saf_status.sh' anytime to check status"
echo "========================================="