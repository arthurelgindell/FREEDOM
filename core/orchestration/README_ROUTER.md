# Intelligent Model Router

## Overview

The Intelligent Model Router automatically selects the optimal AI model for each task based on complexity, cost, performance, and availability. It seamlessly routes between your local MLX models (via LM Studio) and commercial APIs (Claude, OpenAI, Gemini).

## Key Features

### 🎯 Smart Routing
- **Complexity-based routing**: Simple tasks → Local models, Complex tasks → Commercial APIs
- **Task-type optimization**: Code generation, reasoning, analysis, creative tasks
- **Automatic escalation**: Falls back to commercial APIs when local models fail
- **Cost optimization**: Prioritizes free local models when appropriate

### 📊 Performance Monitoring
- **Real-time analytics**: Track model performance, costs, and success rates
- **Optimization recommendations**: AI-driven suggestions for better routing
- **Cost tracking**: Monitor daily budgets and token usage
- **Performance metrics**: Response times, success rates, accuracy

### 🔄 Fallback & Reliability
- **Automatic retry**: Failed requests automatically retry with different models
- **Graceful degradation**: System continues working even if some models are unavailable
- **Health checks**: Monitors model availability in real-time

## Quick Start

### 1. Basic Usage

```python
from core.orchestration.agents.routed_agent import create_routed_coder_agent

# Create a routed agent
agent = create_routed_coder_agent()

# Generate response (automatically routes to best model)
response = await agent.generate_response(
    "Write a Python function to sort a list",
    context={"complexity": 3}
)
```

### 2. Direct Router Usage

```python
from core.orchestration.model_router import IntelligentModelRouter, TaskType
from core.orchestration.model_client import UnifiedModelClient

# Create router and client
router = IntelligentModelRouter()
client = UnifiedModelClient(router)

# Generate with automatic routing
result = await client.generate(
    "Analyze the pros and cons of microservices",
    TaskType.REASONING,
    complexity=7
)
```

### 3. Custom Routing

```python
# Force specific model for testing
result = await client.generate(
    "Write hello world",
    TaskType.CODE_GENERATION,
    complexity=2,
    context={"force_model": "local_mlx"}
)
```

## Configuration

### Environment Variables

Set up API keys for commercial models:

```bash
export ANTHROPIC_API_KEY="your_claude_key"
export OPENAI_API_KEY="your_openai_key"
export GEMINI_API_KEY="your_gemini_key"
```

### LM Studio Setup

Ensure LM Studio is running on `localhost:1234` with your models loaded:
- `qwen/qwen3-30b-a3b-2507` (recommended for code generation)
- `mistralai/devstral-small-2507` (good general purpose)

## Routing Logic

### Decision Tree

1. **Forced Routing**: If `force_model` in context, use that model
2. **Local First**: Simple tasks (complexity ≤ 3) → Local MLX
3. **Escalation**: After 2+ local failures → Commercial API
4. **Complex Tasks**: High complexity (≥ 7) → Claude/Gemini for reasoning
5. **Default**: First preferred model for task type

### Task Type Preferences

- **Code Generation**: Local MLX → OpenAI
- **Code Refactoring**: Local MLX → Claude
- **Reasoning**: Claude → Gemini
- **Analysis**: Claude → Gemini
- **Completion**: OpenAI → Local MLX
- **Creative**: Claude → Gemini

## Analytics & Monitoring

### Performance Reports

```python
from core.orchestration.router_analytics import RouterAnalytics

analytics = RouterAnalytics()

# Get performance metrics
performance = analytics.get_model_performance_report()
print(f"Models tracked: {len(performance)}")

# Get cost analysis
costs = analytics.get_cost_analysis()
print(f"Total cost: ${costs['total_cost']:.6f}")

# Get optimization recommendations
recommendations = analytics.get_optimization_recommendations()
```

### Database Schema

The router uses SQLite for analytics storage (`router_analytics.db`):

```sql
CREATE TABLE routing_decisions (
    id INTEGER PRIMARY KEY,
    timestamp REAL,
    objective TEXT,
    task_type TEXT,
    complexity INTEGER,
    selected_model TEXT,
    reasoning TEXT,
    estimated_cost REAL,
    actual_cost REAL,
    execution_time REAL,
    estimated_time REAL,
    success BOOLEAN,
    tokens_used INTEGER
);
```

## Testing

### Run Test Suite

```bash
python3 core/orchestration/test_router.py
```

### Run Examples

```bash
python3 core/orchestration/example_usage.py
```

### Integration Test

```bash
python3 core/orchestration/integrate_router.py
```

## Architecture

### Core Components

1. **`model_router.py`**: Core routing logic and decision engine
2. **`model_client.py`**: Unified client for all model APIs
3. **`router_analytics.py`**: Performance monitoring and optimization
4. **`agents/routed_agent.py`**: Enhanced agents with intelligent routing

### Model Clients

- **`LMStudioClient`**: Local models via LM Studio API
- **`ClaudeClient`**: Anthropic Claude API
- **`OpenAIClient`**: OpenAI GPT API
- **`GeminiClient`**: Google Gemini API

## Performance Metrics

### Current Performance (from your tests)

- **Qwen 3-30B**: 393 tokens/sec, 1.56s response time
- **Mistral Devstral**: 200 tokens/sec
- **Success Rate**: 100% for local models
- **Cost**: $0.00 for local models

### Commercial API Performance (estimated)

- **Claude 3.5 Sonnet**: 50 tokens/sec, $3/million tokens
- **GPT-4o**: 60 tokens/sec, $1/million tokens
- **Gemini 1.5 Pro**: 40 tokens/sec, $2/million tokens

## Best Practices

### 1. Complexity Assessment

Use appropriate complexity scores:
- **1-3**: Simple tasks (local models)
- **4-6**: Medium complexity (local or commercial)
- **7-10**: Complex tasks (commercial APIs)

### 2. Task Type Classification

Be specific about task types for better routing:
- `code_generation`: Writing new code
- `code_refactor`: Improving existing code
- `reasoning`: Logical analysis and problem-solving
- `analysis`: Data analysis and research
- `completion`: Finishing partial content
- `creative`: Creative writing and ideation

### 3. Cost Management

- Monitor daily costs with `get_daily_budget_remaining()`
- Use local models for high-volume, simple tasks
- Reserve commercial APIs for complex, high-value tasks

### 4. Error Handling

- Always check `result["success"]` before using responses
- Implement retry logic for critical operations
- Monitor escalation patterns in analytics

## Troubleshooting

### Common Issues

1. **LM Studio not responding**: Check if running on `localhost:1234`
2. **API key errors**: Verify environment variables are set
3. **Routing to wrong model**: Check complexity scores and task types
4. **High costs**: Review analytics and adjust complexity thresholds

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

### Planned Features

1. **Dynamic model loading**: Load/unload models based on demand
2. **A/B testing**: Compare model performance on same tasks
3. **Custom routing rules**: User-defined routing logic
4. **Model fine-tuning**: Optimize routing based on user feedback
5. **Multi-modal routing**: Support for image, audio, and video models

### Integration Opportunities

1. **Orchestrator graphs**: Integrate with existing workflow systems
2. **Slack integration**: Route messages to appropriate models
3. **Web interface**: Dashboard for monitoring and configuration
4. **API gateway**: Expose router as a service

## Support

For issues or questions:
1. Check the test suite output
2. Review analytics for performance insights
3. Examine routing decisions in logs
4. Test with forced model selection

The router is designed to be self-healing and will automatically optimize based on real usage patterns.

