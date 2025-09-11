#!/usr/bin/env python3
"""
Check server logs for callback and background task issues
"""

import subprocess
import sys
import time

def run_ssh_command(command, description):
    """Run SSH command and return output"""
    print(f"\n📋 {description}")
    print("=" * 60)
    
    ssh_cmd = [
        "ssh", 
        "skl@192.168.0.234", 
        "-p", "6789",
        command
    ]
    
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"❌ Error (exit code {result.returncode}):")
            print(result.stderr)
    
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out")
    except Exception as e:
        print(f"❌ SSH Error: {e}")

def main():
    """Check various logs and services"""
    
    print("🔍 Checking Server Logs and Services")
    print("Server: skl@192.168.0.234:6789")
    print("=" * 60)
    
    # Check Docker containers status
    run_ssh_command(
        "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
        "Docker Containers Status"
    )
    
    # Check API container logs (recent)
    run_ssh_command(
        "docker logs --tail 50 magic-transcode-media-api-1 2>&1 | grep -E '(callback|background|error|ERROR|INFO)' || docker logs --tail 50 magic-transcode-media-api-1",
        "API Container Logs (Recent)"
    )
    
    # Check background task logs
    run_ssh_command(
        "docker logs --tail 30 magic-transcode-media-api-1 2>&1 | grep -i background || echo 'No background task logs found'",
        "Background Task Logs"
    )
    
    # Check callback logs
    run_ssh_command(
        "docker logs --tail 30 magic-transcode-media-api-1 2>&1 | grep -i callback || echo 'No callback logs found'",
        "Callback Logs"
    )
    
    # Check PubSub subscriber logs
    run_ssh_command(
        "docker logs --tail 30 magic-transcode-media-api-1 2>&1 | grep -E '(pubsub|subscribe|message)' || echo 'No PubSub logs found'",
        "PubSub Subscriber Logs"
    )
    
    # Check container resource usage
    run_ssh_command(
        "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'",
        "Container Resource Usage"
    )
    
    # Check if background tasks are running in API container
    run_ssh_command(
        "docker exec magic-transcode-media-api-1 ps aux | grep -E '(background|callback)' || echo 'No background processes found'",
        "Background Processes in API Container"
    )
    
    # Check API health
    run_ssh_command(
        "curl -s http://localhost:8087/health | head -5 || echo 'API health check failed'",
        "API Health Check"
    )
    
    # Check recent error logs
    run_ssh_command(
        "docker logs --since 1h magic-transcode-media-api-1 2>&1 | grep -i error | tail -10 || echo 'No recent errors found'",
        "Recent Error Logs (Last 1 hour)"
    )

if __name__ == "__main__":
    main()