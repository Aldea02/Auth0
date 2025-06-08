from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import httpx
import base64
import logging
from typing import Optional
from auth import verify_session

# Set up logging
logger = logging.getLogger("github_bot")

# Create router
router = APIRouter(tags=["GitHub Bot"])

# Set up templates
templates = Jinja2Templates(directory="templates")

# Pydantic model for the request
class GitHubPushRequest(BaseModel):
    repoName: str
    branch: str
    filePath: str
    commitMessage: str
    fileContent: str

# GitHub Bot page route
@router.get("/github-bot", response_class=HTMLResponse)
async def github_bot_page(request: Request, current_user: dict = Depends(verify_session)):
    """
    Display the GitHub Bot page
    """
    return templates.TemplateResponse("github_bot.html", {"request": request})

# GitHub push endpoint
@router.post("/api/github/push")
async def push_to_github(
    request: GitHubPushRequest,
    current_user: dict = Depends(verify_session)
):
    """
    Push content to a GitHub repository
    """
    try:
        # Get GitHub token from user's session
        github_token = current_user.get("github_token")
        if not github_token:
            raise HTTPException(
                status_code=401,
                detail="GitHub token not found. Please connect your GitHub account first."
            )

        # Split repository name into owner and repo
        try:
            owner, repo = request.repoName.split("/")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid repository name format. Use 'owner/repo' format."
            )

        # Get the current file content and SHA
        async with httpx.AsyncClient() as client:
            # Get the current file content
            file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{request.filePath}"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            try:
                file_response = await client.get(file_url, headers=headers)
                file_data = file_response.json()
                current_sha = file_data.get("sha")
            except Exception as e:
                logger.warning(f"File might not exist: {str(e)}")
                current_sha = None

            # Prepare the content
            content = base64.b64encode(request.fileContent.encode()).decode()

            # Create the commit
            commit_data = {
                "message": request.commitMessage,
                "content": content,
                "branch": request.branch
            }
            
            if current_sha:
                commit_data["sha"] = current_sha

            # Push the changes
            response = await client.put(
                file_url,
                headers=headers,
                json=commit_data
            )

            if response.status_code in (200, 201):
                return {"message": "Successfully pushed to GitHub"}
            else:
                error_message = response.json().get("message", "Unknown error")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to push to GitHub: {error_message}"
                )

    except httpx.RequestError as e:
        logger.error(f"Error connecting to GitHub: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Failed to connect to GitHub. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        ) 