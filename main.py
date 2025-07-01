from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
import json
from typing import Optional
import os
import time
import logging
from security import security_middleware
from config import config
from llm_providers import get_llm_provider
from content_filter import ContentFilter, get_content_filter

app = FastAPI(title="Mahjong AI Tutor", version="1.0.0")

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add security middleware
app.middleware("http")(security_middleware)

# CORS middleware for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize content filter
content_filter_instance = None
if config.LLM_PROVIDER.lower() == "groq" and config.GROQ_API_KEY:
    content_filter_instance = ContentFilter(
        groq_api_key=config.GROQ_API_KEY,
        blacklist_threshold=5
    )

# Initialize LLM provider based on configuration
def get_current_llm_provider():
    """Get the configured LLM provider"""
    if config.LLM_PROVIDER.lower() == "groq":
        return get_llm_provider(
            "groq",
            api_key=config.GROQ_API_KEY,
            model=config.GROQ_MODEL
        )
    else:
        return get_llm_provider(
            "ollama",
            base_url=config.ollama_base_url,
            model=config.OLLAMA_MODEL
        )

# For backwards compatibility with Ollama-specific endpoints
class OllamaCompat:
    """Compatibility layer for Ollama-specific functionality"""
    def __init__(self):
        self.base_url = config.ollama_base_url
    
    def list_models(self):
        """List available models in Ollama."""
        url = f"{self.base_url}/api/tags"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

ollama_compat = OllamaCompat()

@app.get("/")
async def read_root():
    """Serve the main HTML page."""
    return HTMLResponse(content=open("index.html").read())

@app.get("/favicon.ico")
async def favicon():
    """Return empty response for favicon requests."""
    return ""

@app.get("/api/models")
async def get_models():
    """Get available models."""
    if config.LLM_PROVIDER.lower() == "groq":
        # Return Groq models info
        return {
            "models": [
                {"name": config.GROQ_MODEL, "provider": "groq"},
                {"name": "meta-llama/llama-4-scout-17b-16e-instruct", "provider": "groq"},
                {"name": "llama-3.3-70b-versatile", "provider": "groq"}
            ]
        }
    else:
        return ollama_compat.list_models()

