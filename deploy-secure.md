# Secure Deployment Guide

## Overview
This is the security-hardened version of the Mahjong AI Tutor designed for production deployment on GPU servers.

## Security Features

### 🛡️ Request Filtering
- **Malicious Path Detection**: Blocks common attack patterns
  - Admin/RDP attempts (`/admin`, `/rdp`, `/mstsc`)
  - Wiki/CMS exploits (`/wiki`, `/wp-admin`, `/phpMyAdmin`)
  - Config file access (`/.env`, `/config.php`)
  - Directory traversal (`../`, `%2e%2e`)
  - Script injection attempts
  - SQL injection patterns
  - File inclusion attacks

### ⚡ Rate Limiting
- **Per-IP Limits**: 20 requests per minute per IP
- **Sliding Window**: 60-second rolling window
- **Automatic Cleanup**: Old requests removed automatically

### 📊 Security Logging
- **Attack Detection**: Logs all blocked requests
- **Performance Monitoring**: Tracks slow requests
- **IP Tracking**: Monitors client behavior
- **Suspicious Activity**: Alerts on borderline requests

## Deployment Steps

### 1. Server Setup
```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx

# Create application user
sudo useradd -r -s /bin/false mahjong-ai
sudo mkdir -p /opt/mahjong-ai
sudo chown mahjong-ai:mahjong-ai /opt/mahjong-ai
```

### 2. Install Ollama with GPU Support
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
sudo systemctl enable ollama
sudo systemctl start ollama

# Download model
ollama pull minicpm-v:latest
```

### 3. Deploy Application
```bash
# Clone repository
cd /opt/mahjong-ai
sudo -u mahjong-ai git clone https://github.com/carlosatFroom/mahjong_alex.git .
sudo -u mahjong-ai git checkout secmain

# Setup virtual environment
sudo -u mahjong-ai python3 -m venv venv
sudo -u mahjong-ai ./venv/bin/pip install -r requirements-secure.txt
```

### 4. Configure Nginx Reverse Proxy
```nginx
# /etc/nginx/sites-available/mahjong-ai
server {
    listen 80;
    server_name your-domain.com;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Hide nginx version
    server_tokens off;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/m;
    
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Block common attack paths at nginx level
    location ~* \.(env|git|svn|htaccess|htpasswd)$ {
        deny all;
        return 404;
    }
    
    location ~* /(admin|wp-admin|phpmyadmin|config) {
        deny all;
        return 404;
    }
}
```

### 5. Create Systemd Service
```ini
# /etc/systemd/system/mahjong-ai.service
[Unit]
Description=Mahjong AI Tutor
After=network.target

[Service]
Type=simple
User=mahjong-ai
Group=mahjong-ai
WorkingDirectory=/opt/mahjong-ai
Environment=PATH=/opt/mahjong-ai/venv/bin
ExecStart=/opt/mahjong-ai/venv/bin/python main.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/mahjong-ai

[Install]
WantedBy=multi-user.target
```

### 6. Start Services
```bash
# Enable and start services
sudo systemctl enable mahjong-ai
sudo systemctl start mahjong-ai
sudo systemctl enable nginx
sudo systemctl start nginx

# Check status
sudo systemctl status mahjong-ai
sudo systemctl status nginx
```

## Security Configuration

### Environment Variables
```bash
# /opt/mahjong-ai/.env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
OLLAMA_HOST=10.9.1.44
OLLAMA_PORT=11434
OLLAMA_MODEL=minicpm-v:latest
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://10.9.1.44:8000,http://localhost:8000
MAX_REQUESTS_PER_MINUTE=20
RATE_LIMIT_WINDOW=60
```

### Configure Ollama for Network Access
```bash
# Stop Ollama service
sudo systemctl stop ollama

# Configure Ollama to listen on all interfaces
sudo systemctl edit ollama

# Add this content to the override file:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl start ollama

# Verify Ollama is listening on all interfaces
sudo netstat -tlnp | grep 11434
```

### Firewall Rules
```bash
# Basic firewall setup
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # Block direct access to app
```

## Monitoring

### Log Files
- **Application**: `/opt/mahjong-ai/logs/app.log`
- **Security**: `/opt/mahjong-ai/logs/security.log`
- **Nginx**: `/var/log/nginx/access.log`

### Security Monitoring
```bash
# Monitor blocked requests
sudo tail -f /var/log/nginx/access.log | grep " 404 "

# Monitor rate limiting
sudo tail -f /var/log/nginx/error.log | grep "limiting requests"

# Application security logs
sudo tail -f /opt/mahjong-ai/logs/security.log
```

## Performance Optimization

### GPU Configuration
```bash
# Check GPU availability
nvidia-smi

# Monitor GPU usage
watch -n 1 nvidia-smi
```

### Ollama Optimization
```bash
# Set GPU memory limit (optional)
export OLLAMA_GPU_MEMORY_LIMIT=8GB

# Enable GPU acceleration
export OLLAMA_GPU=1
```

## Backup and Recovery

### Backup Script
```bash
#!/bin/bash
# /opt/mahjong-ai/backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/mahjong-ai"

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/mahjong-ai_$DATE.tar.gz \
    --exclude=venv \
    --exclude=__pycache__ \
    /opt/mahjong-ai
```

## Troubleshooting

### Common Issues
1. **High CPU Usage**: Check for attack patterns in logs
2. **Memory Leaks**: Monitor rate limiter cleanup
3. **Slow Responses**: Check GPU utilization
4. **Blocked Legitimate Requests**: Review security patterns

### Debug Commands
```bash
# Check application logs
sudo journalctl -u mahjong-ai -f

# Test security filtering
curl -v http://localhost:8000/admin
curl -v http://localhost:8000/wp-admin

# Monitor performance
top -p $(pgrep -f "python main.py")
```