from fastapi import APIRouter, Depends, Request, HTTPException, status
from typing import List, Dict, Any

from models import User
from auth import verify_session
from config import settings

router = APIRouter(tags=["Protected"], prefix="/protected")

@router.get("/data")
async def get_protected_data(current_user: User = Depends(verify_session)):
    """
    A protected endpoint that requires authentication.
    Returns some data along with the user's ID.
    """
    return {
        "message": "This is protected data!",
        "user_id": current_user.id,
        "auth_type": current_user.auth_type,
        "user_name": current_user.name,
        "data": {
            "items": ["item1", "item2", "item3"],
            "count": 3
        }
    }

@router.get("/admin-only")
async def admin_only(current_user: User = Depends(verify_session)):
    """
    An endpoint that could check for admin permissions.
    In a real application, you would check if the user has admin permissions.
    """
    # You could check permissions here, e.g., by examining roles assigned in Auth0
    return {
        "message": "You have access to admin area",
        "user_id": current_user.id,
        "user_name": current_user.name
    } 