from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings"""
    # Frontend specific settings
    app_name: str = "BlueTrivia Admin"
    admin_username: str = "admin"
    admin_password: str = "admin"  # Simplified for testing, don't use in production
    
    # Database settings - use the existing database path in root folder
    db_path: str = "bluetrivia.db"  # Direct path to the database in root folder
    
    # Bot settings that might be needed by frontend
    # These won't cause validation errors if present in .env
    bot_debug_mode: str | None = None
    bot_threshold: str | None = None
    bot_skip_on_input: str | None = None
    db_file: str | None = None
    tmdb_api_key: str | None = None
    tmdb_image_quality: str | None = None
    bsky_username: str | None = None
    bsky_password: str | None = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow arbitrary env vars, won't cause validation errors
        extra = "ignore"


settings = Settings()
