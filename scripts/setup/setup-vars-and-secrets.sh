#!/bin/bash

# Script to properly categorize GitHub Variables vs Secrets
# Variables: Non-sensitive configuration that can be public
# Secrets: Sensitive data that should be encrypted

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPO="QuangLe1997/media-transcode"
ENV_FILE="deployment/.env"

echo -e "${BLUE}=== GitHub Variables vs Secrets Setup ===${NC}"
echo

# Check GitHub CLI auth
if ! gh auth status > /dev/null 2>&1; then
    echo -e "${RED}Error: GitHub CLI not authenticated${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

# Function to add variable (non-sensitive)
add_variable() {
    local name=$1
    local value=$2
    local description=$3
    
    if [ -z "$value" ] || [ "$value" == "" ]; then
        echo -e "${YELLOW}  Skipping $name (empty value)${NC}"
        return
    fi
    
    echo -e "${BLUE}Adding variable: $name${NC}"
    echo -e "  ${description}"
    echo "$value" | gh variable set "$name" --repo="$REPO"
    echo -e "${GREEN}  ✓ Added as variable${NC}"
    echo
}

# Function to add secret (sensitive)
add_secret() {
    local name=$1
    local value=$2
    local description=$3
    
    if [ -z "$value" ] || [ "$value" == "" ]; then
        echo -e "${YELLOW}  Skipping $name (empty value)${NC}"
        return
    fi
    
    echo -e "${RED}Adding secret: $name${NC}"
    echo -e "  ${description}"
    echo "$value" | gh secret set "$name" --repo="$REPO"
    echo -e "${GREEN}  ✓ Added as secret${NC}"
    echo
}

# === Variables (Non-sensitive configuration) ===
echo -e "${BLUE}=== Setting up Variables (Non-sensitive) ===${NC}"

add_variable "API_HOST" "0.0.0.0" "API host binding"
add_variable "API_PORT" "8087" "API port number"
add_variable "DEBUG" "true" "Debug mode flag"

# Pub/Sub Topic Names (not sensitive)
add_variable "PUBSUB_TASKS_TOPIC" "transcode-utils-tasks" "Transcode tasks topic"
add_variable "TASKS_SUBSCRIPTION" "transcode-utils-tasks-sub" "Tasks subscription name"
add_variable "PUBSUB_RESULTS_TOPIC" "transcode-utils-results" "Results topic"
add_variable "PUBSUB_RESULTS_SUBSCRIPTION" "transcode-utils-results-sub" "Results subscription"

# Face Detection Topics
add_variable "PUBSUB_FACE_DETECTION_TASKS_TOPIC" "face-detection-worker-tasks" "Face detection tasks topic"
add_variable "PUBSUB_FACE_DETECTION_RESULTS_TOPIC" "face-detection-worker-results" "Face detection results topic"
add_variable "PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION" "face-detection-worker-results-sub" "Face detection results sub"
add_variable "FACE_DETECTION_SUBSCRIPTION" "face-detection-worker-tasks-sub" "Face detection subscription"

# Paths (not sensitive)
add_variable "PUBSUB_PUBLISHER_CREDENTIALS_PATH" "/app/key.json" "GCP credentials path in container"
add_variable "PUBSUB_SUBSCRIBER_CREDENTIALS_PATH" "/app/key.json" "GCP subscriber credentials path"

# AWS Bucket and Endpoint URLs (not sensitive if public)
add_variable "AWS_BUCKET_NAME" "dev-facefusion-media" "S3 bucket name"
add_variable "AWS_ENDPOINT_URL" "https://storage.skylink.vn" "S3 endpoint URL"
add_variable "AWS_ENDPOINT_PUBLIC_URL" "https://static-vncdn.skylinklabs.ai" "Public S3 endpoint"
add_variable "AWS_BASE_FOLDER" "transcode-service" "S3 base folder"

# GCP Project (not sensitive)
add_variable "PUBSUB_PROJECT_ID" "kiwi2-454610" "GCP Project ID"

# Server info (not sensitive for deployment)
add_variable "SERVER_HOST" "54.248.140.63" "Deployment server IP"
add_variable "SERVER_USER" "quanglv" "SSH username"

# === Secrets (Sensitive data) ===
echo -e "${RED}=== Setting up Secrets (Sensitive) ===${NC}"

# Database credentials
add_secret "DATABASE_URL" "postgresql+asyncpg://transcode_user:transcode_pass@192.168.0.234:5433/transcode_db" "Database connection string"

# AWS credentials
add_secret "AWS_ACCESS_KEY_ID" "lohQviNWOolAohjnVxUx" "AWS access key"
add_secret "AWS_SECRET_ACCESS_KEY" "9fkNUpprohih4eSemGw5HwZQbMKelqGPbb7DyMBh" "AWS secret key"

# SSH Key
SSH_KEY="$HOME/.ssh/github_actions_deploy"
if [ -f "$SSH_KEY" ]; then
    echo -e "${RED}Adding SSH private key${NC}"
    cat "$SSH_KEY" | gh secret set "SERVER_SSH_KEY" --repo="$REPO"
    echo -e "${GREEN}  ✓ Added SERVER_SSH_KEY${NC}"
fi

# Google Cloud Service Account Key
KEY_JSON_PATH="src/transcode_service/key.json"
if [ -f "$KEY_JSON_PATH" ]; then
    echo -e "${RED}Adding Google Cloud service account key${NC}"
    cat "$KEY_JSON_PATH" | gh secret set "GOOGLE_CLOUD_KEY_JSON" --repo="$REPO"
    echo -e "${GREEN}  ✓ Added GOOGLE_CLOUD_KEY_JSON${NC}"
else
    echo -e "${YELLOW}Warning: $KEY_JSON_PATH not found${NC}"
fi

echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo
echo -e "${BLUE}Variables (Public):${NC}"
echo "  - API configuration"
echo "  - Topic names"
echo "  - Bucket names"
echo "  - Server info"
echo
echo -e "${RED}Secrets (Encrypted):${NC}"
echo "  - Database credentials"
echo "  - AWS keys"  
echo "  - SSH keys"
echo "  - GCP service account"
echo
echo -e "${YELLOW}View at:${NC}"
echo "  Variables: https://github.com/$REPO/settings/variables/actions"
echo "  Secrets:   https://github.com/$REPO/settings/secrets/actions"