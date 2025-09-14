#!/bin/bash

# Script to setup GitHub Secrets for CI/CD
# This script uses GitHub CLI to add secrets to the repository

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Repository info
REPO="QuangLe1997/media-transcode"

echo -e "${BLUE}=== GitHub Secrets Setup for media-transcode ===${NC}"
echo

# Check if gh CLI is authenticated
if ! gh auth status > /dev/null 2>&1; then
    echo -e "${RED}Error: GitHub CLI is not authenticated${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✓ GitHub CLI is authenticated${NC}"
echo

# Function to add secret
add_secret() {
    local name=$1
    local value=$2
    local description=$3
    
    echo -e "${YELLOW}Adding secret: $name${NC}"
    echo -e "  Description: $description"
    
    if [ -z "$value" ]; then
        echo -e "${RED}  ✗ Skipped (no value provided)${NC}"
        return
    fi
    
    echo "$value" | gh secret set "$name" --repo="$REPO"
    echo -e "${GREEN}  ✓ Added successfully${NC}"
    echo
}

# Server configuration
echo -e "${BLUE}=== Server Configuration ===${NC}"
SERVER_HOST="54.248.140.63"
SERVER_USER="quanglv"

add_secret "SERVER_HOST" "$SERVER_HOST" "Server IP address"
add_secret "SERVER_USER" "$SERVER_USER" "SSH username"

# SSH Key Setup
echo -e "${BLUE}=== SSH Key Setup ===${NC}"
SSH_KEY_PATH="$HOME/.ssh/github_actions_deploy"

if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${YELLOW}Generating new SSH key for GitHub Actions...${NC}"
    ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -C "github-actions" -N ""
    echo -e "${GREEN}✓ SSH key generated${NC}"
    
    echo -e "${YELLOW}Copying public key to server...${NC}"
    ssh-copy-id -i "${SSH_KEY_PATH}.pub" "$SERVER_USER@$SERVER_HOST"
    echo -e "${GREEN}✓ Public key added to server${NC}"
else
    echo -e "${GREEN}✓ SSH key already exists${NC}"
fi

SSH_KEY_CONTENT=$(cat "$SSH_KEY_PATH")
add_secret "SERVER_SSH_KEY" "$SSH_KEY_CONTENT" "Private SSH key for server access"

# AWS Configuration
echo -e "${BLUE}=== AWS S3 Configuration ===${NC}"
echo -e "${YELLOW}Please enter AWS configuration (press Enter to skip):${NC}"

read -p "AWS_ACCESS_KEY_ID: " AWS_ACCESS_KEY_ID
add_secret "AWS_ACCESS_KEY_ID" "$AWS_ACCESS_KEY_ID" "AWS Access Key ID"

read -s -p "AWS_SECRET_ACCESS_KEY: " AWS_SECRET_ACCESS_KEY
echo
add_secret "AWS_SECRET_ACCESS_KEY" "$AWS_SECRET_ACCESS_KEY" "AWS Secret Access Key"

read -p "AWS_BUCKET_NAME: " AWS_BUCKET_NAME
add_secret "AWS_BUCKET_NAME" "$AWS_BUCKET_NAME" "S3 Bucket name"

read -p "AWS_ENDPOINT_URL (optional): " AWS_ENDPOINT_URL
add_secret "AWS_ENDPOINT_URL" "$AWS_ENDPOINT_URL" "Custom S3 endpoint URL"

read -p "AWS_ENDPOINT_PUBLIC_URL (optional): " AWS_ENDPOINT_PUBLIC_URL
add_secret "AWS_ENDPOINT_PUBLIC_URL" "$AWS_ENDPOINT_PUBLIC_URL" "Public S3 endpoint URL"

read -p "AWS_BASE_FOLDER (optional): " AWS_BASE_FOLDER
add_secret "AWS_BASE_FOLDER" "$AWS_BASE_FOLDER" "Base folder in S3"

# Google Cloud Configuration
echo -e "${BLUE}=== Google Cloud Configuration ===${NC}"
echo -e "${YELLOW}Please enter Google Cloud configuration (press Enter to skip):${NC}"

# Check if key.json exists
KEY_JSON_PATH="src/transcode_service/key.json"
if [ -f "$KEY_JSON_PATH" ]; then
    echo -e "${GREEN}Found key.json file${NC}"
    GOOGLE_CLOUD_KEY_JSON=$(cat "$KEY_JSON_PATH")
    add_secret "GOOGLE_CLOUD_KEY_JSON" "$GOOGLE_CLOUD_KEY_JSON" "GCP Service Account key"
else
    echo -e "${YELLOW}key.json not found. Please provide the path:${NC}"
    read -p "Path to key.json file: " KEY_PATH
    if [ -f "$KEY_PATH" ]; then
        GOOGLE_CLOUD_KEY_JSON=$(cat "$KEY_PATH")
        add_secret "GOOGLE_CLOUD_KEY_JSON" "$GOOGLE_CLOUD_KEY_JSON" "GCP Service Account key"
    fi
