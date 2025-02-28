import json
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean, Text, Integer, JSON
from sqlalchemy.orm import relationship
from pydantic import BaseModel

from open_webui.internal.db import Base, get_db

# Forward references
if TYPE_CHECKING:
    from open_webui.models.users import User


class IntegrationModel(Base):
    """Database model for user integrations."""
    __tablename__ = "integrations"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    integration_type = Column(String, nullable=False)  # e.g., "notion", "github", etc.
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    workspace_id = Column(String, nullable=True)
    workspace_name = Column(String, nullable=True)
    workspace_icon = Column(String, nullable=True)
    integration_metadata = Column(JSON, nullable=True)  # Additional integration-specific data
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="integrations", foreign_keys=[user_id])


class IntegrationResponseModel(BaseModel):
    """Response model for integration details."""
    id: str
    integration_type: str
    workspace_name: Optional[str] = None
    workspace_icon: Optional[str] = None
    active: bool
    created_at: datetime
    updated_at: datetime


class IntegrationDetails(BaseModel):
    """Details about an integration type."""
    name: str
    description: str
    icon: str
    enabled: bool


class IntegrationListResponse(BaseModel):
    """Response model for listing integrations."""
    available: Dict[str, IntegrationDetails]
    connected: List[IntegrationResponseModel]


class NotionDatabase(BaseModel):
    """Model for Notion database information."""
    id: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    last_edited_time: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class NotionPage(BaseModel):
    """Model for Notion page information."""
    id: str
    title: str
    url: Optional[str] = None
    last_edited_time: Optional[str] = None
    parent_id: Optional[str] = None
    parent_type: Optional[str] = None


class NotionQueryResult(BaseModel):
    """Model for Notion database query results."""
    object: str
    results: List[Dict[str, Any]]
    has_more: bool
    next_cursor: Optional[str] = None


class IntegrationError(Exception):
    """Exception raised for integration errors."""
    
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class Integrations:
    """Class for interacting with integration models."""
    
    @staticmethod
    def get_user_integrations(user_id: str) -> List[IntegrationModel]:
        """Get all integrations for a user."""
        with get_db() as db:
            return db.query(IntegrationModel).filter(IntegrationModel.user_id == user_id).all()
    
    @staticmethod
    def get_user_integration_by_id(user_id: str, integration_id: str) -> Optional[IntegrationModel]:
        """Get a specific integration for a user by ID."""
        with get_db() as db:
            return db.query(IntegrationModel).filter(
                IntegrationModel.user_id == user_id,
                IntegrationModel.id == integration_id
            ).first()
    
    @staticmethod
    def get_user_active_integration(user_id: str, integration_type: str) -> Optional[IntegrationModel]:
        """Get the active integration of a specific type for a user."""
        with get_db() as db:
            return db.query(IntegrationModel).filter(
                IntegrationModel.user_id == user_id,
                IntegrationModel.integration_type == integration_type,
                IntegrationModel.active == True
            ).first()
    
    @staticmethod
    def create_integration(
        user_id: str,
        integration_type: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        workspace_id: Optional[str] = None,
        workspace_name: Optional[str] = None,
        workspace_icon: Optional[str] = None,
        integration_metadata: Optional[Dict[str, Any]] = None,
    ) -> IntegrationModel:
        """Create a new integration for a user."""
        with get_db() as db:
            # Check if user already has an active integration of this type
            existing = db.query(IntegrationModel).filter(
                IntegrationModel.user_id == user_id,
                IntegrationModel.integration_type == integration_type,
                IntegrationModel.active == True
            ).first()
            
            # If exists, deactivate it
            if existing:
                existing.active = False
                db.commit()
            
            # Create new integration
            integration = IntegrationModel(
                user_id=user_id,
                integration_type=integration_type,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                workspace_icon=workspace_icon,
                integration_metadata=integration_metadata,
                active=True
            )
            db.add(integration)
            db.commit()
            db.refresh(integration)
            return integration
    
    @staticmethod
    def update_integration(integration_id: str, **kwargs) -> Optional[IntegrationModel]:
        """Update an integration."""
        with get_db() as db:
            integration = db.query(IntegrationModel).filter(IntegrationModel.id == integration_id).first()
            if not integration:
                return None
            
            for key, value in kwargs.items():
                if hasattr(integration, key):
                    setattr(integration, key, value)
            
            db.commit()
            db.refresh(integration)
            return integration
    
    @staticmethod
    def delete_integration(integration_id: str) -> bool:
        """Delete an integration."""
        with get_db() as db:
            integration = db.query(IntegrationModel).filter(IntegrationModel.id == integration_id).first()
            if not integration:
                return False
            
            db.delete(integration)
            db.commit()
            return True
            
    @staticmethod
    def deactivate_integration(integration_id: str) -> bool:
        """Deactivate an integration without deleting it."""
        try:
            # Get a direct session instead of using the context manager
            from open_webui.internal.db import SessionLocal
            db = SessionLocal()
            
            try:
                integration = db.query(IntegrationModel).filter(IntegrationModel.id == integration_id).first()
                if not integration:
                    return False
                
                integration.active = False
                db.commit()
                return True
            finally:
                db.close()
        except Exception as e:
            import logging
            log = logging.getLogger(__name__)
            log.error(f"Error in deactivate_integration: {str(e)}")
            return False 