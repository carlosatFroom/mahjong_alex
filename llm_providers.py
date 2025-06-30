"""
LLM provider abstraction for Mahjong AI Tutor
Supports both Ollama and Groq for flexibility and performance
"""

import time
import base64
import requests
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from groq import Groq
import logging

logger = logging.getLogger(__name__)

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

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def chat(self, message: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Send a chat message, optionally with an image"""
        pass

class OllamaProvider(LLMProvider):
    """Ollama provider for local model inference"""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
    
    def chat(self, message: str, image_data: Optional[str] = None) -> Dict[str, Any]:
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
            "model": self.model,
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
                "total_tokens": response_data.get("prompt_eval_count", 0) + response_data.get("eval_count", 0),
                "provider": "ollama"
            }
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API error: {str(e)}")
            raise Exception(f"Ollama API error: {str(e)}")

class GroqProvider(LLMProvider):
    """Groq provider for fast cloud inference"""
    
    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model
    
    def chat(self, message: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Send a chat message to Groq, optionally with an image."""
        
        # Build messages for Groq format
        messages = [
            {
                "role": "system",
                "content": MAHJONG_SYSTEM_PROMPT
            }
        ]
        
        # Handle image + text or text only
        if image_data:
            # For vision models, combine image and text in user message
            user_content = [
                {
                    "type": "text",
                    "text": message
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}"
                    }
                }
            ]
            messages.append({
                "role": "user",
                "content": user_content
            })
        else:
            messages.append({
                "role": "user", 
                "content": message
            })
        
        # Track timing
        start_time = time.time()
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            end_time = time.time()
            
            # Extract response content
            response_content = completion.choices[0].message.content
            
            # Build response in Ollama-compatible format
            response_data = {
                "message": {
                    "content": response_content
                },
                "model": self.model,
                "performance": {
                    "total_time": round(end_time - start_time, 2),
                    "time_to_first_token": round(end_time - start_time, 2),  # Groq is very fast
                    "prompt_eval_count": completion.usage.prompt_tokens if completion.usage else 0,
                    "eval_count": completion.usage.completion_tokens if completion.usage else 0,
                    "total_tokens": completion.usage.total_tokens if completion.usage else 0,
                    "provider": "groq"
                }
            }
            
            return response_data
            
        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            raise Exception(f"Groq API error: {str(e)}")

def get_llm_provider(provider_type: str, **kwargs) -> LLMProvider:
    """Factory function to get the appropriate LLM provider"""
    
    if provider_type.lower() == "ollama":
        base_url = kwargs.get("base_url", "http://localhost:11434")
        model = kwargs.get("model", "minicpm-v:latest")
        return OllamaProvider(base_url, model)
    
    elif provider_type.lower() == "groq":
        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError("Groq API key is required")
        model = kwargs.get("model", "llama-3.2-11b-vision-preview")
        return GroqProvider(api_key, model)
    
    else:
        raise ValueError(f"Unsupported provider: {provider_type}")