# GEMINI.md

## Project Overview

This repository contains the **FREEDOM Platform**, a sophisticated, multi-service environment designed for AI-assisted development with a strong emphasis on local performance, verifiable functionality, and operational readiness. The platform is built around a set of core principles that demand functional reality over theoretical plans, encapsulated in the motto: "If it doesn't run, it doesn't exist."

The architecture is containerized using Docker and includes several key components:

*   **API Gateway:** An orchestrator for various backend services.
*   **Knowledge Base Service:** A vector search service with `pgvector` for similarity search.
*   **MLX Inference Service:** A proxy for machine learning model inference, with a fallback mechanism.
*   **TechKnowledge System:** A database of technical specifications.
*   **RAG System:** A Retrieval-Augmented Generation system for intelligent document chunking and hybrid search.
*   **Crawl Stack:** A set of services for web scraping and data extraction.
*   **Castle GUI:** A Next.js-based frontend for interacting with the platform.

The project heavily utilizes Python, with FastAPI for API development, along with PostgreSQL for data storage and Redis for caching and message queuing.

## Building and Running

### System Configuration

*   **OS:** macOS Tahoe 26.x+
*   **Hardware:** Apple Silicon (optimized)
*   **Python:** 3.13+
*   **Dependencies:** `postgresql@15`, `redis`

### Installation and Setup

1.  **Set up the Python environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Start the services:**
    ```bash
    docker-compose up -d
    ```

3.  **Run the RAG API:**
    ```bash
    cd services/rag_chunker
    python3 rag_api.py
    ```

### Health Checks and Verification

*   **Check all services health:**
    ```bash
    make health
    ```

*   **Run smoke tests:**
    ```bash
    make smoke-test
    ```

*   **Run the full verification suite:**
    ```bash
    make verify
    ```

*   **View container status:**
    ```bash
    docker ps
    ```

### Testing

*   **Unit Tests:**
    ```bash
    pytest /tests/unit/
    ```

*   **Integration Tests:**
    ```bash
    pytest /tests/integration/
    ```

*   **Performance Tests:**
    ```bash
    python tests/performance/mlx_performance_test.py
    ```

## Development Conventions

The project enforces a strict set of development conventions to ensure functional reality and high-quality code.

### Core Operating Principles

*   **Existence = Functionality:** A component "exists" only if it is fully functional, executable, and provides measurable value.
*   **Verification Requirements:** All components must be executable, process real input, produce meaningful output, integrate with other systems, and deliver value.
*   **Strict Language Protocols:** Avoid ambiguous terms like "implemented" or "ready" unless the component is fully functional.

### Definition of Done (DoD)

A feature is considered "done" only if it meets the following criteria:
1.  All unit and integration tests pass.
2.  The smoke test script runs successfully.
3.  Timestamped evidence of functionality is created.
4.  The feature is exercised via an end-to-end test.
5.  All documentation is updated.

### Quick Verification

Before any pull request, the following commands must be run successfully:
```bash
./scripts/maintenance/checks.sh
pytest -q tests/unit && pytest -q tests/integration
./scripts/maintenance/smoke.sh
python core/truth_engine/self_test.py --strict
```

### Documentation

*   All documentation files must be timestamped with the format `_YYYY-MM-DD_HHMM.ext`.

## Key Files and Directories

*   `README.md`: The main source of truth for the project, providing a detailed overview of the architecture, services, and development conventions.
*   `docker-compose.yml`: Defines the services, networks, and volumes for the Docker-based environment.
*   `Makefile`: Provides a set of commands for building, running, and testing the project.
*   `services/`: Contains the source code for the various microservices that make up the platform.
*   `documents/`: Contains timestamped documentation, reports, and other artifacts.
*   `tests/`: Contains the unit, integration, and performance tests for the project.
*   `scripts/`: Contains various utility and maintenance scripts.
