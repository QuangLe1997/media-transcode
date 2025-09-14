#!/bin/bash

# Manual deployment script when GitHub Actions webhook fails
# This simulates what the webhook would do

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVER="54.248.140.63"
USER="quanglv"

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
echo -e "${YELLOW}🚀 Triggering deployment via SSH...${NC}"

ssh $USER@$SERVER "
set -e

echo '📂 Navigating to project directory...'
cd ~/media-transcode

echo '📥 Pulling latest code...'
git pull origin master

echo '📝 Creating .env file...'
cd deployment
cat > .env << 'EOF'
# Auto-generated environment file from manual deployment
# Generated at: $(date -u +%Y-%m-%dT%H:%M:%SZ)

DATABASE_URL=postgresql+asyncpg://transcode_user:transcode_pass@192.168.0.234:5433/transcode_db
API_HOST=0.0.0.0
API_PORT=8087
DEBUG=true
AWS_ACCESS_KEY_ID=lohQviNWOolAohjnVxUx
AWS_SECRET_ACCESS_KEY=9fkNUpprohih4eSemGw5HwZQbMKelqGPbb7DyMBh
AWS_BUCKET_NAME=dev-facefusion-media
AWS_ENDPOINT_URL=https://storage.skylink.vn
AWS_ENDPOINT_PUBLIC_URL=https://static-vncdn.skylinklabs.ai
AWS_BASE_FOLDER=transcode-service
PUBSUB_PROJECT_ID=kiwi2-454610
PUBSUB_TASKS_TOPIC=transcode-utils-tasks
TASKS_SUBSCRIPTION=transcode-utils-tasks-sub
PUBSUB_RESULTS_TOPIC=transcode-utils-results
PUBSUB_RESULTS_SUBSCRIPTION=transcode-utils-results-sub
PUBSUB_FACE_DETECTION_TASKS_TOPIC=face-detection-worker-tasks
PUBSUB_FACE_DETECTION_RESULTS_TOPIC=face-detection-worker-results
PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION=face-detection-worker-results-sub
FACE_DETECTION_SUBSCRIPTION=face-detection-worker-tasks-sub
PUBSUB_PUBLISHER_CREDENTIALS_PATH=/app/key.json
PUBSUB_SUBSCRIBER_CREDENTIALS_PATH=/app/key.json
EOF

echo '✅ Environment file created'

echo '🔑 Checking Google Cloud key file...'
if [ -f '../src/transcode_service/key.json' ]; then
    echo '✅ Google Cloud key file exists'
else
    echo '⚠️  Google Cloud key file not found, services may not work fully'
fi

echo '🛑 Stopping existing containers...'
docker-compose down || echo 'No containers to stop'

echo '🏗️  Building and starting containers...'
docker-compose pull
docker-compose build
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