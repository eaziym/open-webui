#!/usr/bin/env python3
"""
Standalone script to retrieve Notion access tokens directly from the Open WebUI database.
This script has no dependencies on other custom modules.

Usage:
  python get_notion_tokens_standalone.py

Run this from your Open WebUI project root directory.
"""

import os
import sys
import json
from datetime import datetime

# Try to determine if we're in the Open WebUI environment
if os.path.exists("backend/open_webui"):
    sys.path.append("backend")

try:
    # Import SQLAlchemy
    try:
        from sqlalchemy import create_engine, Column, String, inspect, text
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker
    except ImportError:
        print("Error: SQLAlchemy not found. Install it with:")
        print("pip install sqlalchemy")
        sys.exit(1)
        
    # Figure out the database location
    database_url = os.environ.get('DATABASE_URL')
    
    # If not set in environment, try the default SQLite path
    if not database_url:
        sqlite_path = os.path.join("data", "webui.db")
        if os.path.exists(sqlite_path):
            database_url = f"sqlite:///{sqlite_path}"
        else:
            # Try to find the SQLite database in common locations
            for path in ["./webui.db", "./backend/data/webui.db", "./data/webui.db"]:
                if os.path.exists(path):
                    database_url = f"sqlite:///{path}"
                    break
    
    if not database_url:
        print("Error: Database URL not found. Set DATABASE_URL environment variable")
        print("or make sure the SQLite database exists in the data directory.")
        sys.exit(1)
        
    print(f"Connecting to database: {database_url}")
    
    # Connect to the database
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Check if the integrations table exists
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if "integrations" not in tables:
        print("Error: 'integrations' table not found in the database.")
        print("Make sure you're running this script in the Open WebUI project root.")
        sys.exit(1)
    
    # Check if user table exists and get its columns
    user_table_exists = "user" in tables
    user_columns = []
    if user_table_exists:
        user_columns = [column['name'] for column in inspector.get_columns('user')]
        print(f"User table columns: {', '.join(user_columns)}")
    
    # Simplify the query to avoid errors with missing columns
    # Just get the tokens directly without joining with user table
    sql_query = text("""
        SELECT 
            id, user_id, access_token, workspace_name, workspace_id
        FROM 
            integrations
        WHERE 
            integration_type = 'notion' AND active = 1
    """)
    
    result = session.execute(sql_query)
    
    tokens = []
    for row in result:
        # Convert row to dict
        token_info = {
            "integration_id": row[0],
            "user_id": row[1], 
            "access_token": row[2],
            "workspace_name": row[3],
            "workspace_id": row[4]
        }
        tokens.append(token_info)
    
    # Display the results
    if not tokens:
        print("No Notion integration tokens found in the database.")
        sys.exit(0)
    
    print(f"Found {len(tokens)} active Notion integration(s):")
    print("-" * 50)
    
    for i, token_info in enumerate(tokens, 1):
        user_id = token_info.get("user_id", "Unknown")
        access_token = token_info.get("access_token", "Unknown")
        workspace = token_info.get("workspace_name", "Unknown") 
        
        print(f"Integration #{i}:")
        print(f"  User ID: {user_id}")
        print(f"  Workspace: {workspace}")
        print(f"  Token: {access_token[:10]}...{access_token[-5:] if len(access_token) > 15 else ''}")
        print()
    
    # Save tokens to a file for easy access
    output_file = "notion_tokens.json"
    with open(output_file, "w") as f:
        json.dump(tokens, f, indent=2)
    
    print(f"Tokens saved to {output_file}")
    print("\nTo use a token in your code:")
    print("-" * 50)
    print("import requests")
    print("import json")
    print()
    print("# Copy this access token")
    print(f"ACCESS_TOKEN = \"{tokens[0]['access_token']}\"")
    print()
    print("# Use it in the Notion API")
    print("headers = {")
    print('    "Authorization": f"Bearer {ACCESS_TOKEN}",')
    print('    "Content-Type": "application/json",')
    print('    "Notion-Version": "2022-06-28"')
    print("}")
    print()
    print("# Example: List databases")
    print("response = requests.post(")
    print('    "https://api.notion.com/v1/search",')
    print('    headers=headers,')
    print('    json={"filter": {"value": "database", "property": "object"}}')
    print(")")
    print("print(json.dumps(response.json(), indent=2))")
    
except Exception as e:
    print(f"Error: {str(e)}")
    print("\nTroubleshooting:")
    print("1. Make sure you're running this script from the Open WebUI project root")
    print("2. Check if the database is accessible")
    print("3. Ensure you have the required permissions")
    sys.exit(1) 