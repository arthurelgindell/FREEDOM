# FREEDOM MLX Inference Service
# Optimized for Apple Silicon with MLX acceleration

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Apple Silicon optimization
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create models directory
RUN mkdir -p /app/models

# Set environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8000
ENV MODEL_PATH=/app/models/portalAI/UI-TARS-1.5-7B-mlx-bf16
ENV MAX_TOKENS=2048
ENV TEMPERATURE=0.7

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]