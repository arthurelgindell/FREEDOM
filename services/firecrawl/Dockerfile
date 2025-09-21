FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    firecrawl-py \
    fastapi \
    uvicorn \
    httpx \
    redis

COPY app.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8004"]