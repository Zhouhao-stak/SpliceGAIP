#!/bin/bash
# SpliceGAIP Deployment Script for 123.255.66.81:39145
# User: wang_zi_wei
# No root required - uses existing Docker installation

set -e

# Server Configuration
SERVER="wang_zi_wei@123.255.66.81"
PORT="39145"
REMOTE_DIR="/home/wang_zi_wei/splicegaip"
API_PORT="8800"
UI_PORT="8501"

echo "=========================================="
echo "🚀 SpliceGAIP Deployment to 123.255.66.81"
echo "=========================================="
echo ""

# SSH helper function
ssh_cmd() {
    sshpass -p 'qazedctgb' ssh -o StrictHostKeyChecking=no -p $PORT $SERVER "$@"
}

# Step 1: Verify server connectivity
echo "[1/7] Verifying server connection..."
if ssh_cmd "echo 'Connected'" > /dev/null 2>&1; then
    echo "✓ Server reachable"
else
    echo "✗ Cannot connect to server"
    exit 1
fi

# Step 2: Check Docker
echo "[2/7] Checking Docker..."
if ssh_cmd "docker --version" > /dev/null 2>&1; then
    DOCKER_VERSION=$(ssh_cmd "docker --version" | cut -d' ' -f3)
    echo "✓ Docker $DOCKER_VERSION available"
else
    echo "✗ Docker not found"
    exit 1
fi

# Step 3: Check ports
echo "[3/7] Checking port availability..."
OCCUPIED_PORTS=$(ssh_cmd 'netstat -tuln 2>/dev/null | grep -E ":(8800|8501)" || true')
if [ -n "$OCCUPIED_PORTS" ]; then
    echo "⚠️  Ports $API_PORT or $UI_PORT are in use:"
    echo "$OCCUPIED_PORTS"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please change ports in docker-compose.yml first"
        exit 1
    fi
else
    echo "✓ Ports $API_PORT and $UI_PORT are free"
fi

# Step 4: Create remote directory
echo "[4/7] Setting up remote directory..."
ssh_cmd "mkdir -p $REMOTE_DIR"
echo "✓ Directory created: $REMOTE_DIR"

# Step 5: Sync files
echo "[5/7] Uploading files (this may take a moment)..."
rsync -avz --delete \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='node_modules' \
    --exclude='htmlcov' \
    --exclude='dist' \
    --exclude='build' \
    -e "sshpass -p 'qazedctgb' ssh -o StrictHostKeyChecking=no -p $PORT" \
    ./ "$SERVER:$REMOTE_DIR/"

echo "✓ Files uploaded"

# Step 6: Configure environment
echo "[6/7] Configuring environment..."
ssh_cmd "cd $REMOTE_DIR && \
    if [ ! -f .env ]; then
        echo 'Creating .env from template...'
        cp .env.production.example .env
        echo ''
        echo '⚠️  IMPORTANT: Please edit .env and add your API keys!'
        echo '   Run: vim $REMOTE_DIR/.env'
        echo ''
    else
        echo '.env file already exists'
    fi"

# Step 7: Deploy
echo "[7/7] Deploying SpliceGAIP..."
ssh_cmd "cd $REMOTE_DIR && \
    echo 'Pulling latest images...' && \
    docker compose pull && \
    echo 'Building and starting containers...' && \
    docker compose up -d --build && \
    echo '' && \
    echo 'Container status:' && \
    docker compose ps && \
    echo '' && \
    echo 'Waiting for service to start...' && \
    sleep 15 && \
    echo 'Testing health endpoint...' && \
    curl -s http://localhost:$API_PORT/api/health || echo 'Service is starting, check logs below'"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Access your application:"
echo "  🌐 API:  http://123.255.66.81:$API_PORT"
echo "   UI:   http://123.255.66.81:$UI_PORT"
echo ""
echo "Useful commands:"
echo "  View logs:     ssh -p $PORT $SERVER 'cd $REMOTE_DIR && docker compose logs -f'"
echo "  Restart:       ssh -p $PORT $SERVER 'cd $REMOTE_DIR && docker compose restart'"
echo "  Stop:          ssh -p $PORT $SERVER 'cd $REMOTE_DIR && docker compose down'"
echo "  Update config: ssh -p $PORT $SERVER 'vim $REMOTE_DIR/.env'"
echo ""
echo "Next steps:"
echo "  1. Edit .env file and add your DeepSeek API key"
echo "  2. Test the API: curl http://123.255.66.81:$API_PORT/api/health"
echo "  3. Access the web UI in your browser"
echo ""

# Optional: Show logs
read -p "Show live logs? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sshpass -p 'qazedctgb' ssh -o StrictHostKeyChecking=no -p $PORT $SERVER "cd $REMOTE_DIR && docker compose logs -f"
fi
