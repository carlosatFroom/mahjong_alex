"""
Security middleware for Mahjong AI Tutor
Filters malicious requests and implements rate limiting
"""

import re
import time
from collections import defaultdict, deque
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

def get_client_ip(request) -> str:
    """Extract client IP address from request headers"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.remote_addr or "unknown"

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

GAME_PATH_PREFIXES = ("/api/game", "/static/")
APP_PATHS = {"/", "/api/health", "/favicon.ico"}

# Gameplay sends one request per move, so it gets a higher budget than the coach.
game_rate_limiter = RateLimiter(max_requests=240, window_seconds=60)


def check_request(request):
    """Flask before_request hook. Returns a (body, status) tuple to block, or None to allow."""
    client_ip = get_client_ip(request)
    path = request.path

    if path in APP_PATHS or path.startswith(GAME_PATH_PREFIXES):
        is_coach = path.endswith("/coach")
        limiter = rate_limiter if is_coach else game_rate_limiter
        if not limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            return {"error": "Rate limit exceeded. Please try again later."}, 429
        return None

    is_malicious, reason = is_malicious_request(
        path, request.headers.get("User-Agent", ""), request.query_string.decode(errors="ignore")
    )
    if is_malicious:
        logger.warning(f"Blocked malicious request from {client_ip}: {reason}")
        return {"error": "Not found"}, 404

    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for {client_ip} on path {path}")
        return {"error": "Rate limit exceeded"}, 429
    return None

def log_security_stats():
    """Log security statistics (call periodically)"""
    total_ips = len(rate_limiter.requests)
    logger.info(f"Security stats - Tracked IPs: {total_ips}")