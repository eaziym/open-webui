import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

import aiohttp
import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import base64

# Make router available for import
__all__ = ["router"]

from open_webui.config import (
    ENABLE_INTEGRATIONS,
    AVAILABLE_INTEGRATIONS,
    NOTION_CLIENT_ID,
    NOTION_CLIENT_SECRET,
    NOTION_REDIRECT_URI,
)
from open_webui.models.integrations import (
    Integrations,
    IntegrationModel,
    IntegrationResponseModel,
    IntegrationListResponse,
    NotionDatabase,
    NotionPage,
    NotionQueryResult,
    IntegrationError,
    IntegrationDetails,
)
from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user
from open_webui.internal.db import SessionLocal

# Setup router
router = APIRouter()
log = logging.getLogger(__name__)

# Define a simple Response schema for the notion_execute endpoint
class Response(BaseModel):
    result: Optional[Any] = None
    detail: Optional[str] = None


# Helper function to check if integrations are enabled
def check_integrations_enabled():
    """Verify that integrations are enabled in the application."""
    if not ENABLE_INTEGRATIONS.value:
        raise HTTPException(
            status_code=403, 
            detail="Integrations are not enabled for this server."
        )


# Helper function to get and validate integration
def get_user_integration(user_id: str, integration_type: str) -> IntegrationModel:
    """Get and validate a user's integration.
    
    Args:
        user_id: User ID
        integration_type: Type of integration (e.g., "notion")
        
    Returns:
        IntegrationModel: The integration model
        
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
    enabled = integration_config.get("enabled", False)
    if hasattr(enabled, "value"):
        enabled = enabled.value
    if not enabled:
        raise HTTPException(
            status_code=400,
            detail=f"Integration '{integration_type}' is not enabled on this server."
        )
    
    # Create a new database session
    db = SessionLocal()
    
    try:
        # Get user's integration
        integration = db.query(IntegrationModel).filter(
            IntegrationModel.user_id == user_id,
            IntegrationModel.integration_type == integration_type,
            IntegrationModel.active == True
        ).first()
        
        if not integration:
            raise HTTPException(
                status_code=404,
                detail=f"No active {integration_type} integration found for this user."
            )
        
        return integration
    finally:
        # Always close the database session
        db.close()


# Helper function to extract values from PersistentConfig objects
def extract_persistent_config_values(obj):
    """Recursively extract values from PersistentConfig objects."""
    if hasattr(obj, "value") and hasattr(obj, "env_name") and hasattr(obj, "config_path"):
        # This looks like a PersistentConfig object
        return obj.value
    elif isinstance(obj, dict):
        return {k: extract_persistent_config_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [extract_persistent_config_values(item) for item in obj]
    else:
        return obj


# Routes
@router.get(
    "/",
    description="List all available integrations and the user's connected integrations",
)
async def list_integrations(user: UserModel = Depends(get_verified_user)):
    """List all available integrations and the user's connected integrations."""
    try:
        log.info("Starting list_integrations function")
        check_integrations_enabled()
        
        # Get user's integrations
        log.info("Fetching user integrations")
        user_integrations = Integrations.get_user_integrations(user.id)
        
        # Format connected integrations
        log.info("Formatting connected integrations")
        connected_integrations = []
        for integration in user_integrations:
            if integration.active:
                connected_integrations.append({
                    "id": integration.id,
                    "integration_type": integration.integration_type,
                    "workspace_name": integration.workspace_name,
                    "workspace_icon": integration.workspace_icon,
                    "active": integration.active,
                    "created_at": integration.created_at.isoformat() if integration.created_at else None,
                    "updated_at": integration.updated_at.isoformat() if integration.updated_at else None,
                })
        
        # Format available integrations
        log.info("Formatting available integrations")
        available_integrations = {}
        
        # Process AVAILABLE_INTEGRATIONS to extract values from PersistentConfig objects
        processed_available_integrations = extract_persistent_config_values(AVAILABLE_INTEGRATIONS)
        
        # Handle Notion integration
        if "notion" in processed_available_integrations:
            notion_config = processed_available_integrations["notion"]
            notion_enabled = notion_config.get("enabled")
                
            available_integrations["notion"] = {
                "name": "Notion",
                "description": "Connect to Notion to access your databases and pages",
                "icon": "/static/integrations/notion.png",
                "enabled": notion_enabled
            }
        
        # Process ENABLE_INTEGRATIONS to extract value if it's a PersistentConfig
        enable_integrations = extract_persistent_config_values(ENABLE_INTEGRATIONS)
        
        log.info("Returning response")
        return {
            "available": available_integrations,
            "connected": connected_integrations,
            "enabled": enable_integrations
        }
    except Exception as e:
        log.error(f"Error in list_integrations: {str(e)}")
        import traceback
        log.error(traceback.format_exc())
        raise


