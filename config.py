from pydantic_settings import BaseSettings
from pydantic import Field, HttpUrl
import os
from typing import Optional


class Settings(BaseSettings):
    # Auth0 settings
    AUTH0_DOMAIN: str = Field("your-auth0-domain.auth0.com", env="AUTH0_DOMAIN")
    AUTH0_CLIENT_ID: str = Field("your-auth0-client-id", env="AUTH0_CLIENT_ID")
    AUTH0_CLIENT_SECRET: str = Field("your-auth0-client-secret", env="AUTH0_CLIENT_SECRET")
    AUTH0_AUDIENCE: str = Field("https://your-api-audience", env="AUTH0_AUDIENCE")
    
    # OAuth settings - These are derived from AUTH0_DOMAIN, not from environment variables
    @property
    def OAUTH_AUTHORIZE_URL(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/authorize"
    
    @property
    def OAUTH_TOKEN_URL(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/oauth/token"
    
    @property
    def OAUTH_USERINFO_URL(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/userinfo"

    # API settings
    API_URL: str = Field("http://localhost:8000", env="API_URL")
    SECRET_KEY: str = Field("your-secret-key-for-sessions", env="SECRET_KEY")

    # Determines if we're running in debug mode
    DEBUG: bool = Field(True, env="DEBUG")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings() 