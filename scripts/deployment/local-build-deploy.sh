#!/bin/bash

# Local build and deploy script - builds .env locally then deploys
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVER="54.248.140.63"
USER="quanglv"

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/deployment/.env"

echo -e "${BLUE}=== Local Build & Deploy to $SERVER ===${NC}"
echo

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ $ENV_FILE file not found!${NC}"
    echo "Please create deployment/.env file with your environment variables"
    exit 1
fi

echo -e "${YELLOW}📄 Loading environment variables from $ENV_FILE...${NC}"

# Read .env file and export variables
set -a
source "$ENV_FILE"
set +a

echo -e "${YELLOW}📦 Creating deployment package...${NC}"

# Check if key.json exists
KEY_JSON_PATH="$PROJECT_ROOT/src/transcode_service/key.json"
KEY_JSON_CONTENT=""
if [ -f "$KEY_JSON_PATH" ]; then
    echo -e "${GREEN}✅ Found Google Cloud key.json${NC}"
    KEY_JSON_CONTENT=$(cat "$KEY_JSON_PATH")
else
    echo -e "${YELLOW}⚠️  key.json not found, PubSub will be disabled${NC}"
    DISABLE_PUBSUB=true
fi

# Create temp deployment script with actual values
TEMP_SCRIPT="/tmp/deploy-$(date +%s).sh"

cat > "$TEMP_SCRIPT" << EOF
#!/bin/bash
set -e

echo '📂 Navigating to project directory...'
cd ~/media-transcode

echo '📥 Pulling latest code...'
git pull origin master

echo '📝 Creating .env file with actual values...'
cd deployment
cat > .env << 'ENVEOF'
# Auto-generated environment file from local build
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

# Face Detection PubSub
PUBSUB_FACE_DETECTION_TASKS_TOPIC=$PUBSUB_FACE_DETECTION_TASKS_TOPIC
PUBSUB_FACE_DETECTION_RESULTS_TOPIC=$PUBSUB_FACE_DETECTION_RESULTS_TOPIC
PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION=$PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION
FACE_DETECTION_SUBSCRIPTION=$FACE_DETECTION_SUBSCRIPTION

# Credentials paths (Docker container paths)
PUBSUB_PUBLISHER_CREDENTIALS_PATH=/app/key.json
PUBSUB_SUBSCRIBER_CREDENTIALS_PATH=/app/key.json

# Optional flags (disable PubSub if credentials issues)
DISABLE_PUBSUB=$DISABLE_PUBSUB
ENVEOF

echo '✅ Environment file created'

echo '🔑 Checking for Google Cloud key.json file...'
if [ -f '../src/transcode_service/key.json' ]; then
echo '✅ Google Cloud key.json exists'
else
echo '⚠️  Google Cloud key.json not found, PubSub features may not work'
fi

echo '🛑 Stopping existing containers...'
docker-compose down || echo 'No containers to stop'

echo '🏗️  Building and starting containers...'
docker-compose pull || true
docker-compose build --no-cache
docker-compose up -d

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
EOF

chmod +x "$TEMP_SCRIPT"

echo -e "${YELLOW}🚀 Uploading deployment files...${NC}"

# Upload key.json if it exists
if [ -f "$KEY_JSON_PATH" ]; then
    echo -e "${BLUE}📤 Uploading Google Cloud key.json...${NC}"
    ssh "$USER@$SERVER" "mkdir -p ~/media-transcode/src/transcode_service"
    scp "$KEY_JSON_PATH" "$USER@$SERVER:~/media-transcode/src/transcode_service/key.json"
    echo -e "${GREEN}✅ key.json uploaded${NC}"
fi

# Copy script to server and execute
echo -e "${BLUE}📤 Uploading and executing deployment script...${NC}"
scp "$TEMP_SCRIPT" "$USER@$SERVER:/tmp/deploy.sh"
ssh "$USER@$SERVER" "chmod +x /tmp/deploy.sh && /tmp/deploy.sh && rm /tmp/deploy.sh"

# Clean up local temp script
rm "$TEMP_SCRIPT"

echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo
echo -e "${BLUE}📊 Service URLs:${NC}"
echo "  🔗 API: http://$SERVER:8087"
echo "  🔗 Frontend: http://$SERVER:3000"
echo "  🔗 Database: postgresql://$SERVER:5433"