# Notion-specific routes
@router.get(
    "/notion/login",
    description="Start the Notion OAuth flow",
)
async def notion_login(request: Request, user=Depends(get_verified_user)):
    """Start the Notion OAuth flow."""
    check_integrations_enabled()
    
    # Get app state and process with extract_persistent_config_values
    available_integrations = extract_persistent_config_values(request.app.state.AVAILABLE_INTEGRATIONS)
    
    # Check if Notion integration is enabled
    if "notion" not in available_integrations:
        raise HTTPException(
            status_code=400,
            detail="Notion integration is not enabled on this server."
        )
    
    enabled = available_integrations["notion"]["enabled"]
    if not enabled:
        raise HTTPException(
            status_code=400,
            detail="Notion integration is not enabled on this server."
        )
    
    # Generate state parameter to prevent CSRF
    state = str(uuid.uuid4())
    
    # Get client_id and redirect_uri, accessing values with the helper function
    client_id = extract_persistent_config_values(request.app.state.NOTION_CLIENT_ID)
    redirect_uri = extract_persistent_config_values(request.app.state.NOTION_REDIRECT_URI)
    
    log.info(f"Building authorization URL with client_id={client_id}, redirect_uri={redirect_uri}")
    
    # Build the authorization URL
    auth_url = (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&owner=user"
        f"&state={state}"
    )
    
    log.info(f"Authorization URL: {auth_url}")
    return {"authorization_url": auth_url, "state": state}


@router.get("/notion/callback")
async def notion_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    user: UserModel = Depends(get_verified_user)
):
    """Handle the OAuth callback from Notion."""
    check_integrations_enabled()
    
    try:
        # Exchange the authorization code for an access token
        token_url = "https://api.notion.com/v1/oauth/token"
        
        # Get client_id and client_secret using the helper function
        client_id = extract_persistent_config_values(request.app.state.NOTION_CLIENT_ID)
        client_secret = extract_persistent_config_values(request.app.state.NOTION_CLIENT_SECRET)
        
        log.info(f"Using client_id={client_id} and client_secret (hidden) for token exchange")
        
        # Basic auth using client_id and client_secret
        auth_string = f"{client_id}:{client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
        }
        
        # Get redirect_uri using the helper function
        redirect_uri = extract_persistent_config_values(request.app.state.NOTION_REDIRECT_URI)
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        
        log.info(f"Making token request to Notion with redirect_uri={redirect_uri}")
        response = requests.post(token_url, headers=headers, json=payload)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        workspace_id = token_data.get("workspace_id")
        workspace_name = token_data.get("workspace_name")
        workspace_icon = token_data.get("workspace_icon")
        
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="Failed to obtain access token from Notion."
            )
        
        # Calculate token expiry (default: 8 hours from now if not provided)
        token_expires_at = None
        if token_data.get("expires_in"):
            token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in"))
        
        # Create the integration
        integration = Integrations.create_integration(
            user_id=user.id,
            integration_type="notion",
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),
            token_expires_at=token_expires_at,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            workspace_icon=workspace_icon,
            integration_metadata=token_data,
        )
        
        return {
            "success": True,
            "integration_id": integration.id,
            "workspace_name": workspace_name,
        }
        
    except requests.exceptions.RequestException as e:
        log.error(f"Error during Notion OAuth: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to Notion: {str(e)}"
        )


