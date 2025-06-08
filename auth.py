from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError
from authlib.integrations.starlette_client import OAuth
import httpx
import logging
import json
from urllib.parse import urljoin

from config import settings
from models import User, TokenData

# Set up logging
logger = logging.getLogger("auth")

# OAuth configuration for Google authentication via Auth0
oauth = OAuth()

# Log Auth0 configuration
logger.info(f"Configuring Auth0 with domain: {settings.AUTH0_DOMAIN}")

# Register auth0 client with explicit URLs instead of metadata
oauth.register(
    name="auth0",
    client_id=settings.AUTH0_CLIENT_ID,
    client_secret=settings.AUTH0_CLIENT_SECRET,
    authorize_url=f"https://{settings.AUTH0_DOMAIN}/authorize",
    access_token_url=f"https://{settings.AUTH0_DOMAIN}/oauth/token",
    api_base_url=f"https://{settings.AUTH0_DOMAIN}",
    jwks_uri=f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json",
    client_kwargs={
        "scope": "openid profile email",
        "response_type": "code",
    },
)

# Session-based authentication helper function
async def verify_session(request: Request) -> User:
    """
    Verify that the user has an active session and return user information.
    """
    user_data = request.session.get("user")
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or not authenticated",
        )
    
    logger.debug(f"User from session: {user_data}")
    
    # Determine auth type from user ID
    user_id = user_data.get('id', '')
    auth_type = "auth0"
    
    if user_id.startswith("google-oauth2"):
        auth_type = "google"
    elif user_id.startswith("github"):
        auth_type = "github"
    
    return User(
        id=user_data.get("id"),
        email=user_data.get("email"),
        name=user_data.get("name"),
        picture=user_data.get("picture"),
        auth_type=auth_type
    )

# Function to fetch user information from Auth0
async def get_auth0_user_info(token: str) -> dict:
    """
    Get user information from Auth0 using a token.
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://{settings.AUTH0_DOMAIN}/userinfo", 
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting user info from Auth0: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                )
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Auth0: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

async def get_management_api_token() -> str:
    """
    Get a management API token from Auth0.
    This token is used to make calls to the Auth0 Management API.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{settings.AUTH0_DOMAIN}/oauth/token",
                json={
                    "client_id": settings.AUTH0_CLIENT_ID,
                    "client_secret": settings.AUTH0_CLIENT_SECRET,
                    "audience": f"https://{settings.AUTH0_DOMAIN}/api/v2/",
                    "grant_type": "client_credentials"
                }
            )
            response.raise_for_status()
            return response.json()["access_token"]
    except Exception as e:
        logger.error(f"Error getting management API token: {str(e)}")
        raise 