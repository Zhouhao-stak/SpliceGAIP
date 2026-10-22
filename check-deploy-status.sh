#!/bin/bash
# SpliceGAIP Deployment Status Checker
# Run this to check if deployment is complete

SERVER="wang_zi_wei@123.255.66.81"
PORT="39145"
PASS="qazedctgb"

echo "=========================================="
echo "🔍 Checking SpliceGAIP Deployment Status"
echo "=========================================="
echo ""

# Function to run SSH commands
ssh_cmd() {
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p $PORT $SERVER "$@" 2>&1
}

# Step 1: Check connectivity
echo "[1/5] Testing server connection..."
if ssh_cmd "echo 'OK'" | grep -q "OK"; then
    echo "✓ Server reachable"
else
    echo "✗ Cannot connect to server"
    echo "   Please check network or try again later"
    exit 1
fi

# Step 2: Check files
echo "[2/5] Checking uploaded files..."
FILE_COUNT=$(ssh_cmd "cd /home/wang_zi_wei/splicegaip && ls -1 | wc -l")
if [ "$FILE_COUNT" -gt 10 ]; then
    echo "✓ Files uploaded ($FILE_COUNT files found)"
else
    echo "⚠️  Few files found ($FILE_COUNT). Upload may be incomplete."
    echo "   Please use WinSCP to upload splicegaip-deploy-package.tar.gz"
fi

# Step 3: Check .env file
echo "[3/5] Checking configuration..."
if ssh_cmd "test -f /home/wang_zi_wei/splicegaip/.env && echo 'YES'"; then
    echo "✓ .env file exists"

    # Check if API key is configured
    API_KEY=$(ssh_cmd "grep DEEPSEEK_API_KEY /home/wang_zi_wei/splicegaip/.env 2>/dev/null | grep -v '^#' | grep -v 'your-' || true")
    if [ -n "$API_KEY" ]; then
        echo "✓ API key configured"
    else
        echo "️  API key not configured or using placeholder"
        echo "   Run: ssh -p $PORT $SERVER"
        echo "   Then: cd ~/splicegaip && nano .env"
        echo "   Add: DEEPSEEK_API_KEY=sk-your-real-key-here"
    fi
else
    echo "✗ .env file missing"
    echo "   Run: ssh -p $PORT $SERVER"
    echo "   Then: cd ~/splicegaip && cp .env.production.example .env"
fi

# Step 4: Check Docker containers
echo "[4/5] Checking Docker containers..."
CONTAINER_STATUS=$(ssh_cmd "cd /home/wang_zi_wei/splicegaip && docker compose ps --format json 2>/dev/null || echo 'NONE'")
if echo "$CONTAINER_STATUS" | grep -q "running"; then
    echo "✓ Containers are running"
    ssh_cmd "cd /home/wang_zi_wei/splicegaip && docker compose ps"
else
    echo "✗ Containers not running"
    echo "   To start: ssh -p $PORT $SERVER"
    echo "   Then: cd ~/splicegaip && docker compose up -d --build"
fi

# Step 5: Check health endpoint
echo "[5/5] Testing API health..."
HEALTH=$(ssh_cmd "curl -s http://localhost:8800/api/health 2>/dev/null || echo 'DOWN'")
if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo "✅ API is healthy!"
    echo "   Response: $HEALTH"
    echo ""
    echo "=========================================="
    echo "🎉 DEPLOYMENT SUCCESSFUL!"
    echo "=========================================="
    echo ""
    echo "Access your application:"
    echo "  API: http://123.255.66.81:8800"
    echo "  UI:  http://123.255.66.81:8501"
    echo ""
    echo "Useful commands:"
    echo "  Logs:     ssh -p $PORT $SERVER 'cd ~/splicegaip && docker compose logs -f'"
    echo "  Restart:  ssh -p $PORT $SERVER 'cd ~/splicegaip && docker compose restart'"
    echo ""
else
    echo "⚠️  API not responding"
    echo "   Service may still be starting..."
    echo "   Check logs: ssh -p $PORT $SERVER 'cd ~/splicegaip && docker compose logs -f'"
fi

echo ""
echo "Run this script again anytime to check status!"
