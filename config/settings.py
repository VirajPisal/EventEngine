"""
Application settings and environment variable management
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = os.getenv("APP_NAME", "Event Lifecycle Agent")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "event_lifecycle")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    USE_SQLITE: bool = os.getenv("USE_SQLITE", "True").lower() == "true"  # Use SQLite by default for easy testing
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components"""
        if self.USE_SQLITE:
            # Use SQLite for testing (no server required)
            db_path = Path(__file__).parent.parent / "event_lifecycle.db"
            return f"sqlite:///{db_path}"
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRY_HOURS: int = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    

    # Email Configuration — defined as properties so .env changes take effect
    @property
    def SMTP_HOST(self) -> str:
        load_dotenv(override=True)
        return os.getenv("SMTP_HOST", "smtp.gmail.com")

    @property
    def SMTP_PORT(self) -> int:
        return int(os.getenv("SMTP_PORT", "587"))

    @property
    def SMTP_USER(self) -> str:
        load_dotenv(override=True)
        return os.getenv("SMTP_USER", "")

    @property
    def SMTP_PASSWORD(self) -> str:
        load_dotenv(override=True)
        return os.getenv("SMTP_PASSWORD", "")

    @property
    def EMAIL_FROM(self) -> str:
        return os.getenv("EMAIL_FROM", "noreply@eventengine.com")
    
    # SMS Configuration (Twilio)
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # OpenAI Configuration (for AI insights)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Agent Configuration
    AGENT_LOOP_INTERVAL_SECONDS: int = int(os.getenv("AGENT_LOOP_INTERVAL_SECONDS", "60"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/event_agent.log")


# Global settings instance
settings = Settings()
