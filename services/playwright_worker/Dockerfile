FROM mcr.microsoft.com/playwright/python:v1.48.0-focal

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    redis \
    playwright \
    httpx \
    asyncio

# Copy worker script
COPY worker.py .

# Run the worker
CMD ["python", "worker.py"]