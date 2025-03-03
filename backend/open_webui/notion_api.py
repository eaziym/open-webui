"""
This module provides a comprehensive list of all Notion API endpoints integrated with Open WebUI.
It maintains the OAuth integration while removing the tool calling functionality.
"""

from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, BackgroundTasks
from pydantic import BaseModel
import json
import logging
import httpx
import aiohttp
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse

from open_webui.models.users import UserModel as User
from open_webui.models.integrations import IntegrationModel as IntegrationConnection
from open_webui.internal.db import get_db
from open_webui.utils.auth import get_current_user
from open_webui.models.integrations import Integrations
from open_webui.config import (
    AVAILABLE_INTEGRATIONS, 
    ENABLE_INTEGRATIONS, 
    NOTION_CLIENT_ID, 
    NOTION_CLIENT_SECRET, 
    NOTION_REDIRECT_URI
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notion", tags=["integrations-notion"])

# Status response model
class NotionStatusResponse(BaseModel):
    integration: Optional[Dict[str, Any]] = None
    is_connected: bool = False

# Helper function to format Notion API results
def format_notion_api_result(result: Dict[str, Any], action_type: str) -> Dict[str, Any]:
    """Format Notion API results in a consistent way for the frontend
    
    Args:
        result: The API result from Notion
        action_type: The type of action that was performed (e.g., "search_notion")
        
    Returns:
        Dict[str, Any]: Formatted result with consistent structure
    """
    # If there was an error, return it directly
    if result.get("error"):
        return {
            "success": False,
            "error": result.get("message", "Unknown error"),
            "action": action_type,
            "data": None
        }
    
    # Otherwise return the formatted result
    return {
        "success": True,
        "error": None,
        "action": action_type,
        "data": result
    }

# Helper function to check if integrations are enabled
def check_integrations_enabled():
    """Check if integrations are enabled on the server"""
    if not ENABLE_INTEGRATIONS:
        raise HTTPException(
            status_code=400,
            detail="Integrations are not enabled on this server."
        )

# Helper function to get and validate integration
def get_user_integration(user_id: str, integration_type: str) -> IntegrationConnection:
    """Get and validate a user's integration.
    
    Args:
        user_id: User ID
        integration_type: Type of integration (e.g., "notion")
        
    Returns:
        IntegrationConnection: The integration model
        
    Raises:
        HTTPException: If integration doesn't exist or is not active
    """
    check_integrations_enabled()
    
    # Check if integration type is available
    if integration_type not in AVAILABLE_INTEGRATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Integration '{integration_type}' is not supported."
        )
    
    # Check if integration is enabled
    integration_config = AVAILABLE_INTEGRATIONS.get(integration_type)
    if not integration_config.get("enabled", False):
        raise HTTPException(
            status_code=400,
            detail=f"Integration '{integration_type}' is not enabled on this server."
        )
    
    # Get user's integration
    integration = Integrations.get_user_active_integration(user_id, integration_type)
    if not integration:
        raise HTTPException(
            status_code=404,
            detail=f"No active {integration_type} integration found for this user."
        )
    
    return integration

