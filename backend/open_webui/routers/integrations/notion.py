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

from open_webui.models.users import UserModel as User
from open_webui.models.integrations import IntegrationModel as IntegrationConnection
from open_webui.internal.db import get_db
from open_webui.utils.auth import get_current_user
from open_webui.utils.integrations.notion import (
    get_notion_function_tools, 
    handle_notion_function_execution, 
    format_notion_api_result_for_llm
)
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
    Execute a Notion action with the given parameters
    """
    try:
        logger.info(f"Executing Notion action: {request.action} with params: {request.params}")
        
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
        
        # Call the API using the access token
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        # Map the action to the correct API endpoint
        execution_data = handle_notion_function_execution(
            request.action, 
            request.params
        )
        
        if execution_data.get("action") == "search":
            url = "https://api.notion.com/v1/search"
            data = {
                "query": execution_data.get("params", {}).get("query", ""),
                "sort": execution_data.get("params", {}).get("sort", {"direction": "descending", "timestamp": "last_edited_time"}),
                "filter": execution_data.get("params", {}).get("filter", {"value": "page", "property": "object"})
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return format_notion_api_result_for_llm(result, "search_notion")
                
        elif execution_data.get("action") == "list_databases" or execution_data.get("action") == "list_notion_databases":
            url = "https://api.notion.com/v1/search"
            data = {
                "filter": {"value": "database", "property": "object"}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return format_notion_api_result_for_llm(result, "list_notion_databases")
                
        elif execution_data.get("action") == "query_database":
            database_id = execution_data.get("params", {}).get("database_id")
            if not database_id:
                raise HTTPException(status_code=400, detail="Database ID is required")
                
            url = f"https://api.notion.com/v1/databases/{database_id}/query"
            data = {}
            
            # Add filter if provided
            filter_param = execution_data.get("params", {}).get("filter")
            if filter_param:
                data["filter"] = filter_param
                
            # Add sorts if provided
            sorts_param = execution_data.get("params", {}).get("sorts")
            if sorts_param:
                data["sorts"] = sorts_param
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return format_notion_api_result_for_llm(result, "query_notion_database")
                
        elif execution_data.get("action") == "create_page":
            parent = execution_data.get("params", {}).get("parent")
            properties = execution_data.get("params", {}).get("properties")
            
            if not parent or not properties:
                raise HTTPException(status_code=400, detail="Parent and properties are required")
                
            url = "https://api.notion.com/v1/pages"
            data = {
                "parent": parent,
                "properties": properties
            }
            
            # Add children content if provided
            children = execution_data.get("params", {}).get("children")
            if children:
                data["children"] = children
                
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return format_notion_api_result_for_llm(result, "create_notion_page")
        
        elif execution_data.get("action") == "update_page":
            page_id = execution_data.get("params", {}).get("page_id")
            properties = execution_data.get("params", {}).get("properties")
            
            if not page_id or not properties:
                raise HTTPException(status_code=400, detail="Page ID and properties are required")
                
            url = f"https://api.notion.com/v1/pages/{page_id}"
            data = {
                "properties": properties
            }
            
            # Add archived status if provided
            if execution_data.get("params", {}).get("archived") is not None:
                data["archived"] = execution_data.get("params", {}).get("archived")
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return format_notion_api_result_for_llm(result, "update_notion_page")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error executing Notion action: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error executing Notion action: {str(e)}")

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