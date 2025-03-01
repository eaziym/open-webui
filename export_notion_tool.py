#!/usr/bin/env python3
"""
Export Notion Tool Configuration

This script exports the Notion tool configuration as a JSON file that can be imported into OpenWebUI.
It formats the configuration according to the OpenWebUI tool requirements, ensuring all necessary
fields are included and properly structured.

Usage:
    python export_notion_tool.py

The script will create a file named 'notion_tool_config.json' in the same directory.
"""

import json
import time
import os
from datetime import datetime

def export_tool_config():
    """
    Create and export the Notion tool configuration as a JSON file.
    """
    # Get current timestamp for ID and dates
    current_time = int(time.time())
    
    # Create a valid ID (alphanumeric and underscores only)
    tool_id = f"notion_tool_{current_time}"
    
    # The tool code as a string for the "content" field
    tool_content = '''"""
title: Notion Tools
author: Open WebUI
author_url: https://github.com/open-webui
git_url: https://github.com/open-webui/notion-tools
description: A set of tools for interacting with Notion databases and pages
required_open_webui_version: 0.4.0
requirements: notion-client
version: 0.1.0
licence: MIT
"""

import os
import json
from notion_client import Client
from typing import Dict, List, Optional, Any, Union

class Tools:
    def __init__(self):
        """Initialize the Notion Tools."""
        self.notion = None
        # No valve properties needed
    
    def _get_client(self) -> Union[Client, None]:
        """
        Get or create the Notion client instance.
        
        Returns:
            A Notion client instance or None if no access token is available.
        """
        if not self.notion:
            # Only use environment variable for token
            token = os.environ.get("NOTION_ACCESS_TOKEN")
            
            if not token:
                return None
                
            self.notion = Client(auth=token)
        return self.notion
    
    def notion_list_databases(self) -> str:
        """
        List all Notion databases the user has access to.
        
        Returns:
            A formatted list of Notion databases with their IDs and titles.
        """
        client = self._get_client()
        if not client:
            return "Error: Notion access token not found. Please set the NOTION_ACCESS_TOKEN environment variable."
        
        try:
            results = client.search(filter={"property": "object", "value": "database"}).get("results", [])
            
            if not results:
                return "No databases found. Make sure your access token has appropriate permissions."
                
            output = "### Available Notion Databases:\\n\\n"
            for db in results:
                db_id = db.get("id", "Unknown ID")
                title = db.get("title", [])
                db_title = "Untitled"
                
                # Extract title from the title array if available
                if title and len(title) > 0:
                    title_parts = [t.get("plain_text", "") for t in title if "plain_text" in t]
                    if title_parts:
                        db_title = " ".join(title_parts)
                
                output += f"- **{db_title}** (ID: `{db_id}`)\\n"
                
            return output
        except Exception as e:
            return f"Error listing databases: {str(e)}"
    
    def notion_query_database(self, database_id: str, filter_json: str = "") -> str:
        """
        Query a Notion database and return the results.
        
        Args:
            database_id: The ID of the Notion database to query
            filter_json: Optional JSON string containing filter criteria (Notion filter object)
            
        Returns:
            Formatted results from the database query
        """
        client = self._get_client()
        if not client:
            return "Error: Notion access token not found. Please set the NOTION_ACCESS_TOKEN environment variable."
        
        try:
            # Parse filter JSON if provided
            filter_obj = None
            if filter_json:
                try:
                    filter_obj = json.loads(filter_json)
                except json.JSONDecodeError:
                    return f"Error: Invalid filter JSON: {filter_json}"
            
            # Query the database
            query_params = {"database_id": database_id}
            if filter_obj:
                query_params["filter"] = filter_obj
                
            response = client.databases.query(**query_params)
            results = response.get("results", [])
            
            if not results:
                return "No results found for this query."
            
            # Format the results
            output = f"### Query Results for Database `{database_id}`\\n\\n"
            
            for page in results:
                page_id = page.get("id", "Unknown")
                properties = page.get("properties", {})
                
                output += f"#### Page: `{page_id}`\\n"
                
                for prop_name, prop_data in properties.items():
                    prop_type = prop_data.get("type", "unknown")
                    
                    # Extract property values based on their type
                    if prop_type == "title":
                        value_list = prop_data.get("title", [])
                        value = " ".join([item.get("plain_text", "") for item in value_list])
                    elif prop_type == "rich_text":
                        value_list = prop_data.get("rich_text", [])
                        value = " ".join([item.get("plain_text", "") for item in value_list])
                    elif prop_type == "number":
                        value = prop_data.get("number", "")
                    elif prop_type == "select":
                        select_data = prop_data.get("select", {})
                        value = select_data.get("name", "") if select_data else ""
                    elif prop_type == "multi_select":
                        multi_select = prop_data.get("multi_select", [])
                        value = ", ".join([item.get("name", "") for item in multi_select])
                    elif prop_type == "date":
                        date_data = prop_data.get("date", {})
                        if date_data:
                            start = date_data.get("start", "")
                            end = date_data.get("end", "")
                            value = f"{start} - {end}" if end else start
                        else:
                            value = ""
                    elif prop_type == "checkbox":
                        value = "✅" if prop_data.get("checkbox", False) else "❌"
                    else:
                        value = f"[{prop_type} value]"
                    
                    output += f"- **{prop_name}**: {value}\\n"
                
                output += "\\n"
            
            return output
        except Exception as e:
            return f"Error querying database: {str(e)}"
    
    def notion_create_page(self, database_id: str, title: str, properties_json: str = "", content_json: str = "") -> str:
        """
        Create a new page in a Notion database.
        
        Args:
            database_id: The ID of the database to create a page in
            title: The title of the new page
            properties_json: Optional JSON string containing additional properties
            content_json: Optional JSON string containing page content blocks
            
        Returns:
            A success message with the new page ID or an error message
        """
        client = self._get_client()
        if not client:
            return "Error: Notion access token not found. Please set the NOTION_ACCESS_TOKEN environment variable."
        
        try:
            # Prepare the properties
            properties = {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
            
            # Add additional properties if provided
            if properties_json:
                try:
                    additional_props = json.loads(properties_json)
                    if isinstance(additional_props, dict):
                        properties.update(additional_props)
                    else:
                        return "Error: properties_json must be a valid JSON object"
                except json.JSONDecodeError:
                    return f"Error: Invalid properties JSON: {properties_json}"
            
            # Create the page
            page_data = {
                "parent": {"database_id": database_id},
                "properties": properties
            }
            
            # Add content if provided
            if content_json:
                try:
                    content = json.loads(content_json)
                    if isinstance(content, list):
                        page_data["children"] = content
                    else:
                        return "Error: content_json must be a valid JSON array of block objects"
                except json.JSONDecodeError:
                    return f"Error: Invalid content JSON: {content_json}"
            
            response = client.pages.create(**page_data)
            page_id = response.get("id", "Unknown")
            
            return f"Successfully created page in database. Page ID: `{page_id}`"
        except Exception as e:
            return f"Error creating page: {str(e)}"
    
    def notion_search(self, query: str, search_type: str = "") -> str:
        """
        Search Notion for pages, databases, or other content.
        
        Args:
            query: The search query string
            search_type: Optional type filter ('page', 'database', or leave empty for all)
            
        Returns:
            Formatted search results
        """
        client = self._get_client()
        if not client:
            return "Error: Notion access token not found. Please set the NOTION_ACCESS_TOKEN environment variable."
        
        try:
            # Prepare search parameters
            search_params = {"query": query}
            
            # Add filter if specified
            if search_type:
                if search_type in ["page", "database"]:
                    search_params["filter"] = {"property": "object", "value": search_type}
                else:
                    return f"Error: Invalid search_type '{search_type}'. Use 'page', 'database', or leave empty."
            
            # Execute the search
            response = client.search(**search_params)
            results = response.get("results", [])
            
            if not results:
                return f"No results found for query: '{query}'"
            
            # Format the results
            output = f"### Notion Search Results for '{query}'\\n\\n"
            
            for item in results:
                item_id = item.get("id", "Unknown")
                item_type = item.get("object", "Unknown")
                
                if item_type == "page":
                    # Get the title from properties for pages
                    properties = item.get("properties", {})
                    title_prop = properties.get("title", {})
                    title_items = title_prop.get("title", []) if title_prop else []
                    title = " ".join([t.get("plain_text", "") for t in title_items]) or "Untitled Page"
                    
                    parent = item.get("parent", {})
                    parent_type = parent.get("type", "Unknown")
                    parent_id = parent.get(f"{parent_type}_id", "Unknown") if parent_type in ["database", "page", "workspace"] else "Unknown"
                    
                    output += f"#### 📄 Page: {title}\\n"
                    output += f"- **ID**: `{item_id}`\\n"
                    output += f"- **Parent Type**: {parent_type}\\n"
                    output += f"- **Parent ID**: `{parent_id}`\\n\\n"
                
                elif item_type == "database":
                    # Get the title from title field for databases
                    title_items = item.get("title", [])
                    title = " ".join([t.get("plain_text", "") for t in title_items]) or "Untitled Database"
                    
                    output += f"#### 📊 Database: {title}\\n"
                    output += f"- **ID**: `{item_id}`\\n\\n"
                
                else:
                    output += f"#### {item_type.capitalize()}: {item_id}\\n\\n"
            
            return output
        except Exception as e:
            return f"Error searching Notion: {str(e)}"
'''
    
    # Format the full tool configuration
    tool_config = {
        "id": tool_id,
        "name": "Notion Tools",
        "content": tool_content,
        "meta": {
            "name": "Notion Tools",
            "author": "Open WebUI",
            "description": "A set of tools for interacting with Notion databases and pages",
            "avatar": "",
            "cover": "",
            "tags": ["notion", "database", "productivity"],
            "version": "0.1.0"
        },
        "specs": [
            {
                "id": f"{tool_id}_list_databases",
                "name": "notion_list_databases",
                "parameters": {},
                "description": "List all Notion databases the user has access to."
            },
            {
                "id": f"{tool_id}_query_database",
                "name": "notion_query_database",
                "parameters": {
                    "database_id": {
                        "type": "string",
                        "description": "The ID of the Notion database to query"
                    },
                    "filter_json": {
                        "type": "string",
                        "description": "Optional JSON string containing filter criteria (Notion filter object)"
                    }
                },
                "description": "Query a Notion database and return the results."
            },
            {
                "id": f"{tool_id}_create_page",
                "name": "notion_create_page",
                "parameters": {
                    "database_id": {
                        "type": "string",
                        "description": "The ID of the database to create a page in"
                    },
                    "title": {
                        "type": "string",
                        "description": "The title of the new page"
                    },
                    "properties_json": {
                        "type": "string",
                        "description": "Optional JSON string containing additional properties"
                    },
                    "content_json": {
                        "type": "string",
                        "description": "Optional JSON string containing page content blocks"
                    }
                },
                "description": "Create a new page in a Notion database."
            },
            {
                "id": f"{tool_id}_search",
                "name": "notion_search",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "The search query string"
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Optional type filter ('page', 'database', or leave empty for all)"
                    }
                },
                "description": "Search Notion for pages, databases, or other content."
            }
        ],
        "access_control": {
            "enabled": True,
            "roles": [],
            "groups": []
        },
        "created_at": current_time,
        "updated_at": current_time,
        "type": "function"
    }
    
    # Create a list containing the tool configuration
    tools_list = [tool_config]
    
    # Export to a JSON file
    output_file = "notion_tool_config.json"
    with open(output_file, "w") as f:
        json.dump(tools_list, f, indent=2)
    
    print(f"Tool configuration exported to {output_file}")
    print("\nImport instructions:")
    print("1. Open your OpenWebUI instance")
    print("2. Navigate to Workspace → Tools")
    print("3. Click on 'Import Tools'")
    print(f"4. Select the {output_file} file")
    print("\nConfiguration instructions:")
    print("1. Make sure the NOTION_ACCESS_TOKEN environment variable is set in your OpenWebUI environment.")
    print("2. The token should be set to your Notion integration's token value.")
    print("3. Restart OpenWebUI if you change the environment variable.")
    
    return output_file

if __name__ == "__main__":
    export_tool_config() 