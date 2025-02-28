"""
Notion integration utilities for OpenAI function calling.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union

log = logging.getLogger(__name__)

def get_notion_function_tools() -> List[Dict[str, Any]]:
    """
    Return a list of function tools for interacting with Notion.
    
    Returns:
        List[Dict[str, Any]]: List of function tools for interacting with Notion
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_notion",
                "description": "Search Notion for pages, databases, and other content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query string"
                        },
                        "filter": {
                            "type": "object",
                            "description": "Filter for specific types of Notion objects",
                            "properties": {
                                "value": {
                                    "type": "string",
                                    "description": "The type of objects to filter for (e.g. 'page', 'database')"
                                },
                                "property": {
                                    "type": "string",
                                    "description": "The property to filter on (usually 'object')"
                                }
                            }
                        },
                        "sort": {
                            "type": "object",
                            "description": "Sort the results",
                            "properties": {
                                "direction": {
                                    "type": "string",
                                    "description": "Sort direction ('ascending' or 'descending')"
                                },
                                "timestamp": {
                                    "type": "string",
                                    "description": "Which timestamp to sort by (e.g. 'last_edited_time')"
                                }
                            }
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_notion_databases",
                "description": "List all Notion databases the user has access to",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_notion_database",
                "description": "Query a specific Notion database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "The ID of the database to query"
                        },
                        "filter": {
                            "type": "object",
                            "description": "Filter conditions for the database query"
                        },
                        "sorts": {
                            "type": "array",
                            "description": "Sort order for the database query",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "property": {
                                        "type": "string",
                                        "description": "The property to sort by"
                                    },
                                    "direction": {
                                        "type": "string",
                                        "description": "The sort direction ('ascending' or 'descending')"
                                    }
                                }
                            }
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Maximum number of results to return (max 100)"
                        }
                    },
                    "required": ["database_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_notion_page",
                "description": "Create a new page in Notion",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parent": {
                            "type": "object",
                            "description": "Parent resource where the page will be created",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "description": "The parent type ('database_id' or 'page_id')"
                                },
                                "database_id": {
                                    "type": "string",
                                    "description": "The ID of the database to create the page in"
                                },
                                "page_id": {
                                    "type": "string",
                                    "description": "The ID of the page to create a subpage in"
                                }
                            },
                            "required": ["type"]
                        },
                        "properties": {
                            "type": "object",
                            "description": "Page properties (varies by database schema)"
                        },
                        "children": {
                            "type": "array",
                            "description": "Page content blocks",
                            "items": {
                                "type": "object"
                            }
                        }
                    },
                    "required": ["parent", "properties"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_notion_page",
                "description": "Update an existing page in Notion",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The ID of the page to update"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Page properties to update (varies by database schema)"
                        },
                        "archived": {
                            "type": "boolean",
                            "description": "Whether the page should be archived"
                        }
                    },
                    "required": ["page_id", "properties"]
                }
            }
        }
    ]


