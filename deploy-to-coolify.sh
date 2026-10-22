#!/bin/bash
# SpliceGAIP Quick Deploy Script for Coolify
# Usage: ./deploy-to-coolify.sh [server-ip]

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 SpliceGAIP Coolify Deployment Helper${NC}"
echo "=========================================="

# Check if server IP is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <server-ip>${NC}"
    echo ""
    echo "Example: $0 192.168.1.100"
    exit 1
fi

SERVER_IP="$1"
COOLIFY_URL="https://${SERVER_IP}:8000"

echo -e "${GREEN}Server:${NC} ${SERVER_IP}"
echo -e "${GREEN}Coolify URL:${NC} ${COOLIFY_URL}"
echo ""

# Step 1: Verify connectivity
echo -e "${YELLOW}[1/5] Checking server connectivity...${NC}"
if ping -c 1 -W 2 "${SERVER_IP}" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server is reachable${NC}"
else
    echo -e "${RED}✗ Cannot reach server. Please check the IP address.${NC}"
    exit 1
fi

# Step 2: Check if Coolify is installed
echo -e "${YELLOW}[2/5] Checking if Coolify is installed...${NC}"
if curl -k -s -o /dev/null -w "%{http_code}" "${COOLIFY_URL}" | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Coolify is running${NC}"
else
    echo -e "${RED}✗ Coolify is not accessible at ${COOLIFY_URL}${NC}"
    echo ""
    echo "Please install Coolify first:"
    echo "  ssh root@${SERVER_IP}"
    echo "  curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash"
    exit 1
fi

# Step 3: Prepare deployment files
echo -e "${YELLOW}[3/5] Preparing deployment files...${NC}"

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}Creating .env.production from template...${NC}"
    cp .env.production.example .env.production
    echo -e "${RED}⚠️  Please edit .env.production and add your API keys!${NC}"
    echo ""
    read -p "Press Enter after you've configured .env.production..."
fi

# Verify required files exist
REQUIRED_FILES=("Dockerfile" "docker-compose.coolify.yml" "requirements.txt")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗ Missing required file: ${file}${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ All deployment files ready${NC}"

# Step 4: Git status check
echo -e "${YELLOW}[4/5] Checking Git status...${NC}"
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    CURRENT_BRANCH=$(git branch --show-current)
    echo -e "${GREEN}✓ Current branch: ${CURRENT_BRANCH}${NC}"

    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}⚠️  You have uncommitted changes${NC}"
        read -p "Do you want to commit them? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add .
            git commit -m "Deploy to Coolify - $(date '+%Y-%m-%d %H:%M:%S')"
            echo -e "${GREEN}✓ Changes committed${NC}"
        fi
    fi
else
    echo -e "${RED}✗ Not a Git repository. Coolify requires Git integration.${NC}"
    exit 1
fi

# Step 5: Push to trigger deployment
echo -e "${YELLOW}[5/5] Ready to deploy!${NC}"
echo ""
echo "Next steps:"
echo "1. Open Coolify dashboard: ${COOLIFY_URL}"
echo "2. Login with your credentials"
echo "3. Create a new project or select existing one"
echo "4. Connect your GitHub repository"
echo "5. Configure environment variables (see .env.production)"
echo "6. Click 'Deploy'"
echo ""
echo "OR use automatic deployment:"
echo "  git push origin ${CURRENT_BRANCH}"
echo "  (Coolify will auto-deploy on push)"
echo ""

read -p "Do you want to open Coolify in browser now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Open browser based on OS
    case "$(uname -s)" in
        Darwin)  open "${COOLIFY_URL}" ;;
        Linux)   xdg-open "${COOLIFY_URL}" 2>/dev/null || sensible-browser "${COOLIFY_URL}" 2>/dev/null ;;
        MINGW*)  start "${COOLIFY_URL}" ;;
        *)       echo "Please manually open: ${COOLIFY_URL}" ;;
    esac
fi

echo ""
echo -e "${GREEN}✅ Deployment preparation complete!${NC}"
echo ""
echo "For detailed instructions, see: DEPLOY_COOLIFY.md"
echo ""
