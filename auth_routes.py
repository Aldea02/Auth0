from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from authlib.integrations.starlette_client import OAuth
import httpx
from typing import Optional
import json
import logging
import authlib.integrations.base_client.errors
from models import Token, TokenRequest, User, UserProfile
from auth import oauth, verify_session, get_auth0_user_info, get_management_api_token
from config import settings

router = APIRouter(tags=["Authentication"])

# Create logger for authentication routes
logger = logging.getLogger("auth_routes")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Login page route
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Display a simple login page with links to the different authentication methods
    """
    return templates.TemplateResponse("index.html", {"request": request})

# Auth0 login route (handles both username/password and social logins)
@router.get("/login/auth0")
async def login_auth0(request: Request):
    """
    Redirect to Auth0's login page where the user can choose to login via username/password
    """
    redirect_uri = f"{settings.API_URL}/auth/callback"
    logger.info(f"Redirecting to Auth0 for login, callback URL: {redirect_uri}")
    
    try:
        # Verify the OAuth client is properly configured
        if not oauth.auth0.authorize_url:
            logger.error("Auth0 client missing authorize_url")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Auth0 client not properly configured. Missing authorize_url."}
            )
            
        # Clear any existing session first to prevent state mismatch
        request.session.clear()
        
        return await oauth.auth0.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Error redirecting to Auth0: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Failed to initiate authentication: {str(e)}"}
        )

# Google OAuth login route
@router.get("/login/google")
async def login_google(request: Request):
    """
    Redirect to Auth0's Google OAuth login page
    """
    redirect_uri = f"{settings.API_URL}/auth/callback"
    logger.info(f"Redirecting to Auth0 for Google login, callback URL: {redirect_uri}")
    
    try:
        # Verify the OAuth client is properly configured
        if not oauth.auth0.authorize_url:
            logger.error("Auth0 client missing authorize_url")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Auth0 client not properly configured. Missing authorize_url."}
            )
            
        # Clear any existing session first to prevent state mismatch
        request.session.clear()
        
        # We add connection=google-oauth2 to specifically use Google
        return await oauth.auth0.authorize_redirect(
            request, 
            redirect_uri,
            connection="google-oauth2"
        )
    except Exception as e:
        logger.error(f"Error redirecting to Auth0: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Failed to initiate authentication: {str(e)}"}
        )

# GitHub OAuth login route
@router.get("/login/github")
async def login_github(request: Request):
    """Redirect to Auth0's GitHub OAuth login page"""
    redirect_uri = f"{settings.API_URL}/auth/callback"
    logger.info(f"Redirecting to Auth0 for GitHub login, callback URL: {redirect_uri}")
    
    try:
        # Verify the OAuth client is properly configured
        if not oauth.auth0.authorize_url:
            logger.error("Auth0 client missing authorize_url")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Auth0 client not properly configured. Missing authorize_url."}
            )
            
        # Clear any existing session first to prevent state mismatch
        request.session.clear()
        
        # Try to get management API token and check connections
        try:
            token = await get_management_api_token()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{settings.AUTH0_DOMAIN}/api/v2/connections",
                    headers={"Authorization": f"Bearer {token}"}
                )
                connections = response.json()
                
                # Find GitHub connection
                github_connection = next(
                    (conn for conn in connections if conn["strategy"] == "github"),
                    None
                )
                
                if not github_connection:
                    logger.error("GitHub connection not found in Auth0")
                    return JSONResponse(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={
                            "detail": "GitHub connection not found in Auth0. Please set up the GitHub connection in your Auth0 dashboard.",
                            "available_connections": [conn["name"] for conn in connections],
                            "setup_instructions": [
                                "1. Go to Auth0 Dashboard → Authentication → Social",
                                "2. Click 'Create Connection' and select GitHub",
                                "3. Create a GitHub OAuth App at https://github.com/settings/developers",
                                "4. Set the Authorization callback URL to: https://YOUR_AUTH0_DOMAIN/login/callback",
                                "5. Copy the Client ID and Client Secret to Auth0",
                                "6. Enable the connection for your application"
                            ]
                        }
                    )
                
                # Check if our client is enabled
                if settings.AUTH0_CLIENT_ID not in github_connection.get("enabled_clients", []):
                    logger.error(f"GitHub connection not enabled for client {settings.AUTH0_CLIENT_ID}")
                    return JSONResponse(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={
                            "detail": "GitHub connection is not enabled for this application. Please enable it in your Auth0 dashboard.",
                            "connection_name": github_connection["name"],
                            "enabled_clients": github_connection.get("enabled_clients", []),
                            "setup_instructions": [
                                "1. Go to Auth0 Dashboard → Authentication → Social",
                                "2. Find your GitHub connection",
                                "3. Click on it to edit",
                                "4. Go to the 'Applications' tab",
                                "5. Enable your application",
                                "6. Save the changes"
                            ]
                        }
                    )
                
                # Use the actual connection name from Auth0
                connection_name = github_connection["name"]
                logger.info(f"Using GitHub connection name: {connection_name}")
                
                return await oauth.auth0.authorize_redirect(
                    request, 
                    redirect_uri,
                    connection=connection_name
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("Management API access not available, trying default GitHub connection")
                # If management API access is not available, try with default connection name
                return await oauth.auth0.authorize_redirect(
                    request, 
                    redirect_uri,
                    connection="github"  # Default connection name
                )
            raise
    except Exception as e:
        logger.error(f"Error redirecting to Auth0 for GitHub login: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": f"Failed to initiate GitHub authentication: {str(e)}",
                "setup_instructions": [
                    "1. Go to Auth0 Dashboard → Applications → APIs",
                    "2. Find 'Auth0 Management API'",
                    "3. Go to 'Machine to Machine Applications' tab",
                    "4. Enable your application",
                    "5. Grant it the following permissions:",
                    "   - read:connections",
                    "   - read:clients",
                    "6. Save the changes",
                    "7. Then go to Authentication → Social",
                    "8. Set up GitHub connection if not already done",
                    "9. Enable the connection for your application"
                ]
            }
        )

