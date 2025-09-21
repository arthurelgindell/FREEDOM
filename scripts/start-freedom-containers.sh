#!/bin/bash
# Start FREEDOM Docker containers after Docker Desktop starts
# This script waits for Docker to be ready, then starts all containers

echo "[$(date)] Starting FREEDOM container startup script" >> ~/Library/Logs/freedom-docker.log

# Wait for Docker to be ready (max 60 seconds)
COUNTER=0
while [ $COUNTER -lt 60 ]; do
    if docker ps >/dev/null 2>&1; then
        echo "[$(date)] Docker is ready" >> ~/Library/Logs/freedom-docker.log
        break
    fi
    echo "[$(date)] Waiting for Docker... ($COUNTER/60)" >> ~/Library/Logs/freedom-docker.log
    sleep 2
    COUNTER=$((COUNTER + 2))
done

# Check if Docker is running
if ! docker ps >/dev/null 2>&1; then
    echo "[$(date)] ERROR: Docker is not running after 60 seconds" >> ~/Library/Logs/freedom-docker.log
    exit 1
fi

# Navigate to FREEDOM directory and start containers
cd /Volumes/DATA/FREEDOM

# Start all containers with docker-compose
echo "[$(date)] Starting FREEDOM containers..." >> ~/Library/Logs/freedom-docker.log
docker-compose up -d >> ~/Library/Logs/freedom-docker.log 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date)] FREEDOM containers started successfully" >> ~/Library/Logs/freedom-docker.log

    # Wait a moment for containers to initialize
    sleep 5

    # Log container status
    echo "[$(date)] Container status:" >> ~/Library/Logs/freedom-docker.log
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep freedom >> ~/Library/Logs/freedom-docker.log
else
    echo "[$(date)] ERROR: Failed to start FREEDOM containers" >> ~/Library/Logs/freedom-docker.log
    exit 1
fi

echo "[$(date)] FREEDOM startup script completed" >> ~/Library/Logs/freedom-docker.log