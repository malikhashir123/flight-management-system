import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Flight Management System API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    SECRET_KEY: str = "super-secret-fms-jwt-token-key-minimum-32-chars-length"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOWED_ORIGINS: str = "*"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./fms.db"
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    
    # Business logic defaults
    HOLD_TIMEOUT_MINUTES: int = 10
    DEFAULT_QUOTE_EXPIRY_MINUTES: int = 15
    WAITLIST_CLAIM_WINDOW_HOURS: int = 2
    INVOLUNTARY_CHANGE_MIN_HOURS: int = 2
    REFUND_ESCALATION_DAYS: int = 3
    
    # Email settings
    GMAIL_SENDER_EMAIL: str = ""
    GMAIL_APP_PASSWORD: str = ""
    GMAIL_SMTP_HOST: str = "smtp.gmail.com"
    GMAIL_SMTP_PORT: int = 587
    
    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "flight-policies"
    PINECONE_ENVIRONMENT: str = "us-east-1"
    
    # LLM
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

settings = Settings()
