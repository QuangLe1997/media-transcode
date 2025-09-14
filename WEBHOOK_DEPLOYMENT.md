# Webhook Deployment Setup

This document explains how to set up webhook-based deployment as an alternative to SSH deployment when GitHub Actions cannot directly connect to your server.

## 🚨 Why Webhook Deployment?

GitHub Actions runners cannot connect to AWS EC2 instances via SSH due to network restrictions. The webhook approach solves this by:
- GitHub Actions triggers a webhook to your server
- Your server pulls code and deploys locally
- No inbound SSH connection required

---

## 🏗️ Architecture

```
GitHub Actions → HTTP Webhook → Server → Docker Deployment
     ↓               ↓            ↓           ↓
  1. Push code   2. POST to    3. Pull &   4. Update 
     to master      /deploy       Build       Services
```

---

## ⚙️ Server Setup

### 1. Run Setup Script on Server

```bash
ssh quanglv@54.248.140.63
cd ~/media-transcode/deployment
./setup-webhook-server.sh
```

The script will:
- Install Node.js if needed
- Install npm dependencies  
- Generate webhook secret
- Create systemd service
- Configure firewall
- Start webhook server on port 3001

### 2. Copy Webhook Secret

The setup script will output a webhook secret like:
```
🔑 Add this secret to GitHub Secrets as WEBHOOK_SECRET:
d959c2fbf19b4ecee06a3a33a374e673f57808fe38d66683d784f2d87a949606
```

This is already added to GitHub Secrets automatically.

---

## 🔧 GitHub Actions Configuration

The webhook deployment uses `.github/workflows/deploy-webhook.yml`:

- **Triggers**: Push to master branch
- **Method**: HTTP POST to `http://SERVER:3001/deploy`
- **Auth**: Bearer token (WEBHOOK_SECRET)
- **Payload**: Environment variables + deployment info

---

## 🚀 How It Works

### 1. Code Push
```bash
git push origin master
```

### 2. GitHub Actions Workflow
- Triggers `deploy-webhook.yml`
- Collects all environment variables
- Sends POST request to server webhook

### 3. Server Webhook Handler
- Authenticates request
- Pulls latest code from git
- Creates `.env` file
- Creates GCP `key.json`
- Builds and deploys Docker containers
- Performs health checks

### 4. Deployment Complete
- Services available at configured ports
- Logs available in webhook server logs

---

## 📊 Monitoring & Debugging

### Check Webhook Server Status
```bash
sudo systemctl status webhook-deploy
```

### View Webhook Logs
```bash
# System logs
sudo journalctl -u webhook-deploy -f

# Application logs
tail -f ~/media-transcode/deployment/webhook-deploy.log
```

### Test Webhook Server
```bash
curl http://localhost:3001/health
```

### Manual Webhook Trigger
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_WEBHOOK_SECRET" \
  -d '{"repository":"test","sha":"test"}' \
  http://localhost:3001/deploy
```

---

## 🔒 Security

### Webhook Authentication
- Uses Bearer token authentication
- Secret stored in GitHub Secrets and server environment
- 256-bit random secret generated during setup

### Network Security
- Webhook server only listens on port 3001
- Firewall configured to allow this port
- Server authenticates all deployment requests

### Environment Variables
- Sensitive data passed securely via webhook payload
- `.env` file created on server with proper permissions
- GCP credentials stored securely

---

## 🛠️ Service Management

### Start/Stop/Restart Service
```bash
sudo systemctl start webhook-deploy
sudo systemctl stop webhook-deploy
sudo systemctl restart webhook-deploy
```

### Enable/Disable Auto-start
```bash
sudo systemctl enable webhook-deploy
sudo systemctl disable webhook-deploy
```

### Update Webhook Server
```bash
# Pull latest code
cd ~/media-transcode
git pull origin master

# Restart service
sudo systemctl restart webhook-deploy
```

---

## 📈 Endpoints

### Health Check
- **URL**: `http://54.248.140.63:3001/health`
- **Method**: GET
- **Auth**: None required
- **Response**: Server status and uptime

### Deploy Webhook
- **URL**: `http://54.248.140.63:3001/deploy`
- **Method**: POST
- **Auth**: Bearer token required
- **Payload**: Deployment configuration

---

## 🎯 Services After Deployment

After successful webhook deployment:

- **API**: http://54.248.140.63:8087
- **Frontend**: http://54.248.140.63:3000
- **Database**: postgresql://54.248.140.63:5433
- **Webhook Server**: http://54.248.140.63:3001

---

## 🐛 Troubleshooting

### Webhook Server Not Starting
```bash
# Check logs
sudo journalctl -u webhook-deploy -n 50

# Check Node.js installation
node --version
npm --version

# Check port availability
netstat -tlnp | grep 3001
```

### Deployment Fails
```bash
# Check webhook logs
tail -f ~/media-transcode/deployment/webhook-deploy.log

# Check Docker status
docker ps
docker-compose ps -a

# Check git repository
cd ~/media-transcode
git status
git log --oneline -5
```

### GitHub Actions Webhook Fails
1. Check webhook secret matches
2. Verify server is accessible on port 3001
3. Check firewall allows inbound port 3001
4. Review GitHub Actions logs

---

## ✅ Advantages

- **Reliable**: No SSH connection issues
- **Secure**: Token-based authentication
- **Fast**: Direct HTTP communication
- **Scalable**: Can handle multiple deployments
- **Logged**: Full deployment history

This webhook approach ensures reliable deployments even when SSH is not available!