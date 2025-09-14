#!/usr/bin/env node

/**
 * Webhook server to receive deployment requests from GitHub Actions
 * This runs on the deployment server and triggers the deployment process
 */

const express = require('express');
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const app = express();
const PORT = 3001;

// Configuration
const PROJECT_DIR = '/home/quanglv/media-transcode';
const DEPLOYMENT_DIR = path.join(PROJECT_DIR, 'deployment');
const LOG_FILE = path.join(DEPLOYMENT_DIR, 'webhook-deploy.log');

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Logging function
function log(message) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] ${message}\n`;
    console.log(logEntry.trim());
    try {
        fs.appendFileSync(LOG_FILE, logEntry);
    } catch (err) {
        console.error('Failed to write to log file:', err.message);
    }
}

// Verify webhook authentication
function verifyWebhookAuth(req, res, next) {
    const authHeader = req.headers.authorization;
    const expectedToken = process.env.WEBHOOK_SECRET;
    
    if (!expectedToken) {
        log('ERROR: WEBHOOK_SECRET not set');
        return res.status(500).json({ error: 'Server configuration error' });
    }
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        log('ERROR: Missing or invalid Authorization header');
        return res.status(401).json({ error: 'Unauthorized: Missing token' });
    }
    
    const token = authHeader.substring(7);
    if (token !== expectedToken) {
        log('ERROR: Invalid webhook token');
        return res.status(401).json({ error: 'Unauthorized: Invalid token' });
    }
    
    next();
}

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        project_dir: PROJECT_DIR
    });
});

// Main deployment endpoint
app.post('/deploy', verifyWebhookAuth, async (req, res) => {
    const deploymentId = crypto.randomUUID();
    log(`🚀 Starting deployment ${deploymentId}`);
    log(`Repository: ${req.body.repository}`);
    log(`SHA: ${req.body.sha}`);
    log(`Actor: ${req.body.actor}`);
    
    try {
        // Send immediate response
        res.json({
            status: 'deployment_started',
            deployment_id: deploymentId,
            message: 'Deployment process initiated successfully'
        });
        
        // Run deployment asynchronously
        await runDeployment(req.body, deploymentId);
        
    } catch (error) {
        log(`❌ Deployment ${deploymentId} failed: ${error.message}`);
        if (!res.headersSent) {
            res.status(500).json({
                status: 'deployment_failed',
                deployment_id: deploymentId,
                error: error.message
            });
        }
    }
});

async function runDeployment(payload, deploymentId) {
    try {
        log(`📂 Changing to project directory: ${PROJECT_DIR}`);
        process.chdir(PROJECT_DIR);
        
        // Pull latest code
        log('📥 Pulling latest code from git...');
        execSync('git pull origin master', { 
            stdio: ['pipe', 'pipe', 'pipe'],
            cwd: PROJECT_DIR 
        });
        log('✅ Code updated successfully');
        
        // Create .env file with environment variables
        log('📝 Creating .env file...');
        const envContent = generateEnvFile(payload.environment_variables);
        fs.writeFileSync(path.join(DEPLOYMENT_DIR, '.env'), envContent);
        log('✅ Environment file created');
        
        // Create Google Cloud key file
        if (payload.google_cloud_key) {
            log('🔑 Creating Google Cloud key file...');
            const keyPath = path.join(PROJECT_DIR, 'src/transcode_service/key.json');
            fs.writeFileSync(keyPath, payload.google_cloud_key);
            execSync(`chmod 600 "${keyPath}"`);
            log('✅ Google Cloud key file created');
        }
        
        // Change to deployment directory
        process.chdir(DEPLOYMENT_DIR);
        
        // Stop existing containers
        log('🛑 Stopping existing containers...');
        try {
            execSync('docker-compose down', { stdio: 'pipe' });
        } catch (err) {
            log('⚠️  No existing containers to stop');
        }
        
        // Build and start containers
        log('🏗️  Building and starting containers...');
        execSync('docker-compose pull', { stdio: 'pipe' });
        execSync('docker-compose build --no-cache', { 
            stdio: 'pipe',
            timeout: 20 * 60 * 1000 // 20 minutes timeout
        });
        
        execSync('docker-compose up -d', { stdio: 'pipe' });
        log('✅ Containers started successfully');
        
        // Wait a bit for services to initialize
        log('⏳ Waiting for services to initialize...');
        await new Promise(resolve => setTimeout(resolve, 30000));
        
        // Health check
        log('🔍 Running health checks...');
        const containerStatus = execSync('docker-compose ps', { 
            encoding: 'utf8',
            cwd: DEPLOYMENT_DIR 
        });
        log(`Container status:\n${containerStatus}`);
        
        // Clean up old images
        log('🧹 Cleaning up old Docker images...');
        try {
            execSync('docker image prune -f', { stdio: 'pipe' });
        } catch (err) {
            log('⚠️  Failed to clean up images: ' + err.message);
        }
        
        log(`🎉 Deployment ${deploymentId} completed successfully!`);
        log('🌐 Services should be available at:');
        log('  - API: http://localhost:8087');
        log('  - Frontend: http://localhost:3000');
        
    } catch (error) {
        log(`💥 Deployment ${deploymentId} failed: ${error.message}`);
        if (error.stdout) log(`stdout: ${error.stdout}`);
        if (error.stderr) log(`stderr: ${error.stderr}`);
        throw error;
    }
}

function generateEnvFile(envVars) {
    const lines = [
        '# Auto-generated environment file from GitHub Actions deployment',
        `# Generated at: ${new Date().toISOString()}`,
        '',
    ];
    
    for (const [key, value] of Object.entries(envVars)) {
        if (value && value !== 'undefined' && value !== 'null') {
            lines.push(`${key}=${value}`);
        }
    }
    
    return lines.join('\n') + '\n';
}

// Error handling
app.use((error, req, res, next) => {
    log(`❌ Server error: ${error.message}`);
    console.error(error.stack);
    res.status(500).json({
        status: 'error',
        message: 'Internal server error'
    });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
    log(`🎯 Webhook deployment server started on port ${PORT}`);
    log(`📂 Project directory: ${PROJECT_DIR}`);
    log(`📋 Log file: ${LOG_FILE}`);
    log('🔗 Endpoints:');
    log(`  - Health: http://localhost:${PORT}/health`);
    log(`  - Deploy: POST http://localhost:${PORT}/deploy`);
});

// Graceful shutdown
process.on('SIGINT', () => {
    log('📴 Shutting down webhook server...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    log('📴 Shutting down webhook server...');
    process.exit(0);
});