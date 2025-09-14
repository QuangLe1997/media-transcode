# Scripts Directory

This directory contains all automation scripts for the media-transcode project, organized by purpose.

## 📁 Directory Structure

```
scripts/
├── setup/           # GitHub & Environment setup scripts
├── deployment/      # Deployment automation scripts
└── README.md        # This file
```

---

## 🔧 Setup Scripts (`scripts/setup/`)

### GitHub Secrets Management

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup-vars-and-secrets.sh` | **Main script** - Properly categorize Variables vs Secrets | `./setup-vars-and-secrets.sh` |
| `sync-env-to-secrets.sh` | Sync all .env variables to GitHub Secrets (legacy) | `./sync-env-to-secrets.sh` |
| `quick-setup-secrets.sh` | Quick setup with minimal configuration | `./quick-setup-secrets.sh` |
| `cleanup-secrets.sh` | Remove secrets that were converted to variables | `./cleanup-secrets.sh` |

### Recommended Usage Order:
1. **First time**: `./setup-vars-and-secrets.sh`
2. **Clean up**: `./cleanup-secrets.sh` 
3. **Updates**: Modify .env then run `./setup-vars-and-secrets.sh` again

---

## 🚀 Deployment Scripts (`scripts/deployment/`)

| Script | Purpose | Usage |
|--------|---------|-------|
| `manual-deploy.sh` | Manual deployment when GitHub Actions fails | `./manual-deploy.sh` |

### When to Use Manual Deploy:
- GitHub Actions SSH/Webhook fails
- Quick deployment for testing
- Emergency deployments
- Local development deployments

---

## 🎯 Quick Start Guide

### 1. Initial Setup
```bash
# Setup GitHub Variables and Secrets
cd scripts/setup
export GITHUB_TOKEN="your-token-here"
./setup-vars-and-secrets.sh

# Clean up old secrets
./cleanup-secrets.sh
```

### 2. Deploy Application
```bash
# Option A: Push to GitHub (triggers webhook)
git push origin master

# Option B: Manual deployment
cd scripts/deployment  
./manual-deploy.sh
```

### 3. Update Configuration
```bash
# Edit your .env file
nano deployment/.env

# Sync to GitHub
cd scripts/setup
./setup-vars-and-secrets.sh
```

---

## 📋 Prerequisites

### Required Tools:
- **GitHub CLI**: `brew install gh` (for setup scripts)
- **jq**: `brew install jq` (for JSON processing)
- **curl**: Usually pre-installed
- **ssh**: Access to deployment server

### Required Access:
- GitHub repository with admin access
- Server SSH access (quanglv@54.248.140.63)
- GitHub Personal Access Token

---

## 🔐 Security Notes

### Safe Scripts:
- ✅ All setup scripts use GitHub CLI for secure token handling
- ✅ Sensitive data is passed via environment variables
- ✅ No hardcoded credentials in scripts

### Important:
- 🔒 Never commit `.env` files
- 🔒 GitHub Secrets are encrypted and secure
- 🔒 Scripts validate authentication before proceeding

---

## 🐛 Troubleshooting

### GitHub CLI Issues:
```bash
# Check authentication
gh auth status

# Re-authenticate if needed
gh auth login
```

### Server Connection Issues:
```bash
# Test SSH connection
ssh quanglv@54.248.140.63 "echo 'Connection OK'"

# Test webhook server
curl http://54.248.140.63:3001/health
```

### Script Permissions:
```bash
# Make scripts executable
chmod +x scripts/setup/*.sh
chmod +x scripts/deployment/*.sh
```

---

## 📚 Related Documentation

- [WEBHOOK_DEPLOYMENT.md](../WEBHOOK_DEPLOYMENT.md) - Webhook deployment setup
- [VARIABLES_vs_SECRETS.md](../VARIABLES_vs_SECRETS.md) - GitHub Variables vs Secrets guide
- [GITHUB_SECRETS_SETUP.md](../GITHUB_SECRETS_SETUP.md) - Original secrets setup guide

---

## 🔄 Script Updates

When scripts are updated:
1. Pull latest changes: `git pull origin master`
2. Update script permissions: `chmod +x scripts/*/*.sh`
3. Review changes before running

---

## 💡 Tips

### Efficiency:
- Use `setup-vars-and-secrets.sh` for most cases
- Keep scripts organized in their respective folders
- Use manual deployment for quick testing

### Debugging:
- Scripts have verbose output for debugging
- Check GitHub Actions logs for webhook failures
- Monitor server logs: `ssh quanglv@54.248.140.63 "sudo journalctl -u webhook-deploy -f"`