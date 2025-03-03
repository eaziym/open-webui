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
)
from open_webui.models.users import UserModel as User
from open_webui.models.integrations import IntegrationModel as IntegrationConnection
from open_webui.internal.db import get_db, PersistentConfig
from open_webui.utils.auth import get_current_user, get_verified_user, get_admin_user
from open_webui.models.integrations import Integrations
from sqlalchemy.orm import Session

# Import the notion router to include it in our main router
from open_webui.routers.integrations.notion import router as notion_router

logger = logging.getLogger(__name__)
router = APIRouter()

# Include the modular notion router
router.include_router(notion_router)

# General integration endpoints and helper functions

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

# Helper function to check if integrations are enabled
def check_integrations_enabled():
    """Check if integrations are enabled in the config."""
    enable_integrations = extract_persistent_config_values(ENABLE_INTEGRATIONS)
    if not enable_integrations:
        raise HTTPException(
            status_code=403,
            detail="Integrations are not enabled on this server."
        )

# General endpoint to list all available integrations
@router.get(
    "/",
    description="List all available integrations and the user's connected integrations",
)
async def list_integrations(
    request: Request,
    user=Depends(get_verified_user),
):
    """List all available integrations and the user's connected integrations."""
    try:
        logger.info("Starting list_integrations function")
        check_integrations_enabled()
        
        # Get user's integrations
        logger.info("Fetching user integrations")
        user_integrations = Integrations.get_user_integrations(user.id)
        
        # Format connected integrations
        logger.info("Formatting connected integrations")
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
        
        # Format available integrations
        logger.info("Formatting available integrations")
        available_integrations = {}
        
        # Extract values from PersistentConfig objects
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

        # Add other integrations here as they are implemented
        
        # Get the enable_integrations flag
        enable_integrations = extract_persistent_config_values(ENABLE_INTEGRATIONS)
        
        logger.info("Returning response")
        return {
            "available": available_integrations,
            "connected": connected_integrations,
            "enabled": enable_integrations
        }
    except Exception as e:
        logger.error(f"Error in list_integrations: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# Note: All Notion-specific routes have been removed and are now handled by the modular router
# imported from open_webui.routers.integrations.notion 