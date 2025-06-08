from pydantic import BaseModel, Field
from typing import Optional, List


class TokenData(BaseModel):
    """Data extracted from a JWT token"""
    sub: str
    auth_type: str = "regular"  # Can be "regular" or "google"


class User(BaseModel):
    """User model"""
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    auth_type: str = "regular"  # Can be "regular" or "google"


class Token(BaseModel):
    """Token model for OAuth2 response"""
    access_token: str
    token_type: str
    id_token: Optional[str] = None
    expires_in: Optional[int] = None


class TokenRequest(BaseModel):
    """Request model for username/password authentication"""
    username: str
    password: str


class UserProfile(BaseModel):
    """User profile model with more detailed information"""
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    auth_type: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    locale: Optional[str] = None
    verified: Optional[bool] = None 