#!/bin/bash

# Quick setup script for minimal deployment (without AWS/GCP)
# This sets up only the essential secrets for basic deployment

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO="QuangLe1997/media-transcode"

echo -e "${GREEN}=== Quick GitHub Secrets Setup ===${NC}"

# Check gh CLI
if ! gh auth status > /dev/null 2>&1; then
    echo -e "${RED}GitHub CLI not authenticated. Running: gh auth login${NC}"
    gh auth login
fi

# 1. Generate SSH key if not exists
SSH_KEY="$HOME/.ssh/github_actions_deploy"
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${YELLOW}Generating SSH key...${NC}"
    ssh-keygen -t ed25519 -f "$SSH_KEY" -C "github-actions" -N ""
    ssh-copy-id -i "${SSH_KEY}.pub" quanglv@54.248.140.63
    echo -e "${GREEN}✓ SSH key created and copied to server${NC}"
fi

# 2. Add essential secrets
echo -e "${YELLOW}Adding secrets to GitHub...${NC}"

# Server secrets
gh secret set SERVER_HOST --body="54.248.140.63" --repo="$REPO"
gh secret set SERVER_USER --body="quanglv" --repo="$REPO"
cat "$SSH_KEY" | gh secret set SERVER_SSH_KEY --repo="$REPO"

# Minimal environment (disable external services)
gh secret set DISABLE_PUBSUB --body="true" --repo="$REPO"
gh secret set AWS_ACCESS_KEY_ID --body="dummy" --repo="$REPO"
gh secret set AWS_SECRET_ACCESS_KEY --body="dummy" --repo="$REPO"
gh secret set AWS_BUCKET_NAME --body="dummy" --repo="$REPO"
gh secret set PUBSUB_PROJECT_ID --body="dummy" --repo="$REPO"
gh secret set GOOGLE_CLOUD_KEY_JSON --body='{"type":"service_account"}' --repo="$REPO"

echo -e "${GREEN}✓ Basic secrets configured${NC}"
echo
echo -e "${YELLOW}Deployment will work with:${NC}"
echo "  - PostgreSQL database"
echo "  - API service"
echo "  - Frontend"
echo "  - Local file storage (no S3/GCS)"
echo
echo -e "${GREEN}Push to master to trigger deployment:${NC}"
echo "  git push origin master"
echo
echo -e "${GREEN}Monitor at:${NC}"
echo "  https://github.com/$REPO/actions"