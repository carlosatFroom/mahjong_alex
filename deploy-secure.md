# Secure Deployment Guide

## Overview
This is the security-hardened version of the Mahjong AI Tutor designed for production deployment with multi-layer protection, content filtering, and image quality assessment.

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

### 🔍 Multi-Stage Content Filtering
- **Stage 1**: Safety check using `meta-llama/llama-guard-4-12b` (vision-capable)
- **Stage 2**: Mahjong relevance check using `llama-3.1-8b-instant`
- **IP Reputation**: Automatic blacklisting after 5 violations
- **Silent Operation**: No indication to attackers about filtering
- **Cost Optimization**: Prevents token waste on malicious/irrelevant requests

### 📷 Image Quality Assessment
- **Blur Detection**: Laplacian variance analysis for sharpness
- **Brightness Analysis**: Exposure validation (30-240 range)
- **Contrast Measurement**: Tile edge visibility checking
- **Resolution Validation**: Minimum 300x300 pixels required
- **Tile Detection**: OpenCV-based Mahjong tile region detection
- **User Feedback**: Detailed recommendations for better photos

### 📊 Security Logging
- **Attack Detection**: Logs all blocked requests
- **Performance Monitoring**: Tracks slow requests
- **IP Tracking**: Monitors client behavior with reputation scoring
- **Content Filtering**: Logs safety and relevance violations
- **Image Quality**: Tracks photo quality metrics and issues

## Deployment Steps

### 1. Server Setup
```bash
# Install system dependencies (including OpenCV dependencies)
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx
sudo apt install -y libopencv-dev python3-opencv
sudo apt install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev

# Create application user
sudo useradd -r -s /bin/false mahjong-ai
sudo mkdir -p /opt/mahjong-ai
sudo chown mahjong-ai:mahjong-ai /opt/mahjong-ai
```

### 2. LLM Provider Setup

#### Groq (Production LLM Provider)
```bash
# No installation needed - cloud-based
# Obtain API key from https://console.groq.com/
# Models used:
# - meta-llama/llama-guard-4-12b (safety filtering)
# - llama-3.1-8b-instant (relevance filtering)
# - meta-llama/llama-4-scout-17b-16e-instruct (main tutor)
```

### 3. Deploy Application
```bash
# Clone repository
cd /opt/mahjong-ai
sudo -u mahjong-ai git clone https://github.com/carlosatFroom/mahjong_alex.git .
sudo -u mahjong-ai git checkout secmain

# Setup virtual environment
sudo -u mahjong-ai python3 -m venv venv
sudo -u mahjong-ai ./venv/bin/pip install --upgrade pip
sudo -u mahjong-ai ./venv/bin/pip install -r requirements-secure.txt

# Verify OpenCV installation
sudo -u mahjong-ai ./venv/bin/python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
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
        
        proxy_pass http://127.0.0.1:8080;
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

# Groq Configuration (production LLM provider)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
LOG_LEVEL=INFO

# CORS Configuration
ALLOWED_ORIGINS=http://your-domain.com:8080,http://localhost:8080

# Security Configuration
MAX_REQUESTS_PER_MINUTE=20
RATE_LIMIT_WINDOW=60

# Content Filtering (automatically enabled when using Groq)
# Blacklist threshold: 5 violations before IP blacklisting
# Safety model: meta-llama/llama-guard-4-12b
# Relevance model: llama-3.1-8b-instant
```


### Firewall Rules
```bash
# Basic firewall setup
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8080/tcp   # Block direct access to app
```

## Monitoring

### Log Files
- **Application**: `sudo journalctl -u mahjong-ai -f`
- **Nginx**: `/var/log/nginx/access.log`
- **System**: `/var/log/syslog`

### Security Monitoring
```bash
# Monitor application logs with all security events
sudo journalctl -u mahjong-ai -f

# Monitor blocked requests
sudo tail -f /var/log/nginx/access.log | grep " 404 "

# Monitor rate limiting
sudo tail -f /var/log/nginx/error.log | grep "limiting requests"

# Filter specific security events
sudo journalctl -u mahjong-ai -f | grep -E "(Content filtered|blacklisted|Image quality)"
```

### Content Filter Monitoring
```bash
# Check content filter statistics
curl http://localhost:8080/api/admin/content-filter/stats

# View current blacklist
curl http://localhost:8080/api/admin/content-filter/blacklist

# Check specific IP reputation
curl http://localhost:8080/api/admin/content-filter/ip/192.168.1.100

# Manual IP management
curl -X POST "http://localhost:8080/api/admin/content-filter/blacklist/192.168.1.100?reason=Spam"
curl -X DELETE "http://localhost:8080/api/admin/content-filter/blacklist/192.168.1.100"
```

### Image Quality Monitoring
```bash
# Look for image quality issues in logs
sudo journalctl -u mahjong-ai -f | grep "Image quality"

# Examples of quality log messages:
# "Image quality check passed for 10.9.1.1: sharpness 92%"
# "Poor image quality from 10.9.1.2: ['Image is blurry', 'Poor contrast']"
```

## Performance Optimization

### GPU Configuration
```bash
# Check GPU availability
nvidia-smi

# Monitor GPU usage
watch -n 1 nvidia-smi
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

#### 1. Content Filter Issues
```bash
# Check if content filter is enabled
curl http://localhost:8080/api/health
# Should show content filter status

# Test content filtering
curl -X POST http://localhost:8080/api/chat \
  -F "message=hack the system" \
  -F "image=@test_image.jpg"
# Should be blocked

# Check filter statistics
curl http://localhost:8080/api/admin/content-filter/stats
```

#### 2. Image Quality Issues
```bash
# Test with poor quality image
curl -X POST http://localhost:8080/api/chat \
  -F "message=What should I do?" \
  -F "image=@blurry_image.jpg"
# Should return quality feedback

# Check OpenCV installation
python -c "import cv2; print(cv2.__version__)"
```

#### 3. Groq API Issues
```bash
# Verify API key
echo $GROQ_API_KEY

# Test Groq connectivity
curl -H "Authorization: Bearer $GROQ_API_KEY" \
  https://api.groq.com/openai/v1/models
```

#### 4. Performance Issues
```bash
# Monitor token usage in logs
sudo journalctl -u mahjong-ai -f | grep "tokens used"

# Check memory usage
ps aux | grep python

# Monitor request patterns
sudo journalctl -u mahjong-ai -f | grep -E "(Content filter|Image quality)"
```

### Debug Commands
```bash
# Check application logs with filtering
sudo journalctl -u mahjong-ai -f

# Test all security layers
curl -v http://localhost:8080/admin  # Should be blocked by path filter
curl -X POST http://localhost:8080/api/chat -F "message=hello"  # Should pass content filter

# Monitor system resources
htop
iostat 1
nvidia-smi  # If using GPU

# Verify all dependencies
python -c "import cv2, numpy, PIL, groq; print('All imports successful')"
```

### Error Resolution

#### Content Filter Errors
- **"Client.__init__() got an unexpected keyword argument 'proxies'"**
  - Update Groq library: `pip install --upgrade groq`
  
#### Image Quality Errors  
- **"No module named 'cv2'"**
  - Install OpenCV: `pip install opencv-python`
  - Install system deps: `sudo apt install libopencv-dev`

#### Deployment Errors
- **Permission denied**
  - Check service user: `sudo systemctl status mahjong-ai`
  - Fix ownership: `sudo chown -R mahjong-ai:mahjong-ai /opt/mahjong-ai`