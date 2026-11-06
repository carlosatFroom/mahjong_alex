"""
Configuration management for the Mahjong practice table
All values come from environment variables (or a local .env file)
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    # Groq configuration (coach LLM provider)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    # Server configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8080"))
    SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "")
    # "Lax" for a direct link; "None" (HTTPS only) when embedded in another site's iframe
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "Lax")

    # Game configuration
    DB_PATH: str = os.getenv("GAME_DB_PATH", "games.sqlite3")
    CARD_FILE: str = os.getenv("CARD_FILE", "cards/practice_card.json")
    RULES_FILE: str = os.getenv("RULES_FILE", "rules/practice_rules.md")
    COACH_MAX_MESSAGES: int = int(os.getenv("COACH_MAX_MESSAGES", "40"))
    GAME_TTL_HOURS: int = int(os.getenv("GAME_TTL_HOURS", "24"))

    # CORS configuration (comma-separated); empty means same-origin only
    ALLOWED_ORIGINS: list = [o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o]

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __repr__(self):
        return (f"Config(groq_model={self.GROQ_MODEL}, "
                f"server={self.SERVER_HOST}:{self.SERVER_PORT})")


config = Config()
