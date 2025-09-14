# GitHub Variables vs Secrets Configuration

This document explains the difference between GitHub Variables and Secrets and how they're used in our CI/CD pipeline.

## 🔐 Variables vs Secrets

### Variables (Public Configuration)
- **Storage**: Stored as plain text (not encrypted)
- **Visibility**: Visible in GitHub Actions logs
- **Use case**: Non-sensitive configuration data
- **Location**: Repository → Settings → Variables → Actions

### Secrets (Sensitive Data)
- **Storage**: Encrypted and secure
- **Visibility**: Hidden from logs (shows as ***)
- **Use case**: Passwords, keys, tokens
- **Location**: Repository → Settings → Secrets → Actions

---

## 📊 Our Configuration Breakdown

### 🌐 Variables (Non-sensitive)
| Variable Name | Value | Description |
|---------------|-------|-------------|
| `SERVER_HOST` | `54.248.140.63` | Deployment server IP |
| `SERVER_USER` | `quanglv` | SSH username |
| `API_HOST` | `0.0.0.0` | API host binding |
| `API_PORT` | `8087` | API port number |
| `DEBUG` | `true` | Debug mode flag |
| `AWS_BUCKET_NAME` | `dev-facefusion-media` | S3 bucket name |
| `AWS_ENDPOINT_URL` | `https://storage.skylink.vn` | S3 endpoint URL |
| `AWS_ENDPOINT_PUBLIC_URL` | `https://static-vncdn.skylinklabs.ai` | Public S3 URL |
| `AWS_BASE_FOLDER` | `transcode-service` | S3 base folder |
| `PUBSUB_PROJECT_ID` | `kiwi2-454610` | GCP Project ID |
| `PUBSUB_TASKS_TOPIC` | `transcode-utils-tasks` | Transcode tasks topic |
| `TASKS_SUBSCRIPTION` | `transcode-utils-tasks-sub` | Tasks subscription |
| `PUBSUB_RESULTS_TOPIC` | `transcode-utils-results` | Results topic |
| `PUBSUB_RESULTS_SUBSCRIPTION` | `transcode-utils-results-sub` | Results subscription |
| `PUBSUB_FACE_DETECTION_*` | Various | Face detection topic names |
| `PUBSUB_PUBLISHER_CREDENTIALS_PATH` | `/app/key.json` | GCP credentials path |

### 🔒 Secrets (Sensitive)
| Secret Name | Description |
|-------------|-------------|
| `DATABASE_URL` | PostgreSQL connection string with credentials |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key |
| `SERVER_SSH_KEY` | Private SSH key for server access |
| `GOOGLE_CLOUD_KEY_JSON` | GCP service account JSON key |

---

## 🚀 Setup Commands

### Automated Setup
```bash
# Setup both variables and secrets properly categorized
./setup-vars-and-secrets.sh
```

### Manual Setup
```bash
# Add variable (public)
gh variable set VARIABLE_NAME --body="value" --repo="QuangLe1997/media-transcode"

# Add secret (encrypted)
echo "secret_value" | gh secret set SECRET_NAME --repo="QuangLe1997/media-transcode"
```

---

## 🔍 Usage in GitHub Actions

### Accessing Variables
```yaml
# In workflow file
steps:
  - name: Use variable
    run: echo "API Port is ${{ vars.API_PORT }}"
```

### Accessing Secrets
```yaml
# In workflow file
steps:
  - name: Use secret
    run: echo "Connecting with credentials"
    env:
      DB_URL: ${{ secrets.DATABASE_URL }}
```

---

## ✅ Benefits of This Approach

### 🔍 **Transparency**
- Variables are visible → easier debugging
- Secrets are hidden → better security

### 🔒 **Security**
- Credentials never appear in logs
- Public config is clearly marked

### 🛠️ **Maintenance** 
- Easy to update non-sensitive values
- Clear separation of concerns

### 🎯 **Best Practice**
- Follows GitHub's recommended patterns
- Easier for team collaboration

---

## 🚨 Security Guidelines

### ✅ Do's
- Use **Variables** for public configuration
- Use **Secrets** for credentials, keys, tokens
- Keep database URLs as secrets (contain credentials)
- Regular audit of what's stored where

### ❌ Don'ts
- Never put passwords in Variables
- Don't hardcode secrets in code
- Avoid mixing sensitive/non-sensitive data

---

## 🎯 Quick Reference

### View Your Configuration
- **Variables**: https://github.com/QuangLe1997/media-transcode/settings/variables/actions
- **Secrets**: https://github.com/QuangLe1997/media-transcode/settings/secrets/actions

### Update Configuration
```bash
# When you change .env file, run:
./setup-vars-and-secrets.sh
```

### Test Configuration
```bash
# Push to trigger deployment
git push origin master
```