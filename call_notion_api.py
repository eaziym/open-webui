#!/usr/bin/env python3
"""
Notion API Chat Completions Test

This script demonstrates how to properly call the Notion API through the chat completions
endpoint in Open WebUI. It shows the correct URL format and parameters needed to
make function calls work properly.

Usage:
  python3 call_notion_api.py --token YOUR_JWT_TOKEN [--url http://localhost:8080]
"""

import requests
import json
import argparse
import sys

def test_endpoint_options(token, base_url="http://localhost:8080"):
    """Test different endpoint patterns to find the correct one"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Payload for testing
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that can access Notion."},
            {"role": "user", "content": "List my Notion databases"}
        ]
    }
    
    # Test different endpoint patterns
    endpoints = [
        f"{base_url}/chat/completions",
        f"{base_url}/api/v1/chat/completions",
        f"{base_url}/openai/chat/completions",
        f"{base_url}/api/v1/openai/chat/completions"
    ]
    
    print("\n=== Testing different API endpoint patterns ===")
    for endpoint in endpoints:
        print(f"\nTrying endpoint: {endpoint}")
        try:
            response = requests.post(endpoint, headers=headers, json=payload)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                print("Endpoint is valid!")
                try:
                    result = response.json()
                    print_json_limited(result, depth=1)
                except:
                    print("Could not parse response as JSON")
            else:
                print("Endpoint returned an error")
                try:
                    error = response.json()
                    print(json.dumps(error, indent=2))
                except:
                    print(response.text[:100] + "..." if len(response.text) > 100 else response.text)
        except Exception as e:
            print(f"Error: {str(e)}")

def test_available_models(token, base_url="http://localhost:8080"):
    """Test to see which models are available"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    endpoints = [
        f"{base_url}/api/v1/openai/models",
        f"{base_url}/openai/models",
        f"{base_url}/api/v1/models"
    ]
    
    print("\n=== Testing model availability ===")
    for endpoint in endpoints:
        print(f"\nTrying models endpoint: {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                print("Endpoint is valid!")
                try:
                    result = response.json()
                    if "data" in result and isinstance(result["data"], list):
                        print(f"Found {len(result['data'])} models:")
                        for i, model in enumerate(result["data"][:5], 1):  # Show first 5 models
                            print(f"  {i}. {model.get('id', 'Unknown')}")
                        if len(result["data"]) > 5:
                            print(f"  ... and {len(result['data']) - 5} more")
                    else:
                        print_json_limited(result, depth=1)
                except:
                    print("Could not parse response as JSON")
            else:
                print("Endpoint returned an error")
                try:
                    error = response.json()
                    print(json.dumps(error, indent=2))
                except:
                    print(response.text[:100] + "..." if len(response.text) > 100 else response.text)
        except Exception as e:
            print(f"Error: {str(e)}")

def test_chat_completions(token, base_url="http://localhost:8080"):
    """
    Test the chat completions endpoint with Notion function calling
    
    This emulates what happens when a user asks to list Notion databases in chat
    """
    # Try different endpoint patterns
    endpoints = [
        f"{base_url}/chat/completions",
        f"{base_url}/api/v1/chat/completions",
        f"{base_url}/openai/chat/completions",
        f"{base_url}/api/v1/openai/chat/completions"
    ]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # This is the payload that will trigger the list_notion_databases function
    payload = {
        "model": "gpt-4",  # You can use any model that supports function calling
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that can access Notion."},
            {"role": "user", "content": "List my Notion databases"}
        ],
        "tools": [
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
            }
        ],
        "tool_choice": {
            "type": "function",
            "function": {"name": "list_notion_databases"}
        }
    }
    
    print("\n=== Testing chat completions with Notion function call ===")
    for endpoint in endpoints:
        print(f"\nTrying endpoint: {endpoint}")
        try:
            response = requests.post(endpoint, headers=headers, json=payload)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                print("Success! Endpoint is valid!")
                try:
                    result = response.json()
                    # Print a limited view of the result
                    print("\nResponse (limited):")
                    print_json_limited(result, depth=1)
                    
                    # Check if the response contains function calls and responses
                    check_function_calls(result)
                except json.JSONDecodeError:
                    print("\nResponse is not valid JSON. Raw response:")
                    print(response.text[:500])  # Print first 500 chars to avoid overwhelming output
            else:
                print("Endpoint returned an error")
                try:
                    error = response.json()
                    print(json.dumps(error, indent=2))
                except:
                    print(response.text[:100] + "..." if len(response.text) > 100 else response.text)
                    
        except Exception as e:
            print(f"Error: {str(e)}")

