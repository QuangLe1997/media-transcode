#!/bin/bash

# Manual deployment script when GitHub Actions webhook fails
# This simulates what the webhook would do

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'


SERVER="192.168.0.234"
SSH_PORT="6789"
USER="skl"

echo -e "${BLUE}=== Manual Deployment to $SERVER ===${NC}"
echo

echo -e "${YELLOW}📡 Testing webhook server health...${NC}"
if curl -f -s "http://$SERVER:3001/health" > /dev/null; then
    echo -e "${GREEN}✅ Webhook server is healthy${NC}"
    curl -s "http://$SERVER:3001/health" | jq .
else
    echo -e "${RED}❌ Webhook server not accessible${NC}"
    echo "This is expected if AWS Security Group doesn't allow port 3001 from your IP"
fi

echo

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/deployment/.env"

echo -e "${BLUE}📂 Project root: $PROJECT_ROOT${NC}"
echo -e "${BLUE}📄 Looking for: $ENV_FILE${NC}"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ $ENV_FILE file not found!${NC}"
    echo "Please create deployment/.env file with your environment variables"
    echo "You can copy from: $PROJECT_ROOT/deployment/.env.example"
    exit 1
fi

echo -e "${YELLOW}📄 Loading environment variables from $ENV_FILE...${NC}"

# Read .env file and export variables
set -a  # automatically export all variables
source "$ENV_FILE"
set +a

# Upload key.json if it exists
KEY_JSON_PATH="$PROJECT_ROOT/src/transcode_service/key.json"
if [ -f "$KEY_JSON_PATH" ]; then
    echo -e "${BLUE}📤 Uploading Google Cloud key.json...${NC}"
    ssh -p $SSH_PORT "$USER@$SERVER" "sudo mkdir -p /quang/quang/dev-media-transcode/src/transcode_service && sudo chown -R $USER:$USER /quang/quang/dev-media-transcode && rm -rf /quang/quang/dev-media-transcode/src/transcode_service/key.json"
    scp -P $SSH_PORT "$KEY_JSON_PATH" "$USER@$SERVER:/quang/quang/dev-media-transcode/src/transcode_service/"
    echo -e "${GREEN}✅ key.json uploaded${NC}"
else
    echo -e "${YELLOW}⚠️  key.json not found locally, PubSub features may not work${NC}"
fi

echo -e "${YELLOW}🚀 Triggering deployment via SSH...${NC}"

ssh -p $SSH_PORT $USER@$SERVER "
set -e

echo '🌐 Checking network connectivity...'
if ! ping -c 1 8.8.8.8 &> /dev/null; then
    echo '❌ No internet connection detected'
    exit 1
fi

echo '🔍 Testing GitHub connectivity...'
if ! nc -zv github.com 443 2>&1 | grep -q 'succeeded'; then
    echo '⚠️  Cannot connect to GitHub. Trying with DNS...'
    echo '8.8.8.8 google-public-dns-a.google.com' | sudo tee -a /etc/hosts > /dev/null
    echo '140.82.112.3 github.com' | sudo tee -a /etc/hosts > /dev/null
fi

echo '📂 Checking project directory...'
if [ ! -d /quang/quang/dev-media-transcode ]; then
    echo '📥 Project not found. Creating directory and cloning repository...'
    sudo mkdir -p /quang/quang
    sudo chown $USER:$USER /quang/quang
    cd /quang/quang
    
    # Test internet connectivity for git clone
    if ping -c 1 github.com &> /dev/null; then
        echo '🌐 Cloning from GitHub...'
        git clone https://github.com/QuangLe1997/media-transcode.git dev-media-transcode
    else
        echo '❌ Cannot reach GitHub for cloning. Server needs internet access or manual file transfer.'
        exit 1
    fi
    cd /quang/quang/dev-media-transcode
elif [ ! -d /quang/quang/dev-media-transcode/.git ]; then
    echo '⚠️  Directory exists but not a git repository. Re-cloning...'
    sudo rm -rf /quang/quang/dev-media-transcode
    sudo chown $USER:$USER /quang/quang
    cd /quang/quang
    
    # Test internet connectivity for git clone
    if ping -c 1 github.com &> /dev/null; then
        echo '🌐 Cloning from GitHub...'
        git clone https://github.com/QuangLe1997/media-transcode.git dev-media-transcode
    else
        echo '❌ Cannot reach GitHub for cloning. Server needs internet access or manual file transfer.'
        exit 1
    fi
    cd /quang/quang/dev-media-transcode
else
    echo '📂 Navigating to existing repository...'
    cd /quang/quang/dev-media-transcode
    
    # Check if we can pull (git repository exists and has remote)
    if [ -d .git ] && git remote get-url origin &> /dev/null; then
        echo '📥 Pulling latest code...'
        if ping -c 1 github.com &> /dev/null; then
            git pull origin master
        else
            echo '⚠️  Cannot reach GitHub for pulling. Using existing code.'
        fi
    else
        echo '⚠️  Git repository corrupted or no remote configured.'
        echo '🔧 Re-initializing git repository...'
        rm -rf .git
        git init
        if ping -c 1 github.com &> /dev/null; then
            git remote add origin https://github.com/QuangLe1997/media-transcode.git
            git fetch origin
            git checkout -b master origin/master
        else
            echo '⚠️  Cannot reach GitHub. Using existing files without git.'
        fi
    fi
