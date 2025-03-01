"""
Custom OpenAI tools implementation for Notion integration.
This file adds direct support for Notion functions in the OpenAI API.
"""

from typing import List, Dict, Any, Optional, Union
import json
import aiohttp
import logging
import time
import os

from open_webui.utils.integrations.notion import (
    get_notion_function_tools,
    handle_notion_function_execution,
    format_notion_api_result_for_llm
)
from open_webui.models.integrations import Integrations

log = logging.getLogger(__name__)

class NotionTools:
    """Tools for interacting with Notion API"""
    
    @staticmethod
    async def list_notion_databases():
        """List all Notion databases the user has access to"""
        return {"action": "list_notion_databases"}
    
    @staticmethod
    async def search_notion(query: str, filter: Optional[Dict[str, Any]] = None, sort: Optional[Dict[str, Any]] = None):
        """
        Search Notion for pages, databases, and other content
        :param query: The search query string
        :param filter: Filter for specific types of Notion objects (optional)
        :param sort: Sort the results (optional)
        """
        return {
            "action": "search",
            "params": {
                "query": query,
                "filter": filter,
                "sort": sort
            }
        }
    
    @staticmethod
    async def query_notion_database(database_id: str, filter: Optional[Dict[str, Any]] = None, 
                             sorts: Optional[List[Dict[str, Any]]] = None, page_size: Optional[int] = 10):
        """
        Query a specific Notion database
        :param database_id: The ID of the database to query
        :param filter: Filter conditions for the database query (optional)
        :param sorts: Sort order for the database query (optional)
        :param page_size: Maximum number of results to return (max 100)
        """
        return {
            "action": "query_database",
            "params": {
                "database_id": database_id,
                "query": {
                    "filter": filter,
                    "sorts": sorts,
                    "page_size": page_size
                }
            }
        }
    
    @staticmethod
    async def create_notion_page(parent: Dict[str, Any], properties: Dict[str, Any], 
                          children: Optional[List[Dict[str, Any]]] = None):
        """
        Create a new page in Notion
        :param parent: Parent resource where the page will be created
        :param properties: Page properties (varies by database schema)
        :param children: Page content blocks (optional)
        """
        return {
            "action": "create_page",
            "params": {
                "page": {
                    "parent": parent,
                    "properties": properties,
                    "children": children
                }
            }
        }
    
    @staticmethod
    async def update_notion_page(page_id: str, properties: Dict[str, Any], archived: Optional[bool] = None):
        """
        Update an existing page in Notion
        :param page_id: The ID of the page to update
        :param properties: Page properties to update (varies by database schema)
        :param archived: Whether the page should be archived (optional)
        """
        return {
            "action": "update_page",
            "params": {
                "page_id": page_id,
                "properties": properties,
                "archived": archived
            }
        }

