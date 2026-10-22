#!/bin/bash
# Build and deploy SpliceGAIP on server
cd /home/wang_zi_wei/splicegaip

echo "=== Checking files ==="
ls -lh requirements.txt .env Dockerfile docker-compose.yml

echo ""
echo "=== Building Docker image ==="
docker compose build --no-cache > /tmp/splicegaip-build.log 2>&1 &
BUILD_PID=$!

echo "Build started with PID: $BUILD_PID"
echo "Monitor progress with: tail -f /tmp/splicegaip-build.log"

# Wait for build to complete
wait $BUILD_PID
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=== Build successful ==="
    echo "Starting containers..."
    docker compose up -d
    echo ""
    echo "=== Container status ==="
    docker compose ps
    echo ""
    echo "=== Waiting 30 seconds for API to start ==="
    sleep 30
    echo ""
    echo "=== Health check ==="
    curl -s http://localhost:8800/api/health | python3 -m json.tool || echo "API not responding yet"
else
    echo ""
    echo "=== Build failed ==="
    echo "Last 50 lines of build log:"
    tail -50 /tmp/splicegaip-build.log
fi

exit $EXIT_CODE
