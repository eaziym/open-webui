from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, BackgroundTasks
from pydantic import BaseModel
import json
import logging
import httpx
import aiohttp
import secrets
import string
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse
import base64
import os

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

# Custom OAuth manager for Notion
class NotionOAuthManager:
    def __init__(self):
        self.client_id = NOTION_CLIENT_ID.value  # Set from environment/config
        self.client_secret = NOTION_CLIENT_SECRET.value  # Set from environment/config
        self.authorize_endpoint = "https://api.notion.com/v1/oauth/authorize"
        self.token_endpoint = "https://api.notion.com/v1/oauth/token"
        self.redirect_uri = NOTION_REDIRECT_URI.value  # Use config value instead of hardcoded value
        self.scopes = ["read_user", "read_user_bot", "read_databases", "write_databases", "read_pages", "write_pages"]
    
    def generate_state(self) -> str:
        """Generate a random state string for OAuth security"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    def get_authorize_url(self, state: Optional[str] = None) -> str:
        """Get the authorization URL for Notion OAuth"""
        if not state:
            state = self.generate_state()
            
        scope = " ".join(self.scopes)
        return f"{self.authorize_endpoint}?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state={state}&scope={scope}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange the authorization code for an access token"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        # Properly base64 encode the client_id:client_secret for Basic auth
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_b64}"
        }
        
        try:
            logger.info(f"Exchanging code for token with redirect_uri: {self.redirect_uri}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_endpoint,
                    json=data,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error exchanging code for token: {str(e)}")
            return {}

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

notion_oauth_manager = NotionOAuthManager()

class ExecuteRequest(BaseModel):
    action: str
    params: Dict[str, Any] = {}

# Status response model
class NotionStatusResponse(BaseModel):
    integration: Optional[Dict[str, Any]] = None
    is_connected: bool = False

@router.post("/execute")
async def execute_notion_action(
    request: ExecuteRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    """
    Return information about Notion API endpoints without executing actions.
    """
    try:
        logger.info(f"Received Notion action request: {request.action} with params: {request.params}")
        
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
                "endpoint": "databases",
                "method": "GET",
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
        
        if request.action and request.action in available_endpoints:
            return {
                "message": "This endpoint now only provides information about API endpoints without executing actions.",
                "requested_action": request.action,
                "endpoint_info": available_endpoints[request.action]
            }
        else:
            return {
                "message": "This endpoint now only provides information about API endpoints without executing actions.",
                "available_endpoints": available_endpoints
            }
            
    except Exception as e:
        logger.error(f"Error handling Notion action request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error handling Notion action request: {str(e)}")

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

@router.post("/disconnect")
async def disconnect_notion(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    """
    Disconnect the user's Notion integration
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
            
            if not integration:
                raise HTTPException(status_code=400, detail="No active Notion integration found")
                
            # Deactivate the integration
            integration.active = False
            db.commit()
        
        return {"status": "success", "message": "Notion integration disconnected successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error disconnecting Notion integration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error disconnecting Notion integration: {str(e)}")

@router.get("/login")
async def login_to_notion(request: Request):
    """
    Get the authorization URL for Notion OAuth
    """
    try:
        # Generate a random state for security
        state = notion_oauth_manager.generate_state()
        
        # Get the authorization URL
        auth_url = notion_oauth_manager.get_authorize_url(state)
        
        # Store the state in the session
        # Note: This implementation depends on your session handling
        
        return {"auth_url": auth_url, "authorization_url": auth_url}
    except Exception as e:
        logger.error(f"Error getting Notion login URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting Notion login URL: {str(e)}")