@router.get(
    "/notion/databases",
    response_model=List[NotionDatabase],
    description="List all Notion databases for a user",
)
async def list_notion_databases(
    user: UserModel = Depends(get_verified_user),
):
    """List all Notion databases for a user."""
    try:
        check_integrations_enabled()
        
        # Create a new database session
        db = SessionLocal()
        
        try:
            # Find the user's active Notion integration
            integration = db.query(IntegrationModel).filter(
                IntegrationModel.user_id == user.id,
                IntegrationModel.integration_type == "notion",
                IntegrationModel.active == True
            ).first()
            
            if not integration:
                raise HTTPException(
                    status_code=404,
                    detail="No active Notion integration found"
                )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.notion.com/v1/search",
                    headers={
                        "Authorization": f"Bearer {integration.access_token}",
                        "Notion-Version": "2022-06-28",
                        "Content-Type": "application/json",
                    },
                    json={
                        "filter": {"value": "database", "property": "object"},
                        "page_size": 100,
                    }
                ) as response:
                    if response.status != 200:
                        detail = await response.text()
                        log.error(f"Notion API error: {detail}")
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Notion API error: {detail}"
                        )
                    
                    data = await response.json()
                    
                    databases = []
                    for result in data.get("results", []):
                        if result.get("object") == "database":
                            title = ""
                            if result.get("title"):
                                for title_part in result.get("title", []):
                                    if title_part.get("type") == "text":
                                        title += title_part.get("text", {}).get("content", "")
                            
                            db_instance = NotionDatabase(
                                id=result.get("id"),
                                title=title or "Untitled Database",
                                url=result.get("url"),
                                last_edited_time=result.get("last_edited_time"),
                                properties=result.get("properties"),
                            )
                            databases.append(db_instance)
                    
                    return databases
        finally:
            # Always close the database session
            db.close()
    except Exception as e:
        log.error(f"Error listing Notion databases: {str(e)}")
        log.error(f"Error details: {repr(e)}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error listing Notion databases: {str(e)}")


@router.get(
    "/notion/databases/{database_id}",
    response_model=NotionDatabase,
    description="Get a specific Notion database",
)
async def get_notion_database(
    database_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """Get a specific Notion database."""
    try:
        check_integrations_enabled()
        
        # Create a new database session
        db = SessionLocal()
        
        try:
            # Find the user's active Notion integration
            integration = db.query(IntegrationModel).filter(
                IntegrationModel.user_id == user.id,
                IntegrationModel.integration_type == "notion",
                IntegrationModel.active == True
            ).first()
            
            if not integration:
                raise HTTPException(
                    status_code=404,
                    detail="No active Notion integration found"
                )
                
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.notion.com/v1/databases/{database_id}",
                    headers={
                        "Authorization": f"Bearer {integration.access_token}",
                        "Notion-Version": "2022-06-28",
                    }
                ) as response:
                    if response.status != 200:
                        detail = await response.text()
                        log.error(f"Notion API error: {detail}")
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Notion API error: {detail}"
                        )
                    
                    data = await response.json()
                    
                    title = ""
                    if data.get("title"):
                        for title_part in data.get("title", []):
                            if title_part.get("type") == "text":
                                title += title_part.get("text", {}).get("content", "")
                    
                    db_info = NotionDatabase(
                        id=data.get("id"),
                        title=title or "Untitled Database",
                        url=data.get("url"),
                        last_edited_time=data.get("last_edited_time"),
                        properties=data.get("properties"),
                    )
                    
                    return db_info
        finally:
            # Always close the database session
            db.close()
    except Exception as e:
        log.error(f"Error getting Notion database: {str(e)}")
        log.error(f"Error details: {repr(e)}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error getting Notion database: {str(e)}")


