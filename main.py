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

# Ollama configuration from config
OLLAMA_BASE_URL = config.ollama_base_url
OLLAMA_MODEL = config.OLLAMA_MODEL

# Mahjong tutor system prompt
MAHJONG_SYSTEM_PROMPT = """You are an expert Mahjong tutor with deep knowledge of strategy, tile reading, and game theory. 
Your role is to analyze Mahjong game states and provide strategic advice to help players improve.

When analyzing images:
1. Identify all visible tiles and their suits (dots, bamboo, characters, honors)
2. Assess the current hand composition and potential winning patterns
3. Evaluate discarded tiles and what they reveal about opponents
4. Suggest optimal moves with clear reasoning
5. Explain strategic concepts to help the player learn

Always be encouraging and educational. Focus on the 'why' behind your recommendations.
If you cannot clearly see the tiles, ask for a clearer image or describe what you need to see better."""

class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        
    def chat(self, message: str, image_data: Optional[str] = None, model: str = OLLAMA_MODEL):
        """Send a chat message to Ollama, optionally with an image."""
        url = f"{self.base_url}/api/chat"
        
        messages = [
            {
                "role": "system",
                "content": MAHJONG_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": message
            }
        ]
        
        # Add image if provided
        if image_data:
            messages[-1]["images"] = [image_data]
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        # Track timing
        start_time = time.time()
        first_token_time = None
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            first_token_time = time.time()
            response.raise_for_status()
            
            end_time = time.time()
            response_data = response.json()
            
            # Add timing and token information
            response_data["performance"] = {
                "total_time": round(end_time - start_time, 2),
                "time_to_first_token": round(first_token_time - start_time, 2),
                "prompt_eval_count": response_data.get("prompt_eval_count", 0),
                "eval_count": response_data.get("eval_count", 0),
                "total_tokens": response_data.get("prompt_eval_count", 0) + response_data.get("eval_count", 0)
            }
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Ollama API error: {str(e)}")
    
    def list_models(self):
        """List available models in Ollama."""
        url = f"{self.base_url}/api/tags"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

ollama_client = OllamaClient()

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
    """Get available Ollama models."""
    return ollama_client.list_models()

@app.post("/api/chat")
async def chat_with_ai(
    message: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    """Chat with the Mahjong AI tutor."""
    image_data = None
    
    if image:
        # Validate image type
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and encode image
        image_bytes = await image.read()
        image_data = base64.b64encode(image_bytes).decode('utf-8')
    
    # Send to Ollama
    response = ollama_client.chat(message, image_data)
    
    return {
        "response": response.get("message", {}).get("content", ""),
        "model": response.get("model", ""),
        "has_image": image_data is not None,
        "performance": response.get("performance", {})
    }

@app.get("/api/health")
async def health_check():
    """Check if Ollama is running and responsive."""
    try:
        models = ollama_client.list_models()
        return {
            "status": "healthy",
            "ollama_url": OLLAMA_BASE_URL,
            "available_models": len(models.get("models", []))
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "ollama_url": OLLAMA_BASE_URL
        }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Mahjong AI Tutor with security middleware")
    logger.info(f"Ollama configured at: {OLLAMA_BASE_URL}")
    logger.info(f"Using model: {OLLAMA_MODEL}")
    
    # Production configuration
    uvicorn.run(
        app, 
        host=config.SERVER_HOST, 
        port=config.SERVER_PORT,
        log_level=config.LOG_LEVEL.lower(),
        access_log=True
    )