fi

read -p "PUBSUB_PROJECT_ID: " PUBSUB_PROJECT_ID
add_secret "PUBSUB_PROJECT_ID" "$PUBSUB_PROJECT_ID" "GCP Project ID"

read -p "PUBSUB_TASKS_TOPIC: " PUBSUB_TASKS_TOPIC
add_secret "PUBSUB_TASKS_TOPIC" "$PUBSUB_TASKS_TOPIC" "Pub/Sub tasks topic"

read -p "TASKS_SUBSCRIPTION: " TASKS_SUBSCRIPTION
add_secret "TASKS_SUBSCRIPTION" "$TASKS_SUBSCRIPTION" "Tasks subscription"

read -p "PUBSUB_RESULTS_TOPIC: " PUBSUB_RESULTS_TOPIC
add_secret "PUBSUB_RESULTS_TOPIC" "$PUBSUB_RESULTS_TOPIC" "Results topic"

read -p "PUBSUB_RESULTS_SUBSCRIPTION: " PUBSUB_RESULTS_SUBSCRIPTION
add_secret "PUBSUB_RESULTS_SUBSCRIPTION" "$PUBSUB_RESULTS_SUBSCRIPTION" "Results subscription"

# Face Detection Configuration
echo -e "${BLUE}=== Face Detection Configuration ===${NC}"
echo -e "${YELLOW}Face detection topics (press Enter to use defaults):${NC}"

read -p "PUBSUB_FACE_DETECTION_TASKS_TOPIC [face-detection-worker-tasks]: " PUBSUB_FACE_DETECTION_TASKS_TOPIC
PUBSUB_FACE_DETECTION_TASKS_TOPIC=${PUBSUB_FACE_DETECTION_TASKS_TOPIC:-face-detection-worker-tasks}
add_secret "PUBSUB_FACE_DETECTION_TASKS_TOPIC" "$PUBSUB_FACE_DETECTION_TASKS_TOPIC" "Face detection tasks topic"

read -p "PUBSUB_FACE_DETECTION_RESULTS_TOPIC [face-detection-worker-results]: " PUBSUB_FACE_DETECTION_RESULTS_TOPIC
PUBSUB_FACE_DETECTION_RESULTS_TOPIC=${PUBSUB_FACE_DETECTION_RESULTS_TOPIC:-face-detection-worker-results}
add_secret "PUBSUB_FACE_DETECTION_RESULTS_TOPIC" "$PUBSUB_FACE_DETECTION_RESULTS_TOPIC" "Face detection results topic"

read -p "PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION [face-detection-worker-results-sub]: " PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION
PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION=${PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION:-face-detection-worker-results-sub}
add_secret "PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION" "$PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION" "Face detection results subscription"

read -p "FACE_DETECTION_SUBSCRIPTION [face-detection-worker-tasks-sub]: " FACE_DETECTION_SUBSCRIPTION
FACE_DETECTION_SUBSCRIPTION=${FACE_DETECTION_SUBSCRIPTION:-face-detection-worker-tasks-sub}
add_secret "FACE_DETECTION_SUBSCRIPTION" "$FACE_DETECTION_SUBSCRIPTION" "Face detection subscription"

# Task Listener Configuration
echo -e "${BLUE}=== Task Listener Configuration ===${NC}"

read -p "PUBSUB_TASK_SUBSCRIPTION [skl-transcode-cms-tasks-sub]: " PUBSUB_TASK_SUBSCRIPTION
PUBSUB_TASK_SUBSCRIPTION=${PUBSUB_TASK_SUBSCRIPTION:-skl-transcode-cms-tasks-sub}
add_secret "PUBSUB_TASK_SUBSCRIPTION" "$PUBSUB_TASK_SUBSCRIPTION" "Task listener subscription"

read -p "PUBSUB_MAX_MESSAGES [10]: " PUBSUB_MAX_MESSAGES
PUBSUB_MAX_MESSAGES=${PUBSUB_MAX_MESSAGES:-10}
add_secret "PUBSUB_MAX_MESSAGES" "$PUBSUB_MAX_MESSAGES" "Max messages to process"

# Optional settings
echo -e "${BLUE}=== Optional Settings ===${NC}"

read -p "DISABLE_PUBSUB (true/false) [false]: " DISABLE_PUBSUB
DISABLE_PUBSUB=${DISABLE_PUBSUB:-false}
add_secret "DISABLE_PUBSUB" "$DISABLE_PUBSUB" "Disable Pub/Sub for testing"

# Summary
echo -e "${BLUE}=== Setup Complete ===${NC}"
echo -e "${GREEN}✓ All secrets have been configured${NC}"
echo
echo -e "${YELLOW}You can view your secrets at:${NC}"
echo "https://github.com/$REPO/settings/secrets/actions"
echo
echo -e "${YELLOW}To trigger deployment, push to master branch:${NC}"
echo "git push origin master"
echo
echo -e "${YELLOW}Monitor deployment at:${NC}"
echo "https://github.com/$REPO/actions"