# Add this function before the notion_execute route
async def notion_api_request(
    endpoint: str,
    access_token: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make a request to the Notion API"""
    base_url = "https://api.notion.com/v1"
    url = f"{base_url}/{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    logger.info(f"Making {method} request to Notion API: {url}")
    if json_data:
        logger.info(f"Request data: {json_data}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
            ) as response:
                response_text = await response.text()
                
                if response.status != 200:
                    logger.error(f"Notion API error ({response.status}): {response_text}")
                    return {
                        "error": True,
                        "status": response.status,
                        "message": response_text
                    }
                
                try:
                    result = json.loads(response_text)
                    return result
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse Notion API response: {response_text}")
                    return {
                        "error": True,
                        "status": 500,
                        "message": "Failed to parse Notion API response"
                    }
    except Exception as e:
        logger.error(f"Error making Notion API request: {str(e)}")
        return {
            "error": True,
            "status": 500,
            "message": f"Error making Notion API request: {str(e)}"
        }

# Get all Notion endpoints
@router.get("/endpoints")
async def get_notion_endpoints():
    """
    Get a list of all Notion API endpoints available in Open WebUI
    """
    endpoints = [
        {
            "path": "/api/v1/integrations/notion/status",
            "method": "GET",
            "description": "Check if the current user has an active Notion integration"
        },
        {
            "path": "/api/v1/integrations/notion/disconnect",
            "method": "POST",
            "description": "Disconnect the user's Notion integration"
        },
        {
            "path": "/api/v1/integrations/notion/login",
            "method": "GET",
            "description": "Get the authorization URL for Notion OAuth"
        },
        {
            "path": "/api/v1/integrations/notion/callback",
            "method": "GET",
            "description": "Handle the callback from Notion OAuth"
        },
        {
            "path": "/api/v1/integrations/notion/oauth_info",
            "method": "GET",
            "description": "Get OAuth information for Notion integration"
        },
        {
            "path": "/api/v1/integrations/notion/databases",
            "method": "GET",
            "description": "Get a list of Notion databases for the current user"
        },
        {
            "path": "/api/v1/integrations/notion/databases/{database_id}/query",
            "method": "POST",
            "description": "Query a Notion database"
        },
        {
            "path": "/api/v1/integrations/notion/pages",
            "method": "POST",
            "description": "Create a new page in a Notion database"
        },
        {
            "path": "/api/v1/integrations/notion/pages/{page_id}",
            "method": "PATCH",
            "description": "Update a Notion page"
        },
        {
            "path": "/api/v1/integrations/notion/search",
            "method": "POST",
            "description": "Search Notion for pages, databases, or other content"
        },
        {
            "path": "/api/v1/integrations/notion/endpoints",
            "method": "GET",
            "description": "Get a list of all Notion API endpoints available in Open WebUI"
        }
    ]
    
    return endpoints

@router.get("/status", response_model=NotionStatusResponse)
async def get_notion_status(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    """
    Check if the current user has an active Notion integration
    """
    try:
        # Use the get_db context manager properly
        with get_db() as db:
            # Find user's active Notion integration
            integration = db.query(IntegrationConnection).filter(
                IntegrationConnection.user_id == user.id,
                IntegrationConnection.integration_type == "notion",
                IntegrationConnection.active == True
            ).first()
            
            if integration:
                # Check if we have metadata or integration_metadata field
                metadata = getattr(integration, 'integration_metadata', getattr(integration, 'metadata', {}))
                
                return NotionStatusResponse(
                    integration={
                        "id": integration.id,
                        "integration_type": integration.integration_type,
                        "workspace_name": metadata.get("workspace_name", "Notion Workspace"),
                        "workspace_icon": metadata.get("workspace_icon"),
                        "active": integration.active,
                        "created_at": integration.created_at.isoformat(),
                        "updated_at": integration.updated_at.isoformat()
                    },
                    is_connected=True
                )
            else:
                return NotionStatusResponse(
                    integration=None,
                    is_connected=False
                )
    except Exception as e:
        logger.error(f"Error checking Notion status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking Notion status: {str(e)}")

@router.get("/databases")
async def get_notion_databases(
    user: User = Depends(get_current_user),
):
    """
    Get a list of Notion databases for the current user
    """
    try:
        logger.info(f"Getting Notion databases for user: {user.id}")
        
        # Get the user's active Notion integration
        integration = get_user_integration(user.id, "notion")
        
        # Make the API request to get databases
        result = await notion_api_request(
            endpoint="search",
            access_token=integration.access_token,
            method="POST",
            json_data={"filter": {"value": "database", "property": "object"}}
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=result.get("message", "Unknown error")
            )
        
        # Extract and format database information
        databases = []
        for item in result.get("results", []):
            if item.get("object") == "database":
                title = ""
                for title_item in item.get("title", []):
                    if title_item.get("type") == "text":
                        title += title_item.get("text", {}).get("content", "")
                
                databases.append({
                    "id": item.get("id"),
                    "title": title or "Untitled Database",
                    "url": item.get("url"),
                    "last_edited_time": item.get("last_edited_time"),
                    "properties": item.get("properties")
                })
        
        return databases
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting Notion databases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting Notion databases: {str(e)}")

@router.post("/databases/{database_id}/query")
async def query_notion_database(
    database_id: str,
    filter_data: Dict[str, Any] = Body(default={}),
    user: User = Depends(get_current_user),
):
    """
    Query a Notion database with optional filters
    """
    try:
        # Get the user's active Notion integration
        integration = get_user_integration(user.id, "notion")
        
        # Make the API request to query the database
        result = await notion_api_request(
            endpoint=f"databases/{database_id}/query",
            access_token=integration.access_token,
            method="POST",
            json_data=filter_data
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=result.get("message", "Unknown error")
            )
        
        return result
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error querying Notion database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error querying Notion database: {str(e)}")

@router.post("/pages")
async def create_notion_page(
    page_data: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
):
    """
    Create a new page in a Notion database
    """
    try:
        # Get the user's active Notion integration
        integration = get_user_integration(user.id, "notion")
        
        # Make the API request to create a page
        result = await notion_api_request(
            endpoint="pages",
            access_token=integration.access_token,
            method="POST",
            json_data=page_data
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=result.get("message", "Unknown error")
            )
        
        return result
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating Notion page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating Notion page: {str(e)}")

@router.post("/search")
async def search_notion(
    search_data: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
):
    """
    Search Notion for pages, databases, or other content
    """
    try:
        # Get the user's active Notion integration
        integration = get_user_integration(user.id, "notion")
        
        # Make the API request to search Notion
        result = await notion_api_request(
            endpoint="search",
            access_token=integration.access_token,
            method="POST",
            json_data=search_data
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=result.get("message", "Unknown error")
            )
        
        return result
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error searching Notion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching Notion: {str(e)}") 