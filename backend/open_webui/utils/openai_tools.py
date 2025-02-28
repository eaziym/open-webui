"""
Custom OpenAI tools implementation for Notion integration.
This file adds direct support for Notion functions in the OpenAI API.
"""

from typing import List, Dict, Any, Optional
import json
import aiohttp
import logging
import time

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
        
        # Ensure base_url doesn't end with a slash
        base_url = base_url.rstrip("/")
        execute_url = f"{base_url}/api/v1/integrations/notion/execute"
        
        log.info(f"Making request to: {execute_url}")
        # Add more detailed logging for debugging
        log.info(f"Headers: Authorization: Bearer ***, Content-Type: application/json")
        log.info(f"JSON payload: {json.dumps(action_data)}")
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            log.info(f"Starting API request at {start_time}")
            
            async with session.post(
                execute_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=action_data
            ) as response:
                end_time = time.time()
                log.info(f"API request completed in {end_time - start_time:.2f} seconds")
                log.info(f"Response status: {response.status}")
                
                if response.status != 200:
                    detail = await response.text()
                    log.error(f"Notion API error: {detail}")
                    return {"error": True, "message": f"Notion API error: {detail}"}
                
                result = await response.json()
                log.info(f"Notion API response: {result}")
                
                # Check if we have the expected structure
                if isinstance(result, dict):
                    if "result" in result:
                        log.info("Returning result from Response object")
                        return result["result"]
                    elif "error" in result and result["error"]:
                        log.error(f"Error in result: {result.get('message', 'Unknown error')}")
                
                return result
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