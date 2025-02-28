# Import routes
from fastapi import APIRouter, Depends, Request, HTTPException
from . import notion
from open_webui.config import AVAILABLE_INTEGRATIONS, ENABLE_INTEGRATIONS
from open_webui.utils.auth import get_current_user
from open_webui.models.integrations import Integrations
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create a router for the integrations package
router = APIRouter()

# Include sub-routers
router.include_router(notion.router)

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

# Add a root endpoint that returns available integrations
@router.get("/", tags=["integrations"])
async def get_available_integrations(request: Request, user=Depends(get_current_user)):
    """
    Get information about available integrations
    """
    try:
        # Get user's connected integrations
        user_integrations = Integrations.get_user_integrations(user.id)
        
        # Format the response to match what the frontend expects
        connected_integrations = []
        for integration in user_integrations:
            # Check if integration has direct fields or data is in integration_metadata
            workspace_name = getattr(integration, 'workspace_name', None)
            workspace_icon = getattr(integration, 'workspace_icon', None)
            
            # If these fields are None, try to get from integration_metadata
            if workspace_name is None and hasattr(integration, 'integration_metadata') and integration.integration_metadata:
                workspace_name = integration.integration_metadata.get("workspace_name", "")
            
            if workspace_icon is None and hasattr(integration, 'integration_metadata') and integration.integration_metadata:
                workspace_icon = integration.integration_metadata.get("workspace_icon", "")
            
            connected_integrations.append({
                "id": integration.id,
                "integration_type": integration.integration_type,
                "workspace_name": workspace_name or "",
                "workspace_icon": workspace_icon or "",
                "active": integration.active,
                "created_at": integration.created_at.isoformat() if hasattr(integration.created_at, 'isoformat') else str(integration.created_at),
                "updated_at": integration.updated_at.isoformat() if hasattr(integration.updated_at, 'isoformat') else str(integration.updated_at)
            })
        
        # Extract values from PersistentConfig objects
        processed_available_integrations = extract_persistent_config_values(AVAILABLE_INTEGRATIONS)
        processed_enable_integrations = extract_persistent_config_values(ENABLE_INTEGRATIONS)
        
        return {
            "available": processed_available_integrations,
            "connected": connected_integrations,
            "enabled": processed_enable_integrations
        }
    except Exception as e:
        logger.error(f"Error in get_available_integrations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

__all__ = ["notion", "router"] 