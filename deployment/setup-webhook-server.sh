#!/bin/bash

# Setup webhook deployment server on the target server
# Run this script once on the deployment server

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Setting up Webhook Deployment Server ===${NC}"
echo

# Check if running as correct user
if [ "$USER" != "quanglv" ]; then
    echo -e "${RED}❌ This script should be run as user 'quanglv'${NC}"
    echo "Current user: $USER"
    exit 1
fi

PROJECT_DIR="/home/quanglv/media-transcode"
DEPLOYMENT_DIR="$PROJECT_DIR/deployment"

echo -e "${YELLOW}📂 Project directory: $PROJECT_DIR${NC}"

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Project directory not found: $PROJECT_DIR${NC}"
    echo "Please ensure the project is cloned to the correct location"
    exit 1
fi

cd "$DEPLOYMENT_DIR"

# Install Node.js if not present
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}📦 Installing Node.js...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo -e "${GREEN}✅ Node.js installed${NC}"
else
    echo -e "${GREEN}✅ Node.js already installed: $(node --version)${NC}"
fi

# Install required npm packages
echo -e "${YELLOW}📦 Installing npm dependencies...${NC}"
if [ ! -f "package.json" ]; then
    cat > package.json << 'EOF'
{
  "name": "media-transcode-webhook-server",
  "version": "1.0.0",
  "description": "Webhook server for media transcode deployment",
  "main": "webhook-server.js",
  "scripts": {
    "start": "node webhook-server.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "keywords": ["webhook", "deployment", "docker"],
  "author": "Media Transcode Team",
  "license": "MIT"
}
EOF
fi

npm install
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Generate webhook secret if not exists
WEBHOOK_SECRET_FILE="$DEPLOYMENT_DIR/.webhook-secret"
if [ ! -f "$WEBHOOK_SECRET_FILE" ]; then
    echo -e "${YELLOW}🔑 Generating webhook secret...${NC}"
    openssl rand -hex 32 > "$WEBHOOK_SECRET_FILE"
    chmod 600 "$WEBHOOK_SECRET_FILE"
    echo -e "${GREEN}✅ Webhook secret generated${NC}"
else
    echo -e "${GREEN}✅ Webhook secret already exists${NC}"
fi

WEBHOOK_SECRET=$(cat "$WEBHOOK_SECRET_FILE")
echo -e "${BLUE}🔑 Webhook secret: $WEBHOOK_SECRET${NC}"

# Update systemd service file with actual secret
echo -e "${YELLOW}⚙️  Updating systemd service file...${NC}"
sed -i "s/your-secure-webhook-secret-here/$WEBHOOK_SECRET/g" webhook-deploy.service

# Install systemd service
echo -e "${YELLOW}🔧 Installing systemd service...${NC}"
sudo cp webhook-deploy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webhook-deploy
echo -e "${GREEN}✅ Systemd service installed${NC}"

# Start the webhook server
echo -e "${YELLOW}🚀 Starting webhook deployment server...${NC}"
sudo systemctl restart webhook-deploy
sleep 3

# Check service status
if sudo systemctl is-active --quiet webhook-deploy; then
    echo -e "${GREEN}✅ Webhook server is running${NC}"
    sudo systemctl status webhook-deploy --no-pager -l
else
    echo -e "${RED}❌ Webhook server failed to start${NC}"
    echo "Check logs with: sudo journalctl -u webhook-deploy -f"
    exit 1
fi

# Test the webhook server
echo -e "${YELLOW}🧪 Testing webhook server...${NC}"
if curl -f -s http://localhost:3001/health > /dev/null; then
    echo -e "${GREEN}✅ Webhook server is responding${NC}"
    curl -s http://localhost:3001/health | jq .
else
    echo -e "${RED}❌ Webhook server is not responding${NC}"
    echo "Check logs with: sudo journalctl -u webhook-deploy -f"
    exit 1
fi

# Configure firewall if ufw is active
if sudo ufw status | grep -q "Status: active"; then
    echo -e "${YELLOW}🔥 Configuring firewall...${NC}"
    sudo ufw allow 3001/tcp comment "Webhook deployment server"
    echo -e "${GREEN}✅ Firewall configured${NC}"
fi

echo
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo
echo -e "${BLUE}📊 Service Information:${NC}"
echo "  - Service: webhook-deploy"
echo "  - Port: 3001"
echo "  - Log file: $DEPLOYMENT_DIR/webhook-deploy.log"
echo "  - Webhook URL: http://$(curl -s ifconfig.me):3001/deploy"
echo "  - Health check: http://$(curl -s ifconfig.me):3001/health"
echo
echo -e "${BLUE}🔑 Add this secret to GitHub Secrets as WEBHOOK_SECRET:${NC}"
echo "$WEBHOOK_SECRET"
echo
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "  - Check status: sudo systemctl status webhook-deploy"
echo "  - View logs: sudo journalctl -u webhook-deploy -f"
echo "  - Restart: sudo systemctl restart webhook-deploy"
echo "  - Stop: sudo systemctl stop webhook-deploy"
echo
echo -e "${GREEN}🎉 Ready for webhook deployments!${NC}"