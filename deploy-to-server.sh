#!/bin/bash
# SpliceGAIP Server Deployment Script (No Root Required)
# Prerequisites: Docker installed on server, user in docker group
# Usage: ./deploy-to-server.sh [user@server] [remote_dir]

set -e

# Configuration
SERVER="${1:-user@your-server.com}"
REMOTE_DIR="${2:-/home/$USER/splicegaip}"
LOCAL_PORT="8800"
REMOTE_PORT="8800"

echo " SpliceGAIP Server Deployment"
echo "================================"
echo "Server: $SERVER"
echo "Remote Dir: $REMOTE_DIR"
echo ""

# Step 1: Check connectivity
echo "[1/6] Checking server connectivity..."
if ssh "$SERVER" "echo 'Connection OK'" > /dev/null 2>&1; then
    echo "✓ Server reachable"
else
    echo "✗ Cannot connect to server"
    exit 1
fi

# Step 2: Check Docker availability
echo "[2/6] Checking Docker on server..."
if ssh "$SERVER" "docker --version" > /dev/null 2>&1; then
    echo "✓ Docker installed"
else
    echo "✗ Docker not found on server"
    echo "Please ask your admin to install Docker:"
    echo "  sudo apt update && sudo apt install docker.io docker-compose"
    exit 1
fi

# Step 3: Check docker group membership
echo "[3/6] Checking Docker permissions..."
if ssh "$SERVER" "groups | grep -q docker"; then
    echo "✓ User has Docker permissions"
else
    echo "⚠️  User not in docker group"
    echo "Ask admin to run: sudo usermod -aG docker $USER"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 4: Create remote directory
echo "[4/6] Setting up remote directory..."
ssh "$SERVER" "mkdir -p $REMOTE_DIR"

# Step 5: Sync files to server
echo "[5/6] Uploading files to server..."
rsync -avz --delete \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='node_modules' \
    ./ "$SERVER:$REMOTE_DIR/"

echo "✓ Files uploaded"

# Step 6: Deploy on server
echo "[6/6] Deploying on server..."
ssh "$SERVER" "cd $REMOTE_DIR && \
    # Create .env file if not exists
    if [ ! -f .env ]; then
        echo 'Creating .env from template...'
        cp .env.production.example .env
        echo '⚠️  Please edit .env and add your API keys!'
    fi && \
    # Pull latest images
    docker compose pull && \
    # Build and start containers
    docker compose up -d --build && \
    # Show status
    docker compose ps && \
    # Wait for health check
    echo 'Waiting for service to be ready...' && \
    sleep 10 && \
    # Test health endpoint
    curl -s http://localhost:$REMOTE_PORT/api/health || echo 'Service starting, check logs with: docker compose logs -f'
"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Access your application:"
echo "  API:  http://$SERVER:$REMOTE_PORT"
echo "  Logs: ssh $SERVER 'cd $REMOTE_DIR && docker compose logs -f'"
echo ""
echo "To update in the future, just run this script again!"
echo ""

# Optional: Show logs
read -p "Show live logs? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ssh "$SERVER" "cd $REMOTE_DIR && docker compose logs -f"
fi