# Alternative GitHub OAuth login routes with different connection names
@router.get("/login/github-alt1")
async def login_github_alt1(request: Request):
    """
    Alternate GitHub login using 'github-oauth2' connection name
    """
    redirect_uri = f"{settings.API_URL}/auth/callback"
    logger.info(f"Trying alternate GitHub connection name: github-oauth2")
    
    try:
        request.session.clear()
        return await oauth.auth0.authorize_redirect(
            request, 
            redirect_uri,
            connection="github-oauth2"  # Alternative name sometimes used
        )
    except Exception as e:
        logger.error(f"Error with alternate GitHub connection: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Failed to initiate GitHub authentication: {str(e)}"}
        )

# OAuth callback route
@router.get("/callback")
async def auth_callback(request: Request):
    """
    Handle the OAuth callback from Auth0
    """
    try:
        logger.info("Received callback from Auth0")
        logger.debug(f"Callback query params: {request.query_params}")
        
        # Check if there's an error parameter in the query string
        if "error" in request.query_params:
            error = request.query_params.get("error")
            error_description = request.query_params.get("error_description", "Unknown error")
            logger.error(f"Auth0 returned an error: {error} - {error_description}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": f"Authentication failed: {error_description}"}
            )
        
        try:
            # Get the authorization code from the request
            token = await oauth.auth0.authorize_access_token(request)
            logger.info(f"Access token type: {type(token)}")
            
            if token:
                logger.info(f"Token keys: {token.keys()}")
            else:
                logger.error("Received empty token from Auth0")
                raise ValueError("Empty token received")
            
            # Store the token in the session
            request.session['token'] = token
            
            # Try to get user info from id_token if present
            try:
                user_info = await oauth.auth0.parse_id_token(request, token)
                logger.info(f"Retrieved user info from ID token: {user_info.get('sub')}")
            except Exception as id_token_err:
                logger.warning(f"Could not parse ID token: {str(id_token_err)}")
                
                # Fallback to userinfo endpoint
                try:
                    user_info = await get_auth0_user_info(token.get('access_token'))
                    logger.info(f"Retrieved user info from userinfo endpoint: {user_info.get('sub')}")
                except Exception as userinfo_err:
                    logger.error(f"Could not get user info: {str(userinfo_err)}")
                    raise
            
            # Ensure we have the basic user data
            if not user_info or not user_info.get('sub'):
                logger.error(f"Invalid user info: {user_info}")
                raise ValueError("Invalid user information received")
            
            # Store user info in session
            request.session['user'] = {
                'id': user_info.get('sub'),
                'name': user_info.get('name'),
                'email': user_info.get('email'),
                'picture': user_info.get('picture')
            }

            # If this is a GitHub login, store the GitHub token
            if user_info.get('sub', '').startswith('github|'):
                try:
                    # Get GitHub token from Auth0
                    github_token = token.get('access_token')
                    if github_token:
                        request.session['user']['github_token'] = github_token
                        logger.info("GitHub token stored in session")
                except Exception as e:
                    logger.error(f"Failed to store GitHub token: {str(e)}")
            
            logger.info(f"User authenticated: {user_info.get('sub')}")
            
            # User is now authenticated, redirect to a protected page
            return RedirectResponse(url="/api/protected/data")
        
        except authlib.integrations.base_client.errors.MismatchingStateError:
            logger.error("State mismatch error - this could be due to an expired session or CSRF attempt")
            # Clear any partial session data
            request.session.clear()
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Authentication failed: State mismatch error. Please try logging in again."
                }
            )
            
    except Exception as e:
        logger.error(f"Error in Auth0 callback: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": f"Authentication failed: {str(e)}"}
        )