@app.post("/api/chat")
async def chat_with_ai(
    request: Request,
    message: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    """Chat with the Mahjong AI tutor."""
    # Get client IP for content filtering
    client_ip = request.client.host if request.client else "unknown"
    
    # Content filtering (if enabled)
    if content_filter_instance:
        try:
            allowed, filter_result = content_filter_instance.filter_content(message, client_ip)
            
            if not allowed:
                # Log the violation but don't reveal filtering to user
                logger.warning(f"Content filtered from {client_ip}: {filter_result.reason}")
                
                # Return generic error for blacklisted IPs (don't reveal blacklist)
                if filter_result.filter_stage == "blacklist":
                    raise HTTPException(status_code=503, detail="Service temporarily unavailable")
                
                # For other violations, return a helpful message
                if filter_result.filter_stage == "safety":
                    raise HTTPException(status_code=400, detail="Please ensure your message is appropriate and follows community guidelines")
                elif filter_result.filter_stage == "relevance":
                    raise HTTPException(status_code=400, detail="This service is specifically for Mahjong-related questions. Please ask about Mahjong strategy, rules, or gameplay")
                else:
                    raise HTTPException(status_code=400, detail="Unable to process your request")
            
            # Log successful filter with token usage
            logger.info(f"Content filter passed for {client_ip}: {filter_result.tokens_used} tokens used")
            
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logger.error(f"Content filter error: {e}")
            # If content filter fails, allow through but log the error
            pass
    
    image_data = None
    
    if image:
        # Validate image type
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and encode image
        image_bytes = await image.read()
        image_data = base64.b64encode(image_bytes).decode('utf-8')
    
    # Send to configured LLM provider
    try:
        llm_provider = get_current_llm_provider()
        response = llm_provider.chat(message, image_data)
        
        return {
            "response": response.get("message", {}).get("content", ""),
            "model": response.get("model", ""),
            "has_image": image_data is not None,
            "performance": response.get("performance", {})
        }
    except Exception as e:
        logger.error(f"LLM provider error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM provider error: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Check if the configured LLM provider is responsive."""
    try:
        if config.LLM_PROVIDER.lower() == "groq":
            # Test Groq connection
            if not config.GROQ_API_KEY:
                return {
                    "status": "unhealthy",
                    "error": "Groq API key not configured",
                    "provider": "groq"
                }
            
            llm_provider = get_current_llm_provider()
            # Simple test message
            test_response = llm_provider.chat("Hello")
            
            return {
                "status": "healthy",
                "provider": "groq",
                "model": config.GROQ_MODEL,
                "test_response_length": len(test_response.get("message", {}).get("content", ""))
            }
        else:
            # Test Ollama connection
            models = ollama_compat.list_models()
            return {
                "status": "healthy",
                "provider": "ollama", 
                "ollama_url": config.ollama_base_url,
                "available_models": len(models.get("models", []))
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "provider": config.LLM_PROVIDER,
            "config_url": config.ollama_base_url if config.LLM_PROVIDER == "ollama" else "groq_api"
        }

@app.get("/api/admin/content-filter/stats")
async def get_content_filter_stats():
    """Get content filter statistics (admin endpoint)"""
    if not content_filter_instance:
        return {"error": "Content filter not enabled"}
    
    return content_filter_instance.get_system_stats()

@app.get("/api/admin/content-filter/ip/{ip}")
async def get_ip_stats(ip: str):
    """Get statistics for a specific IP address (admin endpoint)"""
    if not content_filter_instance:
        return {"error": "Content filter not enabled"}
    
    return content_filter_instance.get_ip_stats(ip)

@app.get("/api/admin/content-filter/blacklist")
async def get_blacklist():
    """Get current blacklist (admin endpoint)"""
    if not content_filter_instance:
        return {"error": "Content filter not enabled"}
    
    return content_filter_instance.export_blacklist()

@app.post("/api/admin/content-filter/blacklist/{ip}")
async def manual_blacklist_ip(ip: str, reason: str = "Manual admin action"):
    """Manually blacklist an IP address (admin endpoint)"""
    if not content_filter_instance:
        return {"error": "Content filter not enabled"}
    
    content_filter_instance.manually_blacklist_ip(ip, reason)
    return {"message": f"IP {ip} blacklisted", "reason": reason}

@app.delete("/api/admin/content-filter/blacklist/{ip}")
async def unblacklist_ip(ip: str, reason: str = "Manual admin removal"):
    """Remove IP from blacklist (admin endpoint)"""
    if not content_filter_instance:
        return {"error": "Content filter not enabled"}
    
    content_filter_instance.unblacklist_ip(ip, reason)
    return {"message": f"IP {ip} removed from blacklist", "reason": reason}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Mahjong AI Tutor with security middleware")
    logger.info(f"LLM Provider: {config.LLM_PROVIDER}")
    logger.info(f"Environment LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'NOT_SET')}")
    
    if config.LLM_PROVIDER.lower() == "groq":
        logger.info(f"Groq Model: {config.GROQ_MODEL}")
        logger.info(f"API Key configured: {'Yes' if config.GROQ_API_KEY else 'No'}")
        if config.GROQ_API_KEY:
            logger.info(f"API Key starts with: {config.GROQ_API_KEY[:10]}...")
    else:
        logger.info(f"Ollama configured at: {config.ollama_base_url}")
        logger.info(f"Ollama Model: {config.OLLAMA_MODEL}")
    
    # Content filter status
    if content_filter_instance:
        logger.info("Content filter enabled with multi-stage filtering")
        logger.info(f"Safety model: meta-llama/llama-prompt-guard-2-22m")
        logger.info(f"Relevance model: llama-3.1-8b-instant") 
        logger.info(f"Blacklist threshold: 5 violations")
    else:
        logger.warning("Content filter disabled - running without protection")
    
    # Production configuration
    uvicorn.run(
        app, 
        host=config.SERVER_HOST, 
        port=config.SERVER_PORT,
        log_level=config.LOG_LEVEL.lower(),
        access_log=True
    )