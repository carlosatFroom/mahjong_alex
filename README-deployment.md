# Mahjong Tutor - Deployment Guide

This guide explains how to deploy the Mahjong Tutor as a JavaScript widget that can be embedded in any website, with a Flask API backend.

## Architecture

- **Backend**: Flask API (`app.py`) with content filtering
- **Frontend**: JavaScript widget (`mahjong-tutor-widget.js`) for embedding
- **Content Filter**: Advanced filtering system to ensure Mahjong-only content

## Backend Deployment (Flask API)

### 1. Server Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GROQ_API_KEY="your-groq-api-key"
export FLASK_ENV="production"
export PORT=5000
```

### 2. Production Deployment

#### Option A: Using Gunicorn (Recommended)
```bash
# Install gunicorn (included in requirements.txt)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### Option B: Using systemd service
Create `/etc/systemd/system/mahjong-tutor.service`:

```ini
[Unit]
Description=Mahjong Tutor API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/your/app
Environment=GROQ_API_KEY=your-groq-api-key
Environment=FLASK_ENV=production
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mahjong-tutor
sudo systemctl start mahjong-tutor
```

#### Option C: Using Docker
Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:
```bash
docker build -t mahjong-tutor .
docker run -p 5000:5000 -e GROQ_API_KEY=your-key mahjong-tutor
```

### 3. Reverse Proxy Setup (Nginx)

Add to your Nginx configuration:

```nginx
server {
    listen 80;
    server_name your-api-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
        
        # Handle preflight requests
        if ($request_method = OPTIONS) {
            return 204;
        }
    }
}
```

### 4. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-api-domain.com
```

## Frontend Deployment (JavaScript Widget)

### 1. Update Configuration

Edit `mahjong-tutor-widget.js` line 12:

```javascript
const CONFIG = {
    apiUrl: 'https://your-api-domain.com/api',  // Replace with your API URL
    // ... other config
};
```

### 2. Host the Widget File

#### Option A: CDN (Recommended)
Upload `mahjong-tutor-widget.js` to your CDN and reference it:

```html
<script src="https://your-cdn.com/mahjong-tutor-widget.js"></script>
```

#### Option B: Self-hosted
Place the file on your web server and reference it:

```html
<script src="/path/to/mahjong-tutor-widget.js"></script>
```

### 3. Embedding Instructions

Provide these instructions to website owners:

#### Simple Installation
Add this single line to any webpage:

```html
<script src="https://your-cdn.com/mahjong-tutor-widget.js"></script>
```

#### Advanced Installation (Custom Configuration)
```html
<script>
    // Optional: Custom configuration
    window.mahjongTutorConfig = {
        apiUrl: 'https://your-api-domain.com/api',
        maxMessageLength: 1000,
        imageMaxSize: 5 * 1024 * 1024  // 5MB
    };
</script>
<script src="https://your-cdn.com/mahjong-tutor-widget.js"></script>
```

## API Endpoints

### Core Endpoints

- `GET /api/health` - Health check
- `POST /api/chat` - Main chat endpoint
- `GET /api/stats` - System statistics
- `GET /api/ip-stats/<ip>` - IP-specific statistics

### Request Format

```javascript
// POST /api/chat
{
    "message": "What tile should I discard?",
    "image": "base64-encoded-image-data"  // optional
}
```

### Response Format

```javascript
// Success response
{
    "response": "Based on your hand, I recommend...",
    "timestamp": "2024-01-01T12:00:00Z",
    "tokens_used": 150
}

// Error response
{
    "error": "Content not allowed",
    "reason": "Content not related to Mahjong gameplay",
    "filter_stage": "relevance"
}
```

## Security Features

### Content Filtering
- **Safety Check**: Blocks unsafe content using llama-guard-4-12b
- **Relevance Check**: Ensures only Mahjong-related content using llama-3.1-8b-instant
- **IP Reputation**: Tracks and blocks abusive IPs
- **Rate Limiting**: Built-in request tracking

### Security Headers
- CORS properly configured
- Content-Type validation
- Input sanitization
- Error message sanitization

## Monitoring

### Health Check
```bash
curl https://your-api-domain.com/api/health
```

### System Statistics
```bash
curl https://your-api-domain.com/api/stats
```

### Logs
Monitor application logs for:
- Content filtering violations
- API errors
- Performance metrics

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure `Flask-CORS` is installed
   - Check Nginx CORS headers
   - Verify API URL in widget configuration

2. **Content Filtering Too Strict**
   - Check filter prompts in `content_filter.py`
   - Monitor logs for unexpected responses
   - Adjust confidence thresholds if needed

3. **Widget Not Loading**
   - Check browser console for errors
   - Verify script URL is accessible
   - Ensure no CSP blocking the widget

4. **API Errors**
   - Check GROQ_API_KEY is set correctly
   - Monitor API rate limits
   - Verify network connectivity

### Testing

Test the widget locally:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Mahjong Tutor Test</title>
</head>
<body>
    <h1>Test Page</h1>
    <script src="mahjong-tutor-widget.js"></script>
</body>
</html>
```

## Performance Optimization

### Backend
- Use multiple Gunicorn workers
- Implement Redis caching for repeated queries
- Add database persistence for conversation history
- Monitor API response times

### Frontend
- Minify JavaScript file
- Use CDN for global distribution
- Implement conversation caching
- Optimize image compression

## Scaling

### For High Traffic
- Use load balancer with multiple API instances
- Implement Redis session storage
- Add request queuing system
- Monitor and scale based on API usage

### Database Integration
Consider adding PostgreSQL for:
- Conversation history storage
- User analytics
- Enhanced IP reputation tracking
- Content filtering statistics

## Support

For issues or questions:
- Check logs for error messages
- Review API response codes
- Test with curl for API debugging
- Verify widget console logs for frontend issues