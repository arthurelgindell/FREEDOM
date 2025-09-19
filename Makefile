.PHONY: up down health clean verify test

# Quick development commands
up:
	docker-compose up --build

down:
	docker-compose down

health:
	@echo "🔍 Checking service health..."
	@curl -s http://localhost:8080/health || echo "❌ API service down"
	@curl -s http://localhost:8000/docs > /dev/null && echo "✅ MLX service up" || echo "❌ MLX service down"
	@docker-compose exec postgres pg_isready -U freedom -d freedom_kb && echo "✅ Postgres up" || echo "❌ Postgres down"

clean:
	docker-compose down -v
	docker system prune -f

verify: test health
	@echo "✅ All verification passed"

test:
	@echo "🧪 Running smoke tests..."
	@python tests/smoke_test.py

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