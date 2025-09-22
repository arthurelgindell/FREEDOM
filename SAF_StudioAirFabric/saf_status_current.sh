#!/bin/bash
# Studio Air Fabric - Current Status Check
# Updated for single-node configuration

echo "========================================="
echo "    Studio Air Fabric Status Check      "
echo "========================================="
echo ""

# Check if Ray is running
echo "📍 Ray Status:"
if pgrep -f "ray::" > /dev/null 2>&1; then
    echo "   ✅ Ray is running"
    
    # Get Ray status using Python
    cd /Volumes/DATA/FREEDOM
    source .venv/bin/activate 2>/dev/null
    
    python3 -c "
import ray
try:
    ray.init(address='auto', ignore_reinit_error=True)
    resources = ray.cluster_resources()
    nodes = ray.nodes()
    alive = len([n for n in nodes if n['Alive']])
    cpus = resources.get('CPU', 0)
    memory = resources.get('memory', 0) / (1024**3)
    object_store = resources.get('object_store_memory', 0) / (1024**3)
    
    print(f'   Nodes: {alive}')
    print(f'   CPUs: {int(cpus)}')
    print(f'   Memory: {memory:.1f} GB')
    print(f'   Object Store: {object_store:.1f} GB')
    
    # Check for running tasks
    from ray import state
    tasks = state.tasks()
    if tasks:
        print(f'   Active Tasks: {len(tasks)}')
    
    ray.shutdown()
except Exception as e:
    print(f'   ⚠️  Could not connect to Ray: {e}')
" 2>/dev/null || echo "   ⚠️  Ray Python check failed"
    
else
    echo "   ❌ Ray is not running"
    echo ""
    echo "   To start Ray:"
    echo "   cd /Volumes/DATA/FREEDOM"
    echo "   source .venv/bin/activate"
    echo "   ray start --head --num-cpus=32"
fi

echo ""
echo "📊 System Resources:"
# Get system info
python3 -c "
import psutil
cpu_percent = psutil.cpu_percent(interval=1)
memory = psutil.virtual_memory()
print(f'   CPU Usage: {cpu_percent}%')
print(f'   Memory: {memory.used / (1024**3):.1f} / {memory.total / (1024**3):.0f} GB ({memory.percent}%)')
print(f'   Available: {memory.available / (1024**3):.1f} GB')
" 2>/dev/null || echo "   ⚠️  System info unavailable"

echo ""
echo "🧪 Quick Test Commands:"
echo "   Single node test: python test_saf_single_node.py"
echo "   Matrix test: python saf_test.py"
echo "   2-node test: python saf_2node_test.py (requires setup)"

echo ""
echo "📚 Documentation:"
echo "   Full docs: SAF_StudioAirFabric/SAF_COMPLETE_DOCUMENTATION_*.md"
echo "   Test report: SAF_TEST_REPORT.md"

echo ""
echo "========================================="
echo "Studio Air Fabric - Ready for ML workloads"
echo "========================================="
