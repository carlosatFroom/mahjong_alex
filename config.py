"""
Configuration management for Mahjong AI Tutor
Handles environment-specific settings
"""

import os
from typing import Optional

class Config:
    # LLM Provider configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" or "groq"
    
    # Ollama configuration
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "localhost")
    OLLAMA_PORT: int = int(os.getenv("OLLAMA_PORT", "11434"))
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "minicpm-v:latest")
    
    # Groq configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.2-11b-vision-preview")  # Vision-capable model
    
    # Server configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    
    # Security configuration
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "20"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # CORS configuration
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else [
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def ollama_base_url(self) -> str:
        """Get the complete Ollama base URL"""
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"
    
    @classmethod
    def for_production(cls, server_ip: str = "10.9.1.44") -> "Config":
        """Create production configuration"""
        config = cls()
        config.OLLAMA_HOST = server_ip  # Use server IP for Ollama
        config.ALLOWED_ORIGINS = [
            f"http://{server_ip}:8000",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ]
        return config
    
    def __repr__(self):
        return (f"Config(ollama={self.ollama_base_url}, "
                f"model={self.OLLAMA_MODEL}, "
                f"server={self.SERVER_HOST}:{self.SERVER_PORT})")

# Global config instance
config = Config()