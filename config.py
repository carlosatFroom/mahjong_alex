"""
Configuration management for Mahjong AI Tutor
Handles environment-specific settings
"""

import os
from typing import Optional

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, rely on system environment variables
    pass

class Config:
    # Groq configuration (production LLM provider)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")  # Latest vision-capable model
    
    # Server configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8080"))
    
    # Security configuration
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "20"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # CORS configuration
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else [
        f"http://localhost:{SERVER_PORT}",
        f"http://127.0.0.1:{SERVER_PORT}"
    ]
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def for_production(cls, server_ip: str = "10.9.1.44") -> "Config":
        """Create production configuration"""
        config = cls()
        config.ALLOWED_ORIGINS = [
            f"http://{server_ip}:{config.SERVER_PORT}",
            f"http://localhost:{config.SERVER_PORT}",
            f"http://127.0.0.1:{config.SERVER_PORT}"
        ]
        return config
    
    def __repr__(self):
        return (f"Config(groq_model={self.GROQ_MODEL}, "
                f"server={self.SERVER_HOST}:{self.SERVER_PORT})")

# Global config instance
config = Config()