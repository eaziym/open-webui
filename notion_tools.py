import os
import json
import requests
from datetime import datetime
from typing import Optional, Dict, List, Any


class Tools:
    def __init__(self):
        pass

    # Add your custom tools using pure Python code here, make sure to add type hints
    # Use Sphinx-style docstrings to document your tools, they will be used for generating tools specifications
    # Please refer to function_calling_filter_pipeline.py file from pipelines project for an example

    def get_user_name_and_email_and_id(self, __user__: dict = {}) -> str:
        """
        Get the user name, Email and ID from the user object.
        """

        # Do not include :param for __user__ in the docstring as it should not be shown in the tool's specification
        # The session user object will be passed as a parameter when the function is called

        print(__user__)
        result = ""

        if "name" in __user__:
            result += f"User: {__user__['name']}"
        if "id" in __user__:
            result += f" (ID: {__user__['id']})"
        if "email" in __user__:
            result += f" (Email: {__user__['email']})"

        if result == "":
            result = "User: Unknown"

        return result

    def get_current_time(self) -> str:
        """
        Get the current time in a more human-readable format.
        :return: The current time.
        """

        now = datetime.now()
        current_time = now.strftime("%I:%M:%S %p")  # Using 12-hour format with AM/PM
        current_date = now.strftime(
            "%A, %B %d, %Y"
        )  # Full weekday, month name, day, and year

        return f"Current Date and Time = {current_date}, {current_time}"

    def calculator(self, equation: str) -> str:
        """
        Calculate the result of an equation.
        :param equation: The equation to calculate.
        """

        # Avoid using eval in production code
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

    def get_current_weather(self, city: str) -> str:
        """
        Get the current weather for a given city.
        :param city: The name of the city to get the weather for.
        :return: The current weather information or an error message.
        """
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return (
                "API key is not set in the environment variable 'OPENWEATHER_API_KEY'."
            )

        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",  # Optional: Use 'imperial' for Fahrenheit
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            data = response.json()

            if data.get("cod") != 200:
                return f"Error fetching weather data: {data.get('message')}"

            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            return f"Weather in {city}: {temperature}°C"
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"

    # Notion Tools

    def notion_list_databases(self) -> str:
        """
        List all Notion databases the user has access to.
        :return: A formatted list of databases with their IDs and titles.
        """
        access_token = os.getenv("NOTION_ACCESS_TOKEN")
        if not access_token:
            return "Error: NOTION_ACCESS_TOKEN environment variable is not set."

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                "https://api.notion.com/v1/search",
                headers=headers,
                json={"filter": {"value": "database", "property": "object"}}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                return "No databases found. Make sure your integration has access to the databases."
            
            result = "Notion Databases:\n\n"
            for i, db in enumerate(data["results"], 1):
                db_id = db.get("id", "Unknown ID")
                title_objects = db.get("title", [])
                title = title_objects[0]["plain_text"] if title_objects else "Untitled"
                result += f"{i}. {title} (ID: {db_id})\n"
            
            return result
            
        except requests.RequestException as e:
            return f"Error accessing Notion API: {str(e)}"
        except (KeyError, IndexError) as e:
            return f"Error parsing Notion response: {str(e)}"

    def notion_query_database(self, database_id: str, filter_str: Optional[str] = None, max_results: int = 10) -> str:
        """
        Query a specific Notion database and return its content.
        
        :param database_id: The ID of the database to query
        :param filter_str: Optional filter criteria in JSON string format
        :param max_results: Maximum number of results to return (default: 10)
        :return: A formatted result of the database query
        """
        access_token = os.getenv("NOTION_ACCESS_TOKEN")
        if not access_token:
            return "Error: NOTION_ACCESS_TOKEN environment variable is not set."

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

        # Prepare request payload
        payload = {"page_size": max_results}
        
        # Add filter if provided
        if filter_str:
            try:
                filter_json = json.loads(filter_str)
                payload["filter"] = filter_json
            except json.JSONDecodeError:
                return f"Error: Invalid filter JSON: {filter_str}"

        try:
            response = requests.post(
                f"https://api.notion.com/v1/databases/{database_id}/query",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                return "No items found in the database."
            
            result = f"Database Query Results (max {max_results}):\n\n"
            
            for i, page in enumerate(data["results"], 1):
                # Get page title
                title = "Untitled"
                properties = page.get("properties", {})
                
                # Find title property (it could be named anything)
                for prop_name, prop_value in properties.items():
                    if prop_value.get("type") == "title":
                        title_objects = prop_value.get("title", [])
                        if title_objects:
                            title = title_objects[0].get("plain_text", "Untitled")
                            break
                
                page_id = page.get("id", "Unknown ID")
                result += f"{i}. {title} (ID: {page_id})\n"
                
                # Add properties
                result += "   Properties:\n"
                for prop_name, prop_value in properties.items():
                    prop_type = prop_value.get("type", "unknown")
                    
                    if prop_type == "rich_text" or prop_type == "title":
                        text_objects = prop_value.get(prop_type, [])
                        text_content = " ".join([t.get("plain_text", "") for t in text_objects])
                        result += f"   - {prop_name}: {text_content}\n"
                    elif prop_type == "select":
                        select_data = prop_value.get("select")
                        if select_data:
                            result += f"   - {prop_name}: {select_data.get('name', '')}\n"
                    elif prop_type == "date":
                        date_data = prop_value.get("date")
                        if date_data:
                            start = date_data.get("start", "")
                            end = date_data.get("end", "")
                            date_str = start
                            if end:
                                date_str += f" to {end}"
                            result += f"   - {prop_name}: {date_str}\n"
                    elif prop_type == "checkbox":
                        checkbox = prop_value.get("checkbox", False)
                        result += f"   - {prop_name}: {'✓' if checkbox else '✗'}\n"
                    elif prop_type == "number":
                        number = prop_value.get("number", "")
                        result += f"   - {prop_name}: {number}\n"
                    elif prop_type == "multi_select":
                        multi_select = prop_value.get("multi_select", [])
                        options = [option.get("name", "") for option in multi_select]
                        result += f"   - {prop_name}: {', '.join(options)}\n"
                result += "\n"
            
            return result
            
        except requests.RequestException as e:
            return f"Error accessing Notion API: {str(e)}"
        except (KeyError, IndexError) as e:
            return f"Error parsing Notion response: {str(e)}"

    def notion_create_page(self, database_id: str, title: str, properties_str: Optional[str] = None, 
                         content_str: Optional[str] = None) -> str:
        """
        Create a new page in a Notion database.
        
        :param database_id: The ID of the database to create the page in
        :param title: The title of the new page
        :param properties_str: Optional additional properties in JSON string format
        :param content_str: Optional content blocks in JSON string format
        :return: A response message with the result of the operation
        """
        access_token = os.getenv("NOTION_ACCESS_TOKEN")
        if not access_token:
            return "Error: NOTION_ACCESS_TOKEN environment variable is not set."

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

        # First, we need to find the name of the title property in the database
        try:
            response = requests.get(
                f"https://api.notion.com/v1/databases/{database_id}",
                headers=headers
            )
            response.raise_for_status()
            db_data = response.json()
            
            # Find the title property name
            title_property_name = None
            for prop_name, prop_data in db_data.get("properties", {}).items():
                if prop_data.get("type") == "title":
                    title_property_name = prop_name
                    break
            
            if not title_property_name:
                return "Error: Could not find title property in the database."
            
            # Prepare properties
            properties = {
                title_property_name: {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title}
                        }
                    ]
                }
            }
            
            # Add additional properties if provided
            if properties_str:
                try:
                    additional_props = json.loads(properties_str)
                    if not isinstance(additional_props, dict):
                        return "Error: Properties must be a JSON object."
                    properties.update(additional_props)
                except json.JSONDecodeError:
                    return f"Error: Invalid properties JSON: {properties_str}"
            
            # Prepare request payload
            payload = {
                "parent": {"database_id": database_id},
                "properties": properties
            }
            
            # Add content if provided
            if content_str:
                try:
                    content_blocks = json.loads(content_str)
                    payload["children"] = content_blocks
                except json.JSONDecodeError:
                    return f"Error: Invalid content JSON: {content_str}"
            
            # Create the page
            create_response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=payload
            )
            create_response.raise_for_status()
            new_page = create_response.json()
            
            page_id = new_page.get("id", "Unknown")
            return f"Successfully created new page '{title}' with ID: {page_id}"
            
        except requests.RequestException as e:
            return f"Error accessing Notion API: {str(e)}"
        except (KeyError, IndexError) as e:
            return f"Error creating Notion page: {str(e)}"

    def notion_search(self, query: str) -> str:
        """
        Search Notion for pages, databases, and other content.
        
        :param query: The search query string
        :return: Formatted search results from Notion
        """
        access_token = os.getenv("NOTION_ACCESS_TOKEN")
        if not access_token:
            return "Error: NOTION_ACCESS_TOKEN environment variable is not set."

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                "https://api.notion.com/v1/search",
                headers=headers,
                json={"query": query}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                return f"No results found for query: '{query}'"
            
            result = f"Search Results for '{query}':\n\n"
            
            for i, item in enumerate(data["results"], 1):
                item_type = item.get("object", "unknown")
                item_id = item.get("id", "Unknown ID")
                
                if item_type == "page":
                    # Try to get page title
                    title = "Untitled Page"
                    properties = item.get("properties", {})
                    
                    # Find title property
                    for prop_name, prop_value in properties.items():
                        if prop_value.get("type") == "title":
                            title_objects = prop_value.get("title", [])
                            if title_objects:
                                title = title_objects[0].get("plain_text", "Untitled Page")
                                break
                    
                    result += f"{i}. Page: {title} (ID: {item_id})\n"
                
                elif item_type == "database":
                    title_objects = item.get("title", [])
                    title = title_objects[0]["plain_text"] if title_objects else "Untitled Database"
                    result += f"{i}. Database: {title} (ID: {item_id})\n"
                
                else:
                    result += f"{i}. {item_type.capitalize()}: (ID: {item_id})\n"
            
            return result
            
        except requests.RequestException as e:
            return f"Error accessing Notion API: {str(e)}"
        except (KeyError, IndexError) as e:
            return f"Error parsing Notion response: {str(e)}"

# Add a constants section at the bottom of the file
# This will help create the proper registration for the tool in OpenWebUI

NOTION_TOOL_CONFIG = {
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "notion_list_databases",
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
                "name": "notion_query_database",
                "description": "Query a specific Notion database and return its content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "The ID of the database to query"
                        },
                        "filter_str": {
                            "type": "string",
                            "description": "Optional filter criteria in JSON string format"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)"
                        }
                    },
                    "required": ["database_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "notion_create_page",
                "description": "Create a new page in a Notion database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "The ID of the database to create the page in"
                        },
                        "title": {
                            "type": "string",
                            "description": "The title of the new page"
                        },
                        "properties_str": {
                            "type": "string",
                            "description": "Optional additional properties in JSON string format"
                        },
                        "content_str": {
                            "type": "string",
                            "description": "Optional content blocks in JSON string format"
                        }
                    },
                    "required": ["database_id", "title"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "notion_search",
                "description": "Search Notion for pages, databases, and other content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query string"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
} 