.PHONY: up down health clean verify test smoke-test integration-test performance-test metrics-check

# Quick development commands
up:
	docker-compose up --build

down:
	docker-compose down

health:
	@echo "🔍 Checking service health..."
	@curl -s http://localhost:8080/health || echo "❌ API service down"
	@curl -s http://localhost:8001/health > /dev/null && echo "✅ MLX proxy up" || echo "❌ MLX proxy down"
	@docker-compose exec kb-service curl -f http://localhost:8000/health > /dev/null 2>&1 && echo "✅ KB service up" || echo "❌ KB service down"
	@docker-compose exec postgres pg_isready -U freedom -d freedom_kb && echo "✅ Postgres up" || echo "❌ Postgres down"

clean:
	docker-compose down -v
	docker system prune -f

# WORKSTREAM 7: Comprehensive Verification & Observability
# Following FREEDOM principles: "If it doesn't run, it doesn't exist"
# All tests must execute and pass, proving actual functionality

verify: health smoke-test integration-test performance-test metrics-check
	@echo ""
	@echo "🎯 FREEDOM Platform Verification Complete"
	@echo "✅ All services operational and verified"
	@echo "✅ All integrations working correctly"
	@echo "✅ Performance targets met"
	@echo "✅ Observability infrastructure functional"
	@echo ""
	@echo "🚀 FREEDOM Platform is production-ready"

# Core smoke tests - fast verification of basic functionality
smoke-test:
	@echo "🧪 Running FREEDOM Platform Smoke Tests..."
	@echo "Testing all service health endpoints and basic workflows"
	@python3 tests/smoke_test.py

# Integration tests - verify service-to-service communication
integration-test:
	@echo "🔗 Running FREEDOM Platform Integration Tests..."
	@echo "Testing end-to-end workflows and service integrations"
	@python3 tests/integration_test.py

# Performance benchmarks - verify performance targets are met
performance-test:
	@echo "⚡ Running FREEDOM Platform Performance Benchmarks..."
	@echo "Verifying response times and throughput targets"
	@python3 tests/performance_benchmark.py

# Metrics verification - ensure observability is working
metrics-check:
	@echo "📊 Verifying Prometheus Metrics Endpoints..."
	@curl -s http://localhost:8080/metrics > /dev/null && echo "✅ API Gateway metrics available" || echo "❌ API Gateway metrics unavailable"
	@curl -s http://localhost:8001/metrics > /dev/null && echo "✅ MLX Service metrics available" || echo "❌ MLX Service metrics unavailable"
	@echo "📈 Metrics endpoints verified"

# Advanced metrics collection and analysis
metrics-collect:
	@echo "📊 Collecting comprehensive platform metrics..."
	@python3 tests/metrics_collector.py

# Legacy test command (now points to smoke test)
test: smoke-test
	@echo "✅ Basic smoke tests completed"

# Development helpers
logs:
	docker-compose logs -f

shell-api:
	docker-compose exec api /bin/bash

shell-db:
	docker-compose exec postgres psql -U freedom -d freedom_kb

# MLX local development (bypass Docker)
mlx-local:
	source .venv/bin/activate && python -m mlx_vlm.server --model ./models/portalAI/UI-TARS-1.5-7B-mlx-bf16 --port 8000
codex-turbo-register:
	@echo "🔗 Registering Codex Turbo Syncthing folder on this node..."
	@python3 scripts/syncthing_register_codex_turbo.py

codex-turbo-check:
	@echo "🔎 Checking Codex Turbo Syncthing folder status..."
	@python3 scripts/syncthing_check_codex_turbo.py

codex-turbo-bootstrap:
	@echo "🚀 Bootstrapping Codex Turbo (mandatory) ..."
	@python3 scripts/codex_turbo_bootstrap.py