async def execute_notion_tool(action_data: Dict[str, Any], access_token: str, base_url: str) -> Dict[str, Any]:
    """Execute the Notion function with the given action data"""
    try:
        log.info(f"Executing Notion action: {action_data}")
        
        # Use environment variable instead of the database token
        env_token = os.environ.get("NOTION_ACCESS_TOKEN")
        if env_token:
            log.info("Using NOTION_ACCESS_TOKEN from environment variable")
            access_token = env_token
        else:
            log.warning("NOTION_ACCESS_TOKEN environment variable not found, falling back to database token")
        
        # Extract the action and parameters
        action = action_data.get("action", "")
        params = action_data.get("params", {})
        
        log.info(f"Directly executing Notion API action: {action}")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        # Make direct API calls to Notion based on the action
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            
            if action == "search" or action == "search_notion":
                url = "https://api.notion.com/v1/search"
                data = {
                    "query": params.get("query", ""),
                    "filter": params.get("filter", {"value": "page", "property": "object"})
                }
                
                # Only add sort if it's not None
                sort_param = params.get("sort")
                if sort_param is not None:
                    data["sort"] = sort_param
                else:
                    # Use default sort if none provided
                    data["sort"] = {"direction": "descending", "timestamp": "last_edited_time"}
                
                log.info(f"Making direct search request to Notion API: {url} with data: {data}")
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        detail = await response.text()
                        log.error(f"Notion API error: {detail}")
                        return {"error": True, "message": f"Notion API error: {detail}"}
                    
                    result = await response.json()
                    # Return a dictionary rather than using format_notion_api_result_for_llm
                    formatted_result = {
                        "status": "success",
                        "results": result.get("results", []),
                        "count": len(result.get("results", [])),
                        "message": f"Found {len(result.get('results', []))} results matching your query."
                    }
                    log.info(f"Formatted search result: {formatted_result}")
                    return formatted_result
                    
            elif action == "list_databases" or action == "list_notion_databases":
                url = "https://api.notion.com/v1/search"
                data = {
                    "filter": {"value": "database", "property": "object"}
                }
                
                log.info(f"Making direct list_databases request to Notion API: {url}")
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        detail = await response.text()
                        log.error(f"Notion API error: {detail}")
                        return {"error": True, "message": f"Notion API error: {detail}"}
                    
                    result = await response.json()
                    # Return a dictionary rather than using format_notion_api_result_for_llm
                    databases = []
                    for db in result.get("results", []):
                        db_id = db.get("id")
                        title_objects = db.get("title", [])
                        title = " ".join([t.get("plain_text", "") for t in title_objects if "plain_text" in t])
                        if not title:
                            title = "Untitled Database"
                        
                        databases.append({
                            "id": db_id,
                            "title": title,
                            "url": db.get("url", "")
                        })
                    
                    formatted_result = {
                        "status": "success",
                        "databases": databases,
                        "count": len(databases),
                        "message": f"Found {len(databases)} databases."
                    }
                    log.info(f"Formatted database list result: {formatted_result}")
                    return formatted_result
                    
            elif action == "query_database":
                database_id = params.get("database_id")
                if not database_id:
                    return {"error": True, "message": "Database ID is required"}
                    
                url = f"https://api.notion.com/v1/databases/{database_id}/query"
                data = {}
                
                # Add filter if provided
                filter_param = params.get("filter")
                if filter_param:
                    data["filter"] = filter_param
                    
                # Add sorts if provided
                sorts_param = params.get("sorts")
                if sorts_param:
                    data["sorts"] = sorts_param
                
                log.info(f"Making direct query_database request to Notion API: {url}")
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        detail = await response.text()
                        log.error(f"Notion API error: {detail}")
                        return {"error": True, "message": f"Notion API error: {detail}"}
                    
                    result = await response.json()
                    # Return a dictionary rather than using format_notion_api_result_for_llm
                    formatted_result = {
                        "status": "success",
                        "results": result.get("results", []),
                        "count": len(result.get("results", [])),
                        "message": f"Found {len(result.get('results', []))} items in database."
                    }
                    log.info(f"Formatted query result: {formatted_result}")
                    return formatted_result
                    
            elif action == "create_page":
                url = "https://api.notion.com/v1/pages"
                
                # Get parameters from the action_data
                database_id = params.get("database_id")
                title = params.get("title", "")
                properties_json = params.get("properties_json", "")
                content_json = params.get("content_json", "")
                
                if not database_id:
                    return {"error": True, "message": "Database ID is required"}
                
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
                        additional_props = json.loads(properties_json) if isinstance(properties_json, str) else properties_json
                        if isinstance(additional_props, dict):
                            properties.update(additional_props)
                        else:
                            return {"error": True, "message": "properties_json must be a valid JSON object"}
                    except json.JSONDecodeError:
                        return {"error": True, "message": f"Invalid properties JSON: {properties_json}"}
                
                # Create the page data
                page_data = {
                    "parent": {"database_id": database_id},
                    "properties": properties
                }
                
                # Add content if provided
                if content_json:
                    try:
                        content = json.loads(content_json) if isinstance(content_json, str) else content_json
                        if isinstance(content, list):
                            page_data["children"] = content
                        else:
                            return {"error": True, "message": "content_json must be a valid JSON array of block objects"}
                    except json.JSONDecodeError:
                        return {"error": True, "message": f"Invalid content JSON: {content_json}"}
                
                log.info(f"Making direct create_page request to Notion API: {url}")
                async with session.post(url, headers=headers, json=page_data) as response:
                    if response.status != 200:
                        detail = await response.text()
                        log.error(f"Notion API error: {detail}")
                        return {"error": True, "message": f"Notion API error: {detail}"}
                    
                    result = await response.json()
                    # Return a dictionary rather than using format_notion_api_result_for_llm
                    formatted_result = {
                        "status": "success",
                        "page_id": result.get("id"),
                        "url": result.get("url"),
                        "message": "Page created successfully."
                    }
                    log.info(f"Formatted create page result: {formatted_result}")
                    return formatted_result
            
            elif action == "update_page":
                page_id = params.get("page_id")
                properties = params.get("properties")
                
                if not page_id or not properties:
                    return {"error": True, "message": "Page ID and properties are required"}
                    
                url = f"https://api.notion.com/v1/pages/{page_id}"
                data = {
                    "properties": properties
                }
                
                # Add archived status if provided
                if params.get("archived") is not None:
                    data["archived"] = params.get("archived")
                
                log.info(f"Making direct update_page request to Notion API: {url}")
                async with session.patch(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        detail = await response.text()
                        log.error(f"Notion API error: {detail}")
                        return {"error": True, "message": f"Notion API error: {detail}"}
                    
                    result = await response.json()
                    # Return a dictionary rather than using format_notion_api_result_for_llm
                    formatted_result = {
                        "status": "success",
                        "page_id": result.get("id"),
                        "url": result.get("url"),
                        "message": "Page updated successfully."
                    }
                    log.info(f"Formatted update page result: {formatted_result}")
                    return formatted_result
            
            else:
                return {"error": True, "message": f"Unknown action: {action}"}
    except Exception as e:
        log.error(f"Error executing Notion action: {str(e)}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")
        return {"error": True, "message": f"Error executing Notion action: {str(e)}"}

def register_notion_tools(app):
    """Register Notion tools with the application"""
    log.info("Registering Notion tools")
    if not hasattr(app.state, "TOOLS"):
        app.state.TOOLS = {}
    
    # Add Notion tools to the app state
    app.state.TOOLS["notion"] = NotionTools 