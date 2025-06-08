"""
Test script to verify Auth0 connectivity.
This script manually fetches the Auth0 OpenID Connect configuration to verify it's accessible.
"""
import httpx
import asyncio
import json
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("auth0_test")

# Load environment variables
load_dotenv()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")

async def test_connection():
    """Test the connection to Auth0"""
    try:
        logger.info(f"Testing connection to Auth0 domain: {AUTH0_DOMAIN}")
        
        # Test 1: Fetch the OpenID Connect configuration
        async with httpx.AsyncClient(timeout=10.0) as client:
            openid_config_url = f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration"
            logger.info(f"Fetching OpenID configuration from {openid_config_url}")
            
            response = await client.get(openid_config_url)
            
            if response.status_code == 200:
                config = response.json()
                logger.info("OpenID Connect configuration retrieved successfully")
                logger.info(f"Issuer: {config.get('issuer')}")
                logger.info(f"JWKS URI: {config.get('jwks_uri')}")
                
                # Test 2: Fetch the JWKS
                if 'jwks_uri' in config:
                    jwks_response = await client.get(config['jwks_uri'])
                    if jwks_response.status_code == 200:
                        logger.info("JWKS retrieved successfully")
                    else:
                        logger.error(f"Failed to retrieve JWKS: {jwks_response.status_code} - {jwks_response.text}")
                else:
                    logger.error("JWKS URI missing from OpenID configuration")
            else:
                logger.error(f"Failed to retrieve OpenID configuration: {response.status_code} - {response.text}")
        
        # Test 3: Verify client credentials
        if AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET:
            logger.info("Testing client credentials")
            token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
            payload = {
                "client_id": AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
                "audience": f"https://{AUTH0_DOMAIN}/api/v2/",
                "grant_type": "client_credentials"
            }
            
            token_response = await client.post(token_url, json=payload)
            if token_response.status_code == 200:
                logger.info("Client credentials verified successfully")
            else:
                logger.error(f"Failed to verify client credentials: {token_response.status_code} - {token_response.text}")
        else:
            logger.warning("Client ID or Client Secret not provided, skipping client credentials test")
            
    except Exception as e:
        logger.error(f"Error testing Auth0 connection: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_connection()) 