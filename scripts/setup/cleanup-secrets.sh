#!/bin/bash

# Script to remove secrets that have been converted to variables
# This ensures clean separation and avoids confusion

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPO="QuangLe1997/media-transcode"

echo -e "${BLUE}=== Cleanup Converted Secrets ===${NC}"
echo

# Check GitHub CLI auth
if ! gh auth status > /dev/null 2>&1; then
    echo -e "${RED}Error: GitHub CLI not authenticated${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

echo -e "${YELLOW}These secrets have been converted to variables and will be removed:${NC}"
echo

# List of secrets that should now be variables
SECRETS_TO_REMOVE=(
    "API_HOST"
    "API_PORT" 
    "DEBUG"
    "PUBSUB_PROJECT_ID"
    "PUBSUB_TASKS_TOPIC"
    "TASKS_SUBSCRIPTION"
    "PUBSUB_RESULTS_TOPIC"
    "PUBSUB_RESULTS_SUBSCRIPTION"
    "PUBSUB_FACE_DETECTION_TASKS_TOPIC"
    "PUBSUB_FACE_DETECTION_RESULTS_TOPIC"
    "PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION"
    "FACE_DETECTION_SUBSCRIPTION"
    "PUBSUB_PUBLISHER_CREDENTIALS_PATH"
    "PUBSUB_SUBSCRIBER_CREDENTIALS_PATH"
    "AWS_BUCKET_NAME"
    "AWS_ENDPOINT_URL"
    "AWS_ENDPOINT_PUBLIC_URL"
    "AWS_BASE_FOLDER"
    "SERVER_HOST"
    "SERVER_USER"
    "DISABLE_PUBSUB"
    "PUBSUB_TASK_SUBSCRIPTION"
    "PUBSUB_MAX_MESSAGES"
)

# Function to remove secret
remove_secret() {
    local name=$1
    
    echo -e "${YELLOW}Removing secret: $name${NC}"
    
    if gh secret delete "$name" --repo="$REPO" 2>/dev/null; then
        echo -e "${GREEN}  ✓ Removed${NC}"
    else
        echo -e "${BLUE}  - Not found (already removed or never existed)${NC}"
    fi
}

# Remove each converted secret
for secret in "${SECRETS_TO_REMOVE[@]}"; do
    remove_secret "$secret"
done

echo
echo -e "${GREEN}=== Cleanup Complete ===${NC}"
echo
echo -e "${BLUE}Remaining secrets (sensitive data only):${NC}"
echo "  - DATABASE_URL"
echo "  - AWS_ACCESS_KEY_ID"
echo "  - AWS_SECRET_ACCESS_KEY"
echo "  - SERVER_SSH_KEY"
echo "  - GOOGLE_CLOUD_KEY_JSON"
echo
echo -e "${BLUE}All public configuration moved to variables:${NC}"
echo "  - API configuration"
echo "  - Topic names"
echo "  - Bucket names"
echo "  - Server info"
echo
echo -e "${YELLOW}View final configuration:${NC}"
echo "  Variables: https://github.com/$REPO/settings/variables/actions"
echo "  Secrets:   https://github.com/$REPO/settings/secrets/actions"
echo
echo -e "${GREEN}✅ Clean separation achieved!${NC}"