def test_direct_api(token, base_url="http://localhost:8080"):
    """Test the direct Notion API endpoints for comparison"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test the databases endpoint
    print("\n=== Testing direct Notion endpoints ===")
    
    endpoints = [
        f"{base_url}/api/v1/integrations/notion/databases",
        f"{base_url}/integrations/notion/databases"
    ]
    
    for endpoint in endpoints:
        print(f"\nTrying endpoint: {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                print("Success! Endpoint is valid!")
                result = response.json()
                print(f"Found {len(result)} databases:")
                for i, db in enumerate(result, 1):
                    print(f"  {i}. {db.get('title', 'Untitled')} (ID: {db.get('id')})")
            else:
                print("Endpoint returned an error")
                try:
                    error = response.json()
                    print(json.dumps(error, indent=2))
                except:
                    print(response.text[:100] + "..." if len(response.text) > 100 else response.text)
        except Exception as e:
            print(f"Error: {str(e)}")

def check_function_calls(response):
    """Check if the response contains function calls and their responses"""
    # Check for the first choice
    if "choices" in response and len(response["choices"]) > 0:
        choice = response["choices"][0]
        
        # Check if the message contains tool calls
        if "message" in choice and "tool_calls" in choice["message"]:
            tool_calls = choice["message"]["tool_calls"]
            print(f"\nFound {len(tool_calls)} tool call(s):")
            
            for i, tool_call in enumerate(tool_calls, 1):
                if tool_call.get("type") == "function":
                    function = tool_call.get("function", {})
                    print(f"  Tool call {i}: {function.get('name')} - Arguments: {function.get('arguments')}")
        
        # Check if there's a content field with final response
        if "message" in choice and "content" in choice["message"] and choice["message"]["content"]:
            print("\nFinal response content:")
            print(choice["message"]["content"])

def print_json_limited(obj, depth=2, current_depth=0):
    """Print a JSON object with limited depth for readability"""
    if current_depth >= depth:
        if isinstance(obj, dict) and len(obj) > 0:
            print("{...}")
        elif isinstance(obj, list) and len(obj) > 0:
            print("[...]")
        else:
            print(obj)
    elif isinstance(obj, dict):
        print("{")
        for i, (k, v) in enumerate(obj.items()):
            print(f"  {'  ' * current_depth}\"{k}\": ", end="")
            print_json_limited(v, depth, current_depth + 1)
            if i < len(obj) - 1:
                print(",")
        print("}")
    elif isinstance(obj, list):
        if len(obj) == 0:
            print("[]")
        else:
            print("[")
            for i, item in enumerate(obj):
                print(f"  {'  ' * current_depth}", end="")
                print_json_limited(item, depth, current_depth + 1)
                if i < len(obj) - 1:
                    print(",")
            print("]")
    else:
        print(json.dumps(obj))

def main():
    parser = argparse.ArgumentParser(description="Test Notion API through chat completions")
    parser.add_argument("--token", required=True, help="Your JWT token")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL (without /api/v1)")
    args = parser.parse_args()

    print("=== Notion API Chat Completions Test ===")
    print(f"Base URL: {args.url}")
    print(f"Token: {args.token[:10]}...")
    
    # Test different API endpoints
    test_endpoint_options(args.token, args.url)
    
    # Test available models
    test_available_models(args.token, args.url)
    
    # Test the direct API first as a baseline
    test_direct_api(args.token, args.url)
    
    # Test the chat completions endpoint
    test_chat_completions(args.token, args.url)
    
    print("\n=== IMPORTANT NOTES ===")
    print("1. The correct endpoint for chat completions depends on your server configuration")
    print("2. The function name must be 'list_notion_databases' (not 'list_databases')")
    print("3. If you're not getting results, check that your Notion integration is connected")
    print("4. You can always use the direct API endpoint: /api/v1/integrations/notion/databases")

if __name__ == "__main__":
    main() 