# User profile route (protected by session middleware)
@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(verify_session)):
    """
    Get the profile of the authenticated user
    """
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture,
        auth_type=current_user.auth_type
    )

# Logout route
@router.get("/logout")
async def logout(request: Request):
    """
    Log the user out
    """
    # Clear session data
    request.session.clear()
    
    # Build the Auth0 logout URL
    logout_url = (
        f"https://{settings.AUTH0_DOMAIN}/v2/logout?"
        f"client_id={settings.AUTH0_CLIENT_ID}&"
        f"returnTo={settings.API_URL}"
    )
    
    logger.info(f"Logging out user, redirecting to: {logout_url}")
    
    # Redirect to Auth0 logout page, which will clear the Auth0 session
    return RedirectResponse(url=logout_url)

# Debug route for checking Auth0 configuration - DISABLE IN PRODUCTION
@router.get("/debug")
async def debug_auth0():
    """
    Debug endpoint to verify Auth0 configuration
    WARNING: This should be disabled in production!
    """
    try:
        logger.info("Debug endpoint called")
        
        # Check Auth0 domain
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                openid_config_url = f"https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration"
                logger.info(f"Checking Auth0 OpenID configuration: {openid_config_url}")
                
                response = await client.get(openid_config_url)
                if response.status_code == 200:
                    config = response.json()
                    
                    # Check that the important URLs are present
                    required_keys = [
                        'authorization_endpoint',
                        'token_endpoint',
                        'userinfo_endpoint',
                        'jwks_uri'
                    ]
                    
                    missing_keys = [key for key in required_keys if key not in config]
                    
                    if missing_keys:
                        return {
                            "status": "warning",
                            "message": f"Some required keys are missing from OpenID configuration: {missing_keys}",
                            "auth0_domain": settings.AUTH0_DOMAIN,
                            "config": config
                        }
                    else:
                        return {
                            "status": "ok",
                            "message": "Auth0 OpenID configuration is valid",
                            "auth0_domain": settings.AUTH0_DOMAIN,
                            "config": {
                                key: config.get(key) for key in required_keys
                            },
                            "oauth_client": {
                                "authorize_url": oauth.auth0.authorize_url,
                                "access_token_url": oauth.auth0.access_token_url,
                                "api_base_url": oauth.auth0.api_base_url
                            }
                        }
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to retrieve OpenID configuration. Status: {response.status_code}",
                        "auth0_domain": settings.AUTH0_DOMAIN,
                        "error": response.text
                    }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error checking Auth0 configuration: {str(e)}",
                "auth0_domain": settings.AUTH0_DOMAIN
            }
            
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }

# Debug route to check available connections
@router.get("/debug/connections")
async def debug_connections():
    """Debug endpoint to check available connections"""
    try:
        # Get management API token
        token = await get_management_api_token()
        
        # Get all connections
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{settings.AUTH0_DOMAIN}/api/v2/connections",
                headers={"Authorization": f"Bearer {token}"}
            )
            connections = response.json()
            
            # Filter for social connections
            social_connections = [
                {
                    "name": conn["name"],
                    "strategy": conn["strategy"],
                    "enabled_clients": conn.get("enabled_clients", []),
                    "status": "Enabled" if conn.get("enabled_clients") else "Disabled"
                }
                for conn in connections
                if conn["strategy"] in ["github", "google-oauth2"]
            ]
            
            return {
                "status": "success",
                "connections": social_connections,
                "client_id": settings.AUTH0_CLIENT_ID
            }
    except Exception as e:
        logger.error(f"Error checking connections: {str(e)}")
        return {"status": "error", "message": str(e)}

