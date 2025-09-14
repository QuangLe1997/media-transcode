#!/bin/bash

# Script to sync .env file variables to GitHub Secrets
# This reads your local .env file and creates GitHub secrets

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPO="QuangLe1997/media-transcode"
ENV_FILE="deployment/.env"

echo -e "${BLUE}=== Sync .env to GitHub Secrets ===${NC}"
echo

# Check if env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: $ENV_FILE not found${NC}"
    exit 1
fi

# Check GitHub CLI auth
# Make sure GITHUB_TOKEN is set in your environment or gh is authenticated
if ! gh auth status > /dev/null 2>&1; then
    echo -e "${RED}Error: GitHub CLI not authenticated${NC}"
    echo "Please run: gh auth login"
    echo "Or set GITHUB_TOKEN environment variable"
    exit 1
fi

echo -e "${GREEN}✓ Reading from $ENV_FILE${NC}"
echo

# Function to add secret
add_secret() {
    local name=$1
    local value=$2
    
    if [ -z "$value" ] || [ "$value" == "" ]; then
        echo -e "${YELLOW}  Skipping $name (empty value)${NC}"
        return
    fi
    
    echo -e "${YELLOW}Adding secret: $name${NC}"
    echo "$value" | gh secret set "$name" --repo="$REPO"
    echo -e "${GREEN}  ✓ Added${NC}"
}

# Read .env file and process each line
while IFS='=' read -r key value; do
    # Skip empty lines and comments
    if [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    # Remove leading/trailing whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    
    # Remove quotes if present
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    
    # Add to GitHub Secrets
    if [ ! -z "$key" ] && [ ! -z "$value" ]; then
        add_secret "$key" "$value"
    fi
done < "$ENV_FILE"

# Add Google Cloud key.json if exists
KEY_JSON_PATH="src/transcode_service/key.json"
if [ -f "$KEY_JSON_PATH" ]; then
    echo -e "${YELLOW}Adding Google Cloud key.json${NC}"
    GOOGLE_CLOUD_KEY_JSON=$(cat "$KEY_JSON_PATH")
    echo "$GOOGLE_CLOUD_KEY_JSON" | gh secret set "GOOGLE_CLOUD_KEY_JSON" --repo="$REPO"
    echo -e "${GREEN}  ✓ Added GOOGLE_CLOUD_KEY_JSON${NC}"
else
    echo -e "${YELLOW}Warning: $KEY_JSON_PATH not found${NC}"
    # Create dummy key.json for GitHub Actions
    echo '{"type":"service_account","project_id":"dummy"}' | gh secret set "GOOGLE_CLOUD_KEY_JSON" --repo="$REPO"
fi

# Also ensure server secrets are set
echo -e "${BLUE}=== Ensuring server secrets ===${NC}"
add_secret "SERVER_HOST" "54.248.140.63"
add_secret "SERVER_USER" "quanglv"

# Check if SSH key exists and add it
SSH_KEY="$HOME/.ssh/github_actions_deploy"
if [ -f "$SSH_KEY" ]; then
    echo -e "${YELLOW}Adding SSH key${NC}"
    cat "$SSH_KEY" | gh secret set "SERVER_SSH_KEY" --repo="$REPO"
    echo -e "${GREEN}  ✓ Added SERVER_SSH_KEY${NC}"
fi

echo
echo -e "${GREEN}=== Sync Complete ===${NC}"
echo -e "${GREEN}All environment variables have been added to GitHub Secrets${NC}"
echo
echo -e "${YELLOW}View secrets at:${NC}"
echo "https://github.com/$REPO/settings/secrets/actions"
echo
echo -e "${YELLOW}Trigger deployment:${NC}"
echo "git push origin master"