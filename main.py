from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import logging
import sys

from auth import oauth
from config import settings
import auth_routes
import protected_routes
from auth_routes import router as auth_router
from github_bot import router as github_bot_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("auth0_app")

app = FastAPI(
    title="FastAPI Auth0 Authentication",
    description="A FastAPI application with Auth0 authentication that supports Google OAuth and username/password login",
    version="0.1.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth authentication
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Global exception handler for better error messages
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Unhandled error: {str(exc)}"
    logger.error(error_msg, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": error_msg},
    )

# Add health endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running properly.
    Returns a simple status message.
    """
    logger.debug("Health check endpoint called")
    return {"status": "healthy", "message": "Service is up and running"}

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint that provides basic information about the API.
    """
    logger.debug("Root endpoint called")
    return {
        "message": "Welcome to the FastAPI Auth0 Authentication API",
        "documentation": "/docs",
        "auth_routes": {
            "login_page": "/auth/login",
            "login_with_auth0": "/auth/login/auth0",
            "login_with_google": "/auth/login/google",
            "login_with_github": "/auth/login/github",
            "user_profile": "/auth/profile",
            "logout": "/auth/logout"
        }
    }

# Include the authentication and protected routes
app.include_router(auth_router, prefix="/auth")
app.include_router(protected_routes.router, prefix="/api")
app.include_router(github_bot_router, prefix="/github")

# Log Auth0 configuration at startup but mask sensitive values
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting application with Auth0 domain: {settings.AUTH0_DOMAIN}")
    logger.info(f"API URL configured as: {settings.API_URL}")
    # Don't log secrets or credentials

if __name__ == "__main__":
    logger.info(f"Starting server on 0.0.0.0:{8000}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
