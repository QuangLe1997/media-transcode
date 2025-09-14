# GitHub Secrets Setup for CI/CD

This guide explains how to set up GitHub Secrets for automatic deployment to your server.

## Required Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions, then add these secrets:

### 1. Server Connection
- **SERVER_HOST**: `54.248.140.63`
- **SERVER_USER**: `quanglv`
- **SERVER_SSH_KEY**: Your private SSH key content (see below)

### 2. AWS S3 Configuration
- **AWS_ACCESS_KEY_ID**: Your AWS access key
- **AWS_SECRET_ACCESS_KEY**: Your AWS secret key
- **AWS_BUCKET_NAME**: Your S3 bucket name
- **AWS_ENDPOINT_URL**: S3 endpoint URL (optional for custom S3)
- **AWS_ENDPOINT_PUBLIC_URL**: Public S3 endpoint URL
- **AWS_BASE_FOLDER**: Base folder in S3 bucket

### 3. Google Cloud Configuration
- **GOOGLE_CLOUD_KEY_JSON**: Content of your GCP service account key.json file
- **PUBSUB_PROJECT_ID**: Your GCP project ID
- **PUBSUB_TASKS_TOPIC**: Pub/Sub topic for tasks
- **TASKS_SUBSCRIPTION**: Tasks subscription name
- **PUBSUB_RESULTS_TOPIC**: Results topic
- **PUBSUB_RESULTS_SUBSCRIPTION**: Results subscription

### 4. Face Detection Configuration
- **PUBSUB_FACE_DETECTION_TASKS_TOPIC**: Face detection tasks topic
- **PUBSUB_FACE_DETECTION_RESULTS_TOPIC**: Face detection results topic
- **PUBSUB_FACE_DETECTION_RESULTS_SUBSCRIPTION**: Face detection results subscription
- **FACE_DETECTION_SUBSCRIPTION**: Face detection subscription

### 5. Task Listener Configuration
- **PUBSUB_TASK_SUBSCRIPTION**: Task listener subscription
- **PUBSUB_MAX_MESSAGES**: Maximum messages to process (default: 10)

### 6. Optional
- **DISABLE_PUBSUB**: Set to `true` to disable Pub/Sub (for testing)

## How to Generate SSH Key for GitHub Actions

1. On your local machine, generate a new SSH key pair:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_actions_deploy -C "github-actions"
```

2. Copy the public key to your server:
```bash
ssh-copy-id -i ~/.ssh/github_actions_deploy.pub quanglv@54.248.140.63
```

3. Copy the private key content:
```bash
cat ~/.ssh/github_actions_deploy
```

4. Add the private key content to GitHub Secrets as `SERVER_SSH_KEY`

## Testing the Deployment

1. Make sure your server has Docker and Docker Compose installed:
```bash
ssh quanglv@54.248.140.63
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. Verify NVIDIA Docker runtime (if using GPU):
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

3. Test the deployment by pushing to master branch:
```bash
git add .
git commit -m "Test deployment"
git push origin master
```

4. Monitor the deployment in GitHub Actions tab

## Manual Deployment

If you need to deploy manually:

```bash
ssh quanglv@54.248.140.63
cd ~/media-transcode/deployment
./deploy.sh
```

## Troubleshooting

1. **SSH Connection Failed**: 
   - Check if the SSH key is correctly added to GitHub Secrets
   - Verify server is accessible: `ssh quanglv@54.248.140.63`

2. **Docker Build Failed**:
   - Check if Docker is installed on server
   - Verify there's enough disk space

3. **Services Not Starting**:
   - Check logs: `docker-compose logs`
   - Verify all environment variables are set

4. **Port Already in Use**:
   - Check running services: `sudo netstat -tlnp`
   - Stop conflicting services or change ports in docker-compose.yml