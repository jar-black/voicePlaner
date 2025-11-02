"""
Configuration management for AI Project Orchestrator
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Anthropic API
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-5-20250929"

    # Database
    database_url: str

    # MCP Service URLs
    github_mcp_url: str = "http://github-mcp:8001"
    planning_mcp_url: str = "http://planning-mcp:8002"
    claude_code_mcp_url: str = "http://claude-code-mcp:8003"

    # Application
    app_name: str = "AI Project Orchestrator"
    debug: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