# Debug route to check GitHub connection specifically
@router.get("/debug/github")
async def debug_github():
    """Debug endpoint to check GitHub connection specifically"""
    try:
        # Get management API token
        token = await get_management_api_token()
        
        # Get GitHub connection specifically
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{settings.AUTH0_DOMAIN}/api/v2/connections",
                headers={"Authorization": f"Bearer {token}"}
            )
            connections = response.json()
            
            # Find GitHub connection
            github_connection = next(
                (conn for conn in connections if conn["strategy"] == "github"),
                None
            )
            
            if not github_connection:
                return {
                    "status": "error",
                    "message": "GitHub connection not found in Auth0"
                }
            
            # Check if our client is enabled
            is_enabled = settings.AUTH0_CLIENT_ID in github_connection.get("enabled_clients", [])
            
            return {
                "status": "success",
                "connection": {
                    "name": github_connection["name"],
                    "strategy": github_connection["strategy"],
                    "enabled_clients": github_connection.get("enabled_clients", []),
                    "is_enabled_for_this_app": is_enabled
                }
            }
    except Exception as e:
        logger.error(f"Error checking GitHub connection: {str(e)}")
        return {"status": "error", "message": str(e)}

# Debug route to check GitHub connection configuration
@router.get("/debug/github-detailed")
async def debug_github_detailed():
    """Detailed debug endpoint to check GitHub connection configuration"""
    try:
        # Get management API token
        token = await get_management_api_token()
        
        # Get all connections
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{settings.AUTH0_DOMAIN}/api/v2/connections",
                headers={"Authorization": f"Bearer {token}"}
            )
            connections = response.json()
            
            # Find GitHub connection
            github_connection = next(
                (conn for conn in connections if conn["strategy"] == "github"),
                None
            )
            
            if not github_connection:
                return {
                    "status": "error",
                    "message": "GitHub connection not found in Auth0",
                    "available_connections": [conn["name"] for conn in connections]
                }
            
            # Get connection details
            connection_id = github_connection["id"]
            connection_details = await client.get(
                f"https://{settings.AUTH0_DOMAIN}/api/v2/connections/{connection_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            connection_data = connection_details.json()
            
            # Check if our client is enabled
            is_enabled = settings.AUTH0_CLIENT_ID in github_connection.get("enabled_clients", [])
            
            return {
                "status": "success",
                "connection": {
                    "name": github_connection["name"],
                    "strategy": github_connection["strategy"],
                    "enabled_clients": github_connection.get("enabled_clients", []),
                    "is_enabled_for_this_app": is_enabled,
                    "display_name": connection_data.get("display_name"),
                    "options": connection_data.get("options", {}),
                    "available_connections": [conn["name"] for conn in connections]
                },
                "your_client_id": settings.AUTH0_CLIENT_ID
            }
    except Exception as e:
        logger.error(f"Error checking GitHub connection: {str(e)}")
        return {"status": "error", "message": str(e)}

# Debug route to list all available connection names
@router.get("/debug/connection-names")
async def debug_connection_names():
    """Debug endpoint to list all available connection names"""
    try:
        # Get management API token
        token = await get_management_api_token()
        
        # Get all connections
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{settings.AUTH0_DOMAIN}/api/v2/connections",
                headers={"Authorization": f"Bearer {token}"}
            )
            connections = response.json()
            
            # Extract connection names and strategies
            connection_info = [
                {
                    "name": conn["name"],
                    "strategy": conn["strategy"],
                    "enabled_clients": conn.get("enabled_clients", []),
                    "is_enabled_for_this_app": settings.AUTH0_CLIENT_ID in conn.get("enabled_clients", [])
                }
                for conn in connections
            ]
            
            return {
                "status": "success",
                "connections": connection_info,
                "your_client_id": settings.AUTH0_CLIENT_ID
            }
    except Exception as e:
        logger.error(f"Error checking connection names: {str(e)}")
        return {"status": "error", "message": str(e)} 