def handle_notion_function_execution(
    function_name: str, 
    arguments: Dict[str, Any],
    execute_endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Map function calls to the appropriate API endpoints based on function name and arguments
    
    Args:
        function_name: The name of the function to execute
        arguments: The arguments for the function call
        execute_endpoint: The endpoint URL to execute the API call (optional)
        
    Returns:
        Dict containing the action and parameters for the API call
    """
    # Default to standard endpoint if not provided
    if not execute_endpoint:
        execute_endpoint = "/api/v1/integrations/notion/execute"
    
    # Handle case where arguments might be a string (common with LLM function calls)
    if isinstance(arguments, str):
        try:
            # Try to parse JSON string
            if arguments.strip() == '{}' or not arguments.strip():
                # Empty JSON object or empty string
                arguments = {}
            else:
                # Parse the JSON string
                import json
                arguments = json.loads(arguments)
                log.info(f"Parsed arguments string into dict: {arguments}")
        except Exception as e:
            log.warning(f"Failed to parse arguments string: {e}")
            arguments = {}
    
    # If arguments is None or not a dict, set to empty dict
    if arguments is None or not isinstance(arguments, dict):
        log.warning(f"Invalid arguments type: {type(arguments)}. Using empty dict.")
        arguments = {}
    
    log.info(f"Processing Notion function: {function_name} with arguments: {arguments}")
    
    # Start mapping the function to appropriate action
    if function_name == "search_notion":
        return {
            "action": "search",
            "params": {
                "query": arguments.get("query", ""),
                "filter": arguments.get("filter"),
                "sort": arguments.get("sort")
            }
        }
    
    elif function_name == "list_notion_databases":
        # For list_notion_databases, we don't need any parameters
        log.info("Processing list_notion_databases with empty params")
        return {
            "action": "list_notion_databases",
            "params": {}
        }
    
    elif function_name == "query_notion_database":
        return {
            "action": "query_database",
            "params": {
                "database_id": arguments.get("database_id"),
                "filter": arguments.get("filter"),
                "sorts": arguments.get("sorts"),
                "page_size": arguments.get("page_size", 10)
            }
        }
    
    elif function_name == "create_notion_page":
        return {
            "action": "create_page",
            "params": {
                "parent": arguments.get("parent"),
                "properties": arguments.get("properties", {}),
                "children": arguments.get("children", [])
            }
        }
    
    elif function_name == "update_notion_page":
        return {
            "action": "update_page",
            "params": {
                "page_id": arguments.get("page_id"),
                "properties": arguments.get("properties", {}),
                "archived": arguments.get("archived")
            }
        }
    
    else:
        log.warning(f"Unknown Notion function: {function_name}")
        return {
            "action": "unknown",
            "params": {"function_name": function_name, "arguments": arguments}
        }


def format_notion_api_result_for_llm(result: Dict[str, Any], function_name: str = "") -> Dict[str, Any]:
    """
    Format the Notion API result to be more readable by the LLM
    
    Args:
        result: The result from the Notion API
        function_name: The name of the function that was called
        
    Returns:
        A formatted result that's easier for the LLM to parse and use
    """
    # Check if there was an error
    if isinstance(result, dict) and result.get("error"):
        return {
            "status": "error",
            "message": result.get("message", "An error occurred with the Notion API"),
            "details": result
        }
    
    # Special handling for None results (common with AI function calls)
    if result is None:
        log.warning(f"Received None result for function: {function_name}")
        return {
            "status": "error",
            "message": "No data was returned from the Notion API. This may be due to an issue with the function call processing.",
            "help": "Try using the direct /api/v1/integrations/notion/databases endpoint to access your Notion databases directly."
        }
    
    # Handle specific function results
    if function_name == "list_notion_databases" or (
        function_name == "search_notion" and 
        result.get("results") and 
        any(r.get("object") == "database" for r in result.get("results", []))
    ):
        # Format database results
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
                    "last_edited_time": item.get("last_edited_time")
                })
        
        return {
            "status": "success",
            "databases": databases,
            "count": len(databases)
        }
    
    elif function_name == "query_notion_database":
        # Format database query results
        pages = []
        
        for item in result.get("results", []):
            if item.get("object") == "page":
                # Extract page properties
                properties = {}
                for prop_name, prop_value in item.get("properties", {}).items():
                    prop_type = prop_value.get("type")
                    
                    if prop_type == "title":
                        title_text = ""
                        for text in prop_value.get("title", []):
                            if text.get("type") == "text":
                                title_text += text.get("text", {}).get("content", "")
                        properties[prop_name] = title_text
                    
                    elif prop_type == "rich_text":
                        text_content = ""
                        for text in prop_value.get("rich_text", []):
                            if text.get("type") == "text":
                                text_content += text.get("text", {}).get("content", "")
                        properties[prop_name] = text_content
                    
                    elif prop_type == "number":
                        properties[prop_name] = prop_value.get("number")
                    
                    elif prop_type == "select":
                        select_option = prop_value.get("select", {})
                        if select_option:
                            properties[prop_name] = select_option.get("name")
                    
                    elif prop_type == "multi_select":
                        properties[prop_name] = [
                            option.get("name") 
                            for option in prop_value.get("multi_select", [])
                        ]
                    
                    elif prop_type == "date":
                        date_obj = prop_value.get("date", {})
                        if date_obj:
                            properties[prop_name] = {
                                "start": date_obj.get("start"),
                                "end": date_obj.get("end")
                            }
                    
                    elif prop_type == "checkbox":
                        properties[prop_name] = prop_value.get("checkbox")
                    
                    elif prop_type == "url":
                        properties[prop_name] = prop_value.get("url")
                    
                    elif prop_type == "email":
                        properties[prop_name] = prop_value.get("email")
                    
                    elif prop_type == "phone_number":
                        properties[prop_name] = prop_value.get("phone_number")
                
                pages.append({
                    "id": item.get("id"),
                    "url": item.get("url"),
                    "properties": properties,
                    "last_edited_time": item.get("last_edited_time")
                })
        
        return {
            "status": "success",
            "pages": pages,
            "count": len(pages),
            "has_more": result.get("has_more", False),
            "next_cursor": result.get("next_cursor")
        }
    
    elif function_name == "create_notion_page" or function_name == "update_notion_page":
        # Return the created/updated page
        if result.get("object") == "page":
            properties = {}
            for prop_name, prop_value in result.get("properties", {}).items():
                prop_type = prop_value.get("type")
                
                if prop_type == "title":
                    title_text = ""
                    for text in prop_value.get("title", []):
                        if text.get("type") == "text":
                            title_text += text.get("text", {}).get("content", "")
                    properties[prop_name] = title_text
                # Add other property types as needed
            
            return {
                "status": "success",
                "page": {
                    "id": result.get("id"),
                    "url": result.get("url"),
                    "properties": properties
                }
            }
    
    # For other or unknown results, return the raw result
    return {
        "status": "success",
        "result": result
    } 