@router.post(
    "/notion/databases/{database_id}/query",
    response_model=NotionQueryResult,
    description="Query a specific Notion database",
)
async def query_notion_database(
    database_id: str,
    query_params: Dict[str, Any],
    user: UserModel = Depends(get_verified_user),
):
    """Query a specific Notion database."""
    try:
        check_integrations_enabled()
        
        # Create a new database session
        db = SessionLocal()
        
        try:
            # Find the user's active Notion integration
            integration = db.query(IntegrationModel).filter(
                IntegrationModel.user_id == user.id,
                IntegrationModel.integration_type == "notion",
                IntegrationModel.active == True
            ).first()
            
            if not integration:
                raise HTTPException(
                    status_code=404,
                    detail="No active Notion integration found"
                )
                
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://api.notion.com/v1/databases/{database_id}/query",
                    headers={
                        "Authorization": f"Bearer {integration.access_token}",
                        "Notion-Version": "2022-06-28",
                        "Content-Type": "application/json",
                    },
                    json=query_params
                ) as response:
                    if response.status != 200:
                        detail = await response.text()
                        log.error(f"Notion API error: {detail}")
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Notion API error: {detail}"
                        )
                    
                    data = await response.json()
                    return NotionQueryResult(
                        object=data.get("object", "list"),
                        results=data.get("results", []),
                        has_more=data.get("has_more", False),
                        next_cursor=data.get("next_cursor")
                    )
        finally:
            # Always close the database session
            db.close()
    except Exception as e:
        log.error(f"Error querying Notion database: {str(e)}")
        log.error(f"Error details: {repr(e)}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error querying Notion database: {str(e)}")


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
    
    log.info(f"Making {method} request to Notion API: {url}")
    if json_data:
        log.info(f"Request data: {json_data}")
    
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
                    log.error(f"Notion API error ({response.status}): {response_text}")
                    return {
                        "error": True,
                        "status": response.status,
                        "message": response_text
                    }
                
                try:
                    result = json.loads(response_text)
                    return result
                except json.JSONDecodeError:
                    log.error(f"Failed to parse Notion API response: {response_text}")
                    return {
                        "error": True,
                        "status": 500,
                        "message": "Failed to parse Notion API response"
                    }
    except Exception as e:
        log.error(f"Error making Notion API request: {str(e)}")
        return {
            "error": True,
            "status": 500,
            "message": f"Error making Notion API request: {str(e)}"
        }


@router.post("/notion/execute", response_model=Response)
async def notion_execute(
    request: Request,
    action_data: Dict[str, Any],
    user: UserModel = Depends(get_verified_user),
):
    """Return information about Notion API endpoints without executing actions."""
    log.info(f"Received Notion action request: {action_data}")
    
    # List of available Notion API endpoints integrated with Open WebUI
    available_endpoints = {
        "search": {
            "description": "Search for Notion content",
            "endpoint": "search",
            "method": "POST",
            "params": ["query", "filter", "sort"]
        },
        "list_databases": {
            "description": "List all Notion databases",
            "endpoint": "search with database filter",
            "method": "POST",
            "params": []
        },
        "query_database": {
            "description": "Query a specific Notion database",
            "endpoint": "databases/{database_id}/query",
            "method": "POST",
            "params": ["database_id", "filter", "sorts"]
        },
        "create_page": {
            "description": "Create a new page in Notion",
            "endpoint": "pages",
            "method": "POST",
            "params": ["parent", "properties", "children"]
        },
        "update_page": {
            "description": "Update an existing page in Notion",
            "endpoint": "pages/{page_id}",
            "method": "PATCH",
            "params": ["page_id", "properties", "archived"]
        }
    }
    
    action = action_data.get("action", "")
    
    if action and action in available_endpoints:
        return Response(result={
            "message": "This endpoint now only provides information about API endpoints without executing actions.",
            "requested_action": action,
            "endpoint_info": available_endpoints[action]
        })
    else:
        return Response(result={
            "message": "This endpoint now only provides information about API endpoints without executing actions.",
            "available_endpoints": available_endpoints
        })


