"""
Sponge Configuration Module
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import warnings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Sponge"
    DEBUG: bool = False
    VERSION: str = "0.1.0"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # openai, anthropic
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    MODEL_NAME: str = "gpt-4o"
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 4096
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_ECHO: bool = False
    
    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # Sandbox
    SANDBOX_ENABLED: bool = True
    SANDBOX_TYPE: str = "docker"  # docker, local
    SANDBOX_TIMEOUT: int = 300
    SANDBOX_MEMORY_LIMIT: str = "512m"
    SANDBOX_CPU_LIMIT: float = 1.0
    
    # Security
    SECRET_KEY: str
    API_KEY_HEADER: str = "X-API-Key"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def validate_security_settings(self) -> None:
        """Validate security-critical settings"""
        if self.SECRET_KEY == "change-me-in-production" or len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY must be set to a secure value (at least 32 characters). "
                "Generate one using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        
        # Warn about default database password in production
        if not self.DEBUG and "sponge_password" in self.DATABASE_URL:
            warnings.warn(
                "Using default database password in production environment. "
                "Please change the DATABASE_URL to use a secure password.",
                UserWarning,
                stacklevel=2
            )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    # Validate security settings on initialization
    settings.validate_security_settings()
    return settings


# Global settings instance
settings = get_settings()