@router.get("/callback")
async def notion_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    user: User = Depends(get_current_user),
):
    """
    Handle the callback from Notion OAuth
    """
    try:
        logger.info(f"Received Notion callback with code: {code[:5]}... and state: {state[:5]}...")
        
        # Exchange the code for an access token
        logger.info("Exchanging code for access token...")
        token_response = await notion_oauth_manager.exchange_code_for_token(code)
        
        if not token_response:
            logger.error("No response received from token exchange")
            raise HTTPException(status_code=400, detail="Failed to get access token - No response from Notion")
            
        if "access_token" not in token_response:
            logger.error(f"No access_token in response: {token_response}")
            error_detail = token_response.get("error_description", token_response.get("error", "Unknown error"))
            raise HTTPException(status_code=400, detail=f"Failed to get access token: {error_detail}")
            
        access_token = token_response["access_token"]
        workspace_id = token_response.get("workspace_id")
        workspace_name = token_response.get("workspace_name")
        workspace_icon = token_response.get("workspace_icon")
        
        logger.info(f"Successfully obtained access token for workspace: {workspace_name}")
        
        # Use the get_db context manager properly
        with get_db() as db:
            # Check if an active integration already exists
            existing_integration = db.query(IntegrationConnection).filter(
                IntegrationConnection.user_id == user.id,
                IntegrationConnection.integration_type == "notion",
                IntegrationConnection.active == True
            ).first()
            
            if existing_integration:
                # Update the existing integration
                logger.info(f"Updating existing Notion integration for user: {user.id}")
                existing_integration.access_token = access_token
                existing_integration.metadata = {
                    "workspace_id": workspace_id,
                    "workspace_name": workspace_name,
                    "workspace_icon": workspace_icon
                }
                db.commit()
            else:
                # Create a new integration
                logger.info(f"Creating new Notion integration for user: {user.id}")
                new_integration = IntegrationConnection(
                    user_id=user.id,
                    integration_type="notion",
                    access_token=access_token,
                    active=True,
                    metadata={
                        "workspace_id": workspace_id,
                        "workspace_name": workspace_name,
                        "workspace_icon": workspace_icon
                    }
                )
                db.add(new_integration)
                db.commit()
        
        # Redirect to the application's integrations page
        logger.info("Redirecting user to integrations page")
        
        # Get the host from the original request
        host = request.headers.get("host", "localhost:8080")
        # If the port is 8080 (API server), we need to redirect to the frontend port
        # For a production deployment, the host might already have the correct frontend URL
        if host.endswith(":8080"):
            # Use port 5173 which is typical for Vite/SvelteKit dev server
            frontend_host = host.replace(":8080", ":5173")
            protocol = "http"  # In development, typically using http
        else:
            # In production, keep the same host
            frontend_host = host
            # In production, we're typically using https
            protocol = "https" if not host.startswith("localhost") else "http"
            
        frontend_url = f"{protocol}://{frontend_host}/integrations"
        logger.info(f"Redirecting to frontend URL: {frontend_url}")
        return RedirectResponse(url=frontend_url)
    except HTTPException as e:
        logger.error(f"HTTP exception in Notion callback: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Error handling Notion callback: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error handling Notion callback: {str(e)}")

