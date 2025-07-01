"""
Multi-layer content filtering system for Mahjong AI Tutor
Uses Groq models for cost-effective safety and relevance checking
"""

import time
import json
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from groq import Groq
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class FilterResult:
    """Result of content filtering"""
    allowed: bool
    reason: str
    confidence: float
    filter_stage: str
    tokens_used: int = 0

@dataclass
class IPReputation:
    """IP address reputation tracking"""
    bad_requests: int = 0
    total_requests: int = 0
    first_seen: datetime = None
    last_violation: datetime = None
    blacklisted: bool = False
    blacklist_reason: str = ""

class ContentFilter:
    """Multi-stage content filtering with IP reputation tracking"""
    
    def __init__(self, groq_api_key: str, blacklist_threshold: int = 5):
        self.groq_client = Groq(api_key=groq_api_key)
        self.blacklist_threshold = blacklist_threshold
        
        # IP reputation tracking
        self.ip_reputations: Dict[str, IPReputation] = {}
        self.request_history = defaultdict(deque)  # IP -> deque of timestamps
        
        # Models for different stages
        self.safety_model = "meta-llama/llama-prompt-guard-2-22m"
        self.relevance_model = "llama-3.1-8b-instant"
        
        logger.info(f"Content filter initialized with blacklist threshold: {blacklist_threshold}")
    
    def is_ip_blacklisted(self, client_ip: str) -> bool:
        """Check if IP is blacklisted"""
        if client_ip in self.ip_reputations:
            return self.ip_reputations[client_ip].blacklisted
        return False
    
    def track_request(self, client_ip: str, is_violation: bool = False):
        """Track request and update IP reputation"""
        now = datetime.now()
        
        # Initialize IP reputation if new
        if client_ip not in self.ip_reputations:
            self.ip_reputations[client_ip] = IPReputation(first_seen=now)
        
        rep = self.ip_reputations[client_ip]
        rep.total_requests += 1
        
        if is_violation:
            rep.bad_requests += 1
            rep.last_violation = now
            
            # Check if should be blacklisted
            if rep.bad_requests >= self.blacklist_threshold and not rep.blacklisted:
                rep.blacklisted = True
                rep.blacklist_reason = f"Exceeded {self.blacklist_threshold} violations"
                logger.warning(f"IP {client_ip} blacklisted: {rep.bad_requests} violations")
        
        # Track request timestamps for rate analysis
        self.request_history[client_ip].append(now)
        
        # Keep only last 24 hours of history
        cutoff = now - timedelta(hours=24)
        while (self.request_history[client_ip] and 
               self.request_history[client_ip][0] < cutoff):
            self.request_history[client_ip].popleft()
    
    def check_safety(self, message: str) -> FilterResult:
        """Stage 1: Safety check using llama-prompt-guard"""
        try:
            # Prompt guard expects specific format
            safety_prompt = f"""Is the following message safe and appropriate? Answer with just "SAFE" or "UNSAFE":

Message: {message}"""
            
            response = self.groq_client.chat.completions.create(
                model=self.safety_model,
                messages=[{"role": "user", "content": safety_prompt}],
                max_tokens=10,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip().upper()
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            is_safe = "SAFE" in result
            confidence = 0.9 if "SAFE" in result or "UNSAFE" in result else 0.5
            
            return FilterResult(
                allowed=is_safe,
                reason="Safety check failed" if not is_safe else "Passed safety check",
                confidence=confidence,
                filter_stage="safety",
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            # Fail closed - if safety check fails, block the request
            return FilterResult(
                allowed=False,
                reason=f"Safety check error: {str(e)}",
                confidence=0.0,
                filter_stage="safety",
                tokens_used=0
            )
    
    def check_mahjong_relevance(self, message: str) -> FilterResult:
        """Stage 2: Mahjong relevance check using llama-3.1-8b-instant"""
        try:
            relevance_prompt = f"""You are a content moderator for a Mahjong tutoring website. Determine if this message is related to Mahjong (the tile-based game) or requesting help with Mahjong strategy, rules, or gameplay.

Answer with just "RELEVANT" if the message is about Mahjong, or "IRRELEVANT" if it's about something else.

Message: {message}"""

            response = self.groq_client.chat.completions.create(
                model=self.relevance_model,
                messages=[{"role": "user", "content": relevance_prompt}],
                max_tokens=20,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip().upper()
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            is_relevant = "RELEVANT" in result
            confidence = 0.9 if "RELEVANT" in result or "IRRELEVANT" in result else 0.5
            
            return FilterResult(
                allowed=is_relevant,
                reason="Not Mahjong-related" if not is_relevant else "Mahjong-related content",
                confidence=confidence,
                filter_stage="relevance",
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"Relevance check failed: {e}")
            # Fail open for relevance - if check fails, allow through
            return FilterResult(
                allowed=True,
                reason=f"Relevance check error (allowed): {str(e)}",
                confidence=0.0,
                filter_stage="relevance",
                tokens_used=0
            )
    
    def filter_content(self, message: str, client_ip: str) -> Tuple[bool, FilterResult]:
        """
        Main filtering pipeline
        Returns: (allowed, filter_result)
        """
        # Check if IP is blacklisted first
        if self.is_ip_blacklisted(client_ip):
            logger.info(f"Blocked request from blacklisted IP: {client_ip}")
            return False, FilterResult(
                allowed=False,
                reason="IP blacklisted",
                confidence=1.0,
                filter_stage="blacklist",
                tokens_used=0
            )
        
        # Stage 1: Safety check
        safety_result = self.check_safety(message)
        if not safety_result.allowed:
            self.track_request(client_ip, is_violation=True)
            logger.warning(f"Safety violation from {client_ip}: {safety_result.reason}")
            return False, safety_result
        
        # Stage 2: Mahjong relevance check
        relevance_result = self.check_mahjong_relevance(message)
        if not relevance_result.allowed:
            self.track_request(client_ip, is_violation=True)
            logger.info(f"Irrelevant content from {client_ip}: {message[:50]}...")
            return False, relevance_result
        
        # All checks passed
        self.track_request(client_ip, is_violation=False)
        
        # Combine token usage
        total_tokens = safety_result.tokens_used + relevance_result.tokens_used
        
        return True, FilterResult(
            allowed=True,
            reason="Passed all content filters",
            confidence=min(safety_result.confidence, relevance_result.confidence),
            filter_stage="complete",
            tokens_used=total_tokens
        )
    
    def get_ip_stats(self, client_ip: str) -> Dict:
        """Get statistics for an IP address"""
        if client_ip not in self.ip_reputations:
            return {"status": "new", "requests": 0, "violations": 0}
        
        rep = self.ip_reputations[client_ip]
        return {
            "status": "blacklisted" if rep.blacklisted else "active",
            "total_requests": rep.total_requests,
            "bad_requests": rep.bad_requests,
            "violation_rate": rep.bad_requests / rep.total_requests if rep.total_requests > 0 else 0,
            "first_seen": rep.first_seen.isoformat() if rep.first_seen else None,
            "last_violation": rep.last_violation.isoformat() if rep.last_violation else None,
            "blacklisted": rep.blacklisted,
            "blacklist_reason": rep.blacklist_reason
        }
    
    def get_system_stats(self) -> Dict:
        """Get overall system statistics"""
        total_ips = len(self.ip_reputations)
        blacklisted_ips = sum(1 for rep in self.ip_reputations.values() if rep.blacklisted)
        total_requests = sum(rep.total_requests for rep in self.ip_reputations.values())
        total_violations = sum(rep.bad_requests for rep in self.ip_reputations.values())
        
        return {
            "total_ips_tracked": total_ips,
            "blacklisted_ips": blacklisted_ips,
            "total_requests": total_requests,
            "total_violations": total_violations,
            "violation_rate": total_violations / total_requests if total_requests > 0 else 0,
            "blacklist_threshold": self.blacklist_threshold
        }
    
    def export_blacklist(self) -> Dict[str, Dict]:
        """Export current blacklist for backup/analysis"""
        return {
            ip: asdict(rep) for ip, rep in self.ip_reputations.items() 
            if rep.blacklisted
        }
    
    def manually_blacklist_ip(self, client_ip: str, reason: str = "Manual blacklist"):
        """Manually add IP to blacklist"""
        if client_ip not in self.ip_reputations:
            self.ip_reputations[client_ip] = IPReputation(first_seen=datetime.now())
        
        rep = self.ip_reputations[client_ip]
        rep.blacklisted = True
        rep.blacklist_reason = reason
        logger.warning(f"Manually blacklisted IP {client_ip}: {reason}")
    
    def unblacklist_ip(self, client_ip: str, reason: str = "Manual unblacklist"):
        """Remove IP from blacklist"""
        if client_ip in self.ip_reputations:
            rep = self.ip_reputations[client_ip]
            rep.blacklisted = False
            rep.blacklist_reason = f"Unblacklisted: {reason}"
            logger.info(f"Unblacklisted IP {client_ip}: {reason}")

# Global content filter instance (will be initialized in main.py)
content_filter: Optional[ContentFilter] = None

def get_content_filter() -> ContentFilter:
    """Get the global content filter instance"""
    if content_filter is None:
        raise RuntimeError("Content filter not initialized")
    return content_filter