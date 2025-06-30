"""
Security middleware for Mahjong AI Tutor
Filters malicious requests and implements rate limiting
"""

import re
import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suspicious path patterns commonly used in attacks
MALICIOUS_PATTERNS = [
    # Admin/RDP attempts
    r'/(admin|administrator|rdp|remote|desktop)',
    r'/mstsc',
    r'/(login|signin|auth)\.php',
    
    # Wiki/CMS attacks
    r'/(wiki|mediawiki|wordpress|wp-admin|wp-login)',
    r'/phpMyAdmin',
    r'/phpmyadmin',
    
    # Common exploit attempts
    r'/\.env',
    r'/config\.(php|json|yml|yaml)',
    r'/(backup|backups|dump|sql)',
    r'/\.(git|svn|hg)/',
    
    # Directory traversal
    r'\.\.',
    r'%2e%2e',
    r'//+',
    
    # Script injection attempts
    r'<script',
    r'javascript:',
    r'vbscript:',
    r'(eval|exec|system)\(',
    
    # SQL injection patterns
    r'(union|select|insert|update|delete|drop)\s+(all\s+)?(select|from|where)',
    r'(\||&|;|`|\$\()',
    
    # File inclusion attempts
    r'/(etc/passwd|proc/version|windows/system32)',
    r'\.(php|asp|jsp|py|pl|cgi)\?',
    
    # Bot/crawler attempts
    r'/(robots\.txt|sitemap\.xml)$',
    r'/\.(well-known|htaccess|htpasswd)',
    
    # Common vulnerability scanners
    r'/(wp-content|wp-includes|drupal|joomla)',
    r'/(cgi-bin|bin/sh|usr/bin)',
    
    # Network probes
    r'/(soap|xmlrpc|rpc2|rpc)',
    r'/(api/v[0-9]+/)?(user|users|admin|login|auth|token)',
]

# Compile regex patterns for better performance
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in MALICIOUS_PATTERNS]

# Rate limiting storage
class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        client_requests = self.requests[client_ip]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) >= self.max_requests:
            return False
        
        # Add current request
        client_requests.append(now)
        return True

# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request headers"""
    # Check for forwarded headers (when behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    return request.client.host if request.client else "unknown"

def is_malicious_request(path: str, user_agent: str = "", query_params: str = "") -> tuple[bool, str]:
    """
    Check if a request matches malicious patterns
    Returns (is_malicious, reason)
    """
    # Check path against malicious patterns
    for pattern in COMPILED_PATTERNS:
        if pattern.search(path):
            return True, f"Malicious path pattern detected: {path}"
    
    # Check query parameters
    if query_params:
        for pattern in COMPILED_PATTERNS:
            if pattern.search(query_params):
                return True, f"Malicious query parameter detected: {query_params}"
    
    # Check user agent for common bot signatures
    if user_agent:
        bot_patterns = [
            r'(sqlmap|nikto|nmap|masscan|zmap)',
            r'(gobuster|dirb|dirbuster|wfuzz)',
            r'(burp|owasp|zaproxy)',
            r'(python-requests/|curl/|wget/)',  # Basic automation
        ]
        
        for pattern in bot_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return True, f"Suspicious user agent: {user_agent}"
    
    return False, ""

async def security_middleware(request: Request, call_next):
    """
    Security middleware to filter malicious requests
    """
    start_time = time.time()
    client_ip = get_client_ip(request)
    path = str(request.url.path)
    query_params = str(request.url.query) if request.url.query else ""
    user_agent = request.headers.get("User-Agent", "")
    
    # Skip security checks for legitimate app endpoints
    if path in ["/", "/api/chat", "/api/health", "/api/models", "/favicon.ico"]:
        # Still apply rate limiting to legitimate endpoints
        if not rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Please try again later."}
            )
        
        response = await call_next(request)
        return response
    
    # Check for malicious patterns
    is_malicious, reason = is_malicious_request(path, user_agent, query_params)
    
    if is_malicious:
        logger.warning(f"Blocked malicious request from {client_ip}: {reason}")
        logger.info(f"Request details - Path: {path}, UA: {user_agent}, Query: {query_params}")
        
        # Return a generic 404 to not reveal we're filtering
        return JSONResponse(
            status_code=404,
            content={"error": "Not found"}
        )
    
    # Check rate limiting for all other requests
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for {client_ip} on path {path}")
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"}
        )
    
    # Log suspicious but not blocked requests
    if any(keyword in path.lower() for keyword in ['admin', 'login', 'config', 'api']):
        logger.info(f"Suspicious but allowed request from {client_ip}: {path}")
    
    response = await call_next(request)
    
    # Log response time for monitoring
    process_time = time.time() - start_time
    if process_time > 1.0:  # Log slow requests
        logger.info(f"Slow request: {path} took {process_time:.2f}s")
    
    return response

def log_security_stats():
    """Log security statistics (call periodically)"""
    total_ips = len(rate_limiter.requests)
    logger.info(f"Security stats - Tracked IPs: {total_ips}")