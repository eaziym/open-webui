import sys
from sqlalchemy import (
    Column, DateTime, String, 
    Boolean, Text, JSON, inspect, 
    create_engine
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import os
import uuid

# Get the database URL from environment or use a default
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/webui.db')

# Create engine
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define IntegrationModel
class IntegrationModel(Base):
    """Database model for user integrations."""
    __tablename__ = "integrations"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)  # Removed ForeignKey constraint
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

def create_integrations_table():
    """Create the integrations table if it doesn't exist"""
    try:
        # Check if the table already exists
        inspector = inspect(engine)
        if "integrations" in inspector.get_table_names():
            print("Integrations table already exists.")
            return True

        # Create the table
        Base.metadata.create_all(engine, tables=[IntegrationModel.__table__])
        print("Integrations table created successfully!")
        return True
    except SQLAlchemyError as e:
        print(f"Error creating integrations table: {e}")
        return False

if __name__ == "__main__":
    create_integrations_table() 