@router.get("/oauth_info")
async def get_oauth_info(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    """Get OAuth information for Notion integration"""
    return {
        "client_id": notion_oauth_manager.client_id,
        "authorize_url": notion_oauth_manager.get_authorize_url(),
        "scopes": notion_oauth_manager.scopes
    }

@router.get("/databases")
async def get_notion_databases(
    user: User = Depends(get_current_user),
):
    """
    Get a list of Notion databases for the current user
    """
    try:
        logger.info(f"Getting Notion databases for user: {user.id}")
        
        # Use the get_db context manager properly
        with get_db() as db:
            # Find user's active Notion integration
            integration = db.query(IntegrationConnection).filter(
                IntegrationConnection.user_id == user.id,
                IntegrationConnection.integration_type == "notion",
                IntegrationConnection.active == True
            ).first()
            
            if not integration:
                raise HTTPException(status_code=400, detail="No active Notion integration found")
            
            # Get the access token
            access_token = integration.access_token
        
        # Call the Notion API to search for databases
        url = "https://api.notion.com/v1/search"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        data = {
            "filter": {"value": "database", "property": "object"}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code != 200:
                logger.error(f"Notion API error ({response.status_code}): {response.text}")
                raise HTTPException(status_code=response.status_code, detail=f"Notion API error: {response.text}")
            
            result = response.json()
            
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

# Request and response models for new endpoints
class QueryDatabaseRequest(BaseModel):
    filter: Optional[Dict[str, Any]] = None
    sorts: Optional[List[Dict[str, Any]]] = None
    page_size: Optional[int] = 100
    start_cursor: Optional[str] = None

class CreatePageRequest(BaseModel):
    parent: Dict[str, Any]  # Required: database_id or page_id
    properties: Dict[str, Any]  # Required
    children: Optional[List[Dict[str, Any]]] = None  # Optional content blocks
    icon: Optional[Dict[str, Any]] = None
    cover: Optional[Dict[str, Any]] = None

class UpdatePageRequest(BaseModel):
    properties: Dict[str, Any]
    archived: Optional[bool] = None

class CommentRequest(BaseModel):
    parent: Dict[str, str]  # Required: page_id or block_id
    rich_text: List[Dict[str, Any]]  # Required: comment content

class BlockRequest(BaseModel):
    children: List[Dict[str, Any]]

class UpdateBlockRequest(BaseModel):
    block_data: Dict[str, Any]

class SearchRequest(BaseModel):
    query: Optional[str] = None
    sort: Optional[Dict[str, Any]] = None
    filter: Optional[Dict[str, Any]] = None
    page_size: Optional[int] = 100
    start_cursor: Optional[str] = None

# HELPER FUNCTION: Get integration access token
async def get_notion_access_token(user: User) -> str:
    """Helper function to get the user's Notion access token"""
    with get_db() as db:
        integration = db.query(IntegrationConnection).filter(
            IntegrationConnection.user_id == user.id,
            IntegrationConnection.integration_type == "notion",
            IntegrationConnection.active == True
        ).first()
        
        if not integration:
            raise HTTPException(status_code=400, detail="No active Notion integration found")
        
        return integration.access_token

# DATABASE ENDPOINTS
@router.post("/databases/{database_id}/query")
async def query_notion_database(
    database_id: str,
    query_request: QueryDatabaseRequest,
    user: User = Depends(get_current_user),
):
    """
    Query a specific Notion database with filters and sorting options
    """
    try:
        logger.info(f"Querying Notion database {database_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Prepare the request data
        data = {}
        if query_request.filter:
            data["filter"] = query_request.filter
        if query_request.sorts:
            data["sorts"] = query_request.sorts
        if query_request.page_size:
            data["page_size"] = query_request.page_size
        if query_request.start_cursor:
            data["start_cursor"] = query_request.start_cursor
            
        # Make the API request
        result = await notion_api_request(
            f"databases/{database_id}/query",
            access_token=access_token,
            method="POST",
            json_data=data
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error querying Notion database: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error querying Notion database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error querying Notion database: {str(e)}")

@router.get("/databases/{database_id}")
async def get_notion_database(
    database_id: str,
    user: User = Depends(get_current_user),
):
    """
    Retrieve a specific Notion database by ID
    """
    try:
        logger.info(f"Getting Notion database {database_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Make the API request
        result = await notion_api_request(
            f"databases/{database_id}",
            access_token=access_token
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error retrieving Notion database: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving Notion database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving Notion database: {str(e)}")

# PAGE ENDPOINTS
@router.post("/pages")
async def create_notion_page(
    page_request: CreatePageRequest,
    user: User = Depends(get_current_user),
):
    """
    Create a new page in Notion
    """
    try:
        logger.info(f"Creating new Notion page for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Validate required fields
        if not page_request.parent or not page_request.properties:
            raise HTTPException(status_code=400, detail="Missing required fields: parent and properties")
        
        # Prepare the request data
        data = {
            "parent": page_request.parent,
            "properties": page_request.properties
        }
        
        if page_request.children:
            data["children"] = page_request.children
        if page_request.icon:
            data["icon"] = page_request.icon
        if page_request.cover:
            data["cover"] = page_request.cover
            
        # Make the API request
        result = await notion_api_request(
            "pages",
            access_token=access_token,
            method="POST",
            json_data=data
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error creating Notion page: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating Notion page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating Notion page: {str(e)}")

@router.get("/pages/{page_id}")
async def get_notion_page(
    page_id: str,
    user: User = Depends(get_current_user),
):
    """
    Retrieve a specific Notion page by ID
    """
    try:
        logger.info(f"Getting Notion page {page_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Make the API request
        result = await notion_api_request(
            f"pages/{page_id}",
            access_token=access_token
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error retrieving Notion page: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving Notion page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving Notion page: {str(e)}")

@router.patch("/pages/{page_id}")
async def update_notion_page(
    page_id: str,
    update_request: UpdatePageRequest,
    user: User = Depends(get_current_user),
):
    """
    Update an existing Notion page
    """
    try:
        logger.info(f"Updating Notion page {page_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Prepare the request data
        data = {"properties": update_request.properties}
        if update_request.archived is not None:
            data["archived"] = update_request.archived
            
        # Make the API request
        result = await notion_api_request(
            f"pages/{page_id}",
            access_token=access_token,
            method="PATCH",
            json_data=data
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error updating Notion page: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating Notion page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating Notion page: {str(e)}")

@router.get("/pages/{page_id}/properties/{property_id}")
async def get_page_property(
    page_id: str,
    property_id: str,
    user: User = Depends(get_current_user),
):
    """
    Retrieve a specific property of a Notion page
    """
    try:
        logger.info(f"Getting property {property_id} of page {page_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Make the API request
        result = await notion_api_request(
            f"pages/{page_id}/properties/{property_id}",
            access_token=access_token
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error retrieving page property: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving page property: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving page property: {str(e)}")

# BLOCK ENDPOINTS
@router.get("/blocks/{block_id}")
async def get_notion_block(
    block_id: str,
    user: User = Depends(get_current_user),
):
    """
    Retrieve a specific Notion block by ID
    """
    try:
        logger.info(f"Getting Notion block {block_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Make the API request
        result = await notion_api_request(
            f"blocks/{block_id}",
            access_token=access_token
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error retrieving Notion block: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving Notion block: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving Notion block: {str(e)}")

@router.get("/blocks/{block_id}/children")
async def get_block_children(
    block_id: str,
    start_cursor: Optional[str] = None,
    page_size: Optional[int] = 100,
    user: User = Depends(get_current_user),
):
    """
    Retrieve the children of a specific Notion block
    """
    try:
        logger.info(f"Getting children of block {block_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Prepare parameters
        params = {}
        if start_cursor:
            params["start_cursor"] = start_cursor
        if page_size:
            params["page_size"] = page_size
            
        # Make the API request
        result = await notion_api_request(
            f"blocks/{block_id}/children",
            access_token=access_token,
            params=params
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error retrieving block children: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving block children: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving block children: {str(e)}")

@router.patch("/blocks/{block_id}/children")
async def append_block_children(
    block_id: str,
    block_request: BlockRequest,
    user: User = Depends(get_current_user),
):
    """
    Append new children blocks to a specific Notion block
    """
    try:
        logger.info(f"Appending children to block {block_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Validate required fields
        if not block_request.children:
            raise HTTPException(status_code=400, detail="Missing required field: children")
            
        # Make the API request
        result = await notion_api_request(
            f"blocks/{block_id}/children",
            access_token=access_token,
            method="PATCH",
            json_data={"children": block_request.children}
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error appending block children: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error appending block children: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error appending block children: {str(e)}")

@router.patch("/blocks/{block_id}")
async def update_notion_block(
    block_id: str,
    update_request: UpdateBlockRequest,
    user: User = Depends(get_current_user),
):
    """
    Update a specific Notion block
    """
    try:
        logger.info(f"Updating block {block_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Validate request
        if not update_request.block_data:
            raise HTTPException(status_code=400, detail="Missing required field: block_data")
            
        # Make the API request
        result = await notion_api_request(
            f"blocks/{block_id}",
            access_token=access_token,
            method="PATCH",
            json_data=update_request.block_data
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error updating block: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating block: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating block: {str(e)}")

@router.delete("/blocks/{block_id}")
async def delete_notion_block(
    block_id: str,
    user: User = Depends(get_current_user),
):
    """
    Delete a specific Notion block (sets the archived property to true)
    """
    try:
        logger.info(f"Deleting block {block_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Make the API request
        result = await notion_api_request(
            f"blocks/{block_id}",
            access_token=access_token,
            method="DELETE"
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error deleting block: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting block: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting block: {str(e)}")

# SEARCH ENDPOINT
@router.post("/search")
async def search_notion(
    search_request: SearchRequest,
    user: User = Depends(get_current_user),
):
    """
    Search for Notion content (pages and databases)
    """
    try:
        logger.info(f"Searching Notion content for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Prepare the request data
        data = {}
        if search_request.query:
            data["query"] = search_request.query
        if search_request.sort:
            data["sort"] = search_request.sort
        if search_request.filter:
            data["filter"] = search_request.filter
        if search_request.page_size:
            data["page_size"] = search_request.page_size
        if search_request.start_cursor:
            data["start_cursor"] = search_request.start_cursor
            
        # Make the API request
        result = await notion_api_request(
            "search",
            access_token=access_token,
            method="POST",
            json_data=data
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error searching Notion: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error searching Notion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching Notion: {str(e)}")

# USER ENDPOINTS
@router.get("/users")
async def list_notion_users(
    user: User = Depends(get_current_user),
):
    """
    List all users in the current Notion workspace
    """
    try:
        logger.info(f"Listing Notion users for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Make the API request
        result = await notion_api_request(
            "users",
            access_token=access_token
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error listing Notion users: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error listing Notion users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing Notion users: {str(e)}")

@router.get("/users/{user_id}")
async def get_notion_user(
    notion_user_id: str,
    user: User = Depends(get_current_user),
):
    """
    Retrieve a specific Notion user by ID
    """
    try:
        logger.info(f"Getting Notion user {notion_user_id} for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Make the API request
        result = await notion_api_request(
            f"users/{notion_user_id}",
            access_token=access_token
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error retrieving Notion user: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving Notion user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving Notion user: {str(e)}")

@router.get("/users/me")
async def get_my_notion_user(
    user: User = Depends(get_current_user),
):
    """
    Retrieve the current bot user in Notion
    """
    try:
        logger.info(f"Getting bot user for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Make the API request
        result = await notion_api_request(
            "users/me",
            access_token=access_token
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error retrieving bot user: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving bot user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving bot user: {str(e)}")

# COMMENT ENDPOINTS
@router.post("/comments")
async def create_notion_comment(
    comment_request: CommentRequest,
    user: User = Depends(get_current_user),
):
    """
    Create a new comment in Notion
    """
    try:
        logger.info(f"Creating new Notion comment for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Validate required fields
        if not comment_request.parent or not comment_request.rich_text:
            raise HTTPException(status_code=400, detail="Missing required fields: parent and rich_text")
            
        # Make the API request
        result = await notion_api_request(
            "comments",
            access_token=access_token,
            method="POST",
            json_data={
                "parent": comment_request.parent,
                "rich_text": comment_request.rich_text
            }
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error creating Notion comment: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating Notion comment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating Notion comment: {str(e)}")

@router.get("/comments")
async def get_notion_comments(
    block_id: Optional[str] = None,
    page_id: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """
    Retrieve comments for a block or page in Notion
    """
    try:
        logger.info(f"Getting Notion comments for user: {user.id}")
        access_token = await get_notion_access_token(user)
        
        # Validate parameters
        if not block_id and not page_id:
            raise HTTPException(status_code=400, detail="At least one of block_id or page_id is required")
            
        # Prepare parameters
        params = {}
        if block_id:
            params["block_id"] = block_id
        if page_id:
            params["page_id"] = page_id
            
        # Make the API request
        result = await notion_api_request(
            "comments",
            access_token=access_token,
            params=params
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=f"Error retrieving Notion comments: {result.get('message')}"
            )
            
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving Notion comments: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving Notion comments: {str(e)}") 