fi

echo '📝 Creating .env file...'
cd deployment
cat > .env << 'EOF'
# Auto-generated environment file from manual deployment
# Generated at: \$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Database Configuration (using Docker container name)
DATABASE_URL=postgresql+asyncpg://transcode_user:transcode_pass@postgres:5432/transcode_db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8087
DEBUG=$DEBUG

# AWS S3 Configuration  
AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
AWS_BUCKET_NAME=$AWS_BUCKET_NAME
AWS_ENDPOINT_URL=$AWS_ENDPOINT_URL
AWS_ENDPOINT_PUBLIC_URL=$AWS_ENDPOINT_PUBLIC_URL
AWS_BASE_FOLDER=$AWS_BASE_FOLDER

# Google Cloud PubSub Configuration
PUBSUB_PROJECT_ID=$PUBSUB_PROJECT_ID
PUBSUB_TASKS_TOPIC=$PUBSUB_TASKS_TOPIC
TASKS_SUBSCRIPTION=$TASKS_SUBSCRIPTION
PUBSUB_RESULTS_TOPIC=$PUBSUB_RESULTS_TOPIC
PUBSUB_RESULTS_SUBSCRIPTION=$PUBSUB_RESULTS_SUBSCRIPTION

#TRANSCODE PUBSUB
PUBSUB_TRANSCODE_TASK_TOPIC=$PUBSUB_TRANSCODE_TASK_TOPIC
TRANSCODE_TASK_SUBSCRIPTION=$TRANSCODE_TASK_SUBSCRIPTION

# Face Detection PubSub
PUBSUB_FACE_DETECTION_TASKS_TOPIC=$PUBSUB_FACE_DETECTION_TASKS_TOPIC
PUBSUB_FACE_DETECTION_RESULTS_TOPIC=$PUBSUB_FACE_DETECTION_RESULTS_TOPIC
PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION=$PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION
FACE_DETECTION_SUBSCRIPTION=$FACE_DETECTION_SUBSCRIPTION

# Credentials paths (Docker container paths)
PUBSUB_PUBLISHER_CREDENTIALS_PATH=/app/key.json
PUBSUB_SUBSCRIBER_CREDENTIALS_PATH=/app/key.json

# Optional flags
DISABLE_PUBSUB=\${DISABLE_PUBSUB:-false}
EOF

echo '✅ Environment file created'

echo '🔑 Checking Google Cloud key file...'
if [ -f '../src/transcode_service/key.json' ]; then
    echo '✅ Google Cloud key file exists'
else
    echo '⚠️  Google Cloud key file not found, services may not work fully'
fi

echo '🤖 Face detection models will be auto-downloaded on first use'

echo '🛑 Stopping existing containers...'
docker-compose down || echo 'No containers to stop'

echo '🏗️  Building and starting containers...'
docker-compose pull
docker-compose build
docker-compose up

echo '⏳ Waiting for services to initialize...'
sleep 30

echo '🔍 Checking container status...'
docker-compose ps

echo '🧹 Cleaning up old images...'
docker image prune -f || true

echo '🎉 Deployment completed!'
echo '🌐 Services should be available at:'
echo '  - API: http://$SERVER:8087'
echo '  - Frontend: http://$SERVER:3000'
echo '  - Database: postgresql://$SERVER:5433'
"

echo
echo -e "${BLUE}=== Post-deployment Health Checks ===${NC}"

echo -e "${YELLOW}⏳ Waiting 30 seconds for services to be ready...${NC}"
sleep 30

echo -e "${YELLOW}🔍 Checking API health...${NC}"
if curl -f -s "http://$SERVER:8087/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy!${NC}"
else
    echo -e "${YELLOW}⚠️  API not ready yet, may need more time${NC}"
fi

echo -e "${YELLOW}🔍 Checking frontend...${NC}"
if curl -f -s "http://$SERVER:3000" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is accessible!${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend not ready yet, may need more time${NC}"
fi

echo
echo -e "${GREEN}=== Manual Deployment Complete! ===${NC}"
echo
echo -e "${BLUE}📊 Service URLs:${NC}"
echo "  🔗 API: http://$SERVER:8087"
echo "  🔗 Frontend: http://$SERVER:3000" 
echo "  🔗 Database: postgresql://$SERVER:5433"
echo "  🔗 Webhook: http://$SERVER:3001/health"
echo
echo -e "${YELLOW}💡 To fix GitHub Actions webhook:${NC}"
echo "  1. Go to AWS EC2 Console"
echo "  2. Find Security Group for this instance"
echo "  3. Add inbound rule: Port 3001, Source: 0.0.0.0/0"
echo "  4. Then GitHub Actions webhook deployment will work"