@router.delete(
    "/{integration_id}",
    description="Delete an integration",
)
async def delete_integration(
    integration_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """Delete an integration."""
    try:
        check_integrations_enabled()
        
        # Create a new database session
        db = SessionLocal()
        
        try:
            # Get the integration by ID, ensuring it belongs to the user
            integration = db.query(IntegrationModel).filter(
                IntegrationModel.id == integration_id,
                IntegrationModel.user_id == user.id
            ).first()
            
            if not integration:
                raise HTTPException(
                    status_code=404,
                    detail="Integration not found"
                )
            
            # Delete the integration
            db.delete(integration)
            db.commit()
            
            return {"success": True}
        finally:
            # Always close the database session
            db.close()
    except HTTPException as e:
        raise e
    except Exception as e:
        log.error(f"Error deleting integration: {str(e)}")
        log.error(f"Error details: {repr(e)}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error deleting integration: {str(e)}")


# Define response models for the status endpoint
class NotionStatusResponse(BaseModel):
    integration: Optional[IntegrationResponseModel] = None
    is_connected: bool = False

@router.get(
    "/notion/status",
    response_model=NotionStatusResponse,
    description="Get the status of the user's Notion integration",
)
async def notion_status(
    user: UserModel = Depends(get_verified_user),
):
    """Get the status of the user's Notion integration."""
    try:
        check_integrations_enabled()
        
        # Create a new database session
        db = SessionLocal()
        
        try:
            # Find the user's active Notion integration
            integration = db.query(IntegrationModel).filter(
                IntegrationModel.user_id == user.id,
                IntegrationModel.integration_type == "notion",
                IntegrationModel.active == True
            ).first()
            
            if integration:
                # Format the integration data
                integration_data = IntegrationResponseModel(
                    id=integration.id,
                    integration_type=integration.integration_type,
                    workspace_name=integration.workspace_name,
                    workspace_icon=integration.workspace_icon,
                    active=integration.active,
                    created_at=integration.created_at,
                    updated_at=integration.updated_at,
                )
                
                return NotionStatusResponse(
                    integration=integration_data,
                    is_connected=True,
                )
            else:
                return NotionStatusResponse(is_connected=False)
        finally:
            # Always close the database session
            db.close()
    except Exception as e:
        log.error(f"Error getting Notion status: {str(e)}")
        log.error(f"Error details: {repr(e)}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")
        return NotionStatusResponse(is_connected=False)


@router.post(
    "/notion/disconnect", 
    description="Disconnect the user's Notion integration"
)
async def disconnect_notion(
    user: UserModel = Depends(get_verified_user),
):
    """Disconnect the user's Notion integration."""
    try:
        log.info(f"Disconnecting Notion integration for user {user.id}")
        check_integrations_enabled()
        
        # Create a new database session
        db = SessionLocal()
        
        try:
            # Find the user's active Notion integration
            integration = db.query(IntegrationModel).filter(
                IntegrationModel.user_id == user.id,
                IntegrationModel.integration_type == "notion",
                IntegrationModel.active == True
            ).first()
            
            if not integration:
                raise HTTPException(
                    status_code=404,
                    detail="No active Notion integration found"
                )
            
            # Deactivate the integration
            integration.active = False
            db.commit()
            
            return {"status": "success", "message": "Notion integration disconnected successfully"}
        finally:
            # Always close the database session
            db.close()
            
    except HTTPException as e:
        raise e
    except Exception as e:
        log.error(f"Error disconnecting Notion integration: {str(e)}")
        log.error(f"Error details: {repr(e)}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error disconnecting Notion integration: {str(e)}") 