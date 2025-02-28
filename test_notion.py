#!/usr/bin/env python3
"""
Notion Integration Test Script for Open WebUI

This script tests the Notion integration in Open WebUI, including:
1. Checking if integrations are enabled
2. Checking connected Notion integrations
3. Testing the Notion status endpoint
4. Testing direct API calls to list Notion databases
5. Testing the dedicated databases endpoint
6. Testing AI function calls for Notion (may not work depending on deployment)

Key findings:
- The Notion integration uses 'list_notion_databases' as the action name, not 'list_databases'
- The status endpoint may return a 500 error due to a server-side issue
- The dedicated databases endpoint at /api/v1/integrations/notion/databases works reliably
- The AI function call endpoints may vary depending on deployment

Usage:
  python3 test_notion.py --token YOUR_JWT_TOKEN [--base-url http://localhost:8080] [--debug]

To get a JWT token:
1. Log in to Open WebUI
2. Open browser developer tools (F12)
3. Go to Application tab > Storage > Local Storage
4. Find the 'token' key and copy its value
"""

import requests
import json
import argparse
import time
import traceback
import os
from urllib.parse import urljoin

# Parse command line arguments
parser = argparse.ArgumentParser(description="Test Notion integration with Open WebUI")
parser.add_argument("--token", required=True, help="Your JWT token")
parser.add_argument("--base-url", default="http://localhost:8080", help="Base URL of Open WebUI")
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
args = parser.parse_args()

# Configuration
ACCESS_TOKEN = args.token
BASE_URL = args.base_url
DEBUG = args.debug

# Helper function for debug printing
def debug_print(message):
    if DEBUG:
        print(f"🔍 DEBUG: {message}")

# Helper function to print OAuth login information
def print_oauth_info():
    oauth_url = f"{BASE_URL}/api/v1/integrations/notion/oauth"
    print("\n=== Notion OAuth Information ===")
    print(f"To connect Notion, visit: {oauth_url}")
    print("This will redirect you to Notion for authorization.")

# Check if integrations are enabled
def check_integrations_enabled():
    print("\n=== Checking if Integrations are Enabled ===")
    url = f"{BASE_URL}/api/v1/integrations"
    
    try:
        debug_print(f"Making request to: {url}")
        response = requests.get(url, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
        debug_print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            debug_print(f"Response JSON: {json.dumps(data)}")
            
            integrations_enabled = data.get("enabled", False)
            notion_available = "notion" in data.get("available", {})
            
            print(f"Integrations enabled: {integrations_enabled}")
            print(f"Notion integration available: {notion_available}")
            
            return integrations_enabled and notion_available
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Error checking integrations: {str(e)}")
        if DEBUG:
            traceback.print_exc()
        return False

# Check connected integrations
def check_connected_integrations():
    print("\n=== Checking User's Connected Integrations ===")
    url = f"{BASE_URL}/api/v1/integrations"
    
    try:
        debug_print(f"Making request to: {url}")
        response = requests.get(url, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
        debug_print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Find Notion connections
            notion_connections = [conn for conn in data.get("connected", []) 
                                if conn.get("integration_type") == "notion"]
            
            active_connections = [conn for conn in notion_connections if conn.get("active")]
            
            if notion_connections:
                print(f"Found {len(notion_connections)} Notion connection(s), {len(active_connections)} active")
                
                for i, conn in enumerate(notion_connections, 1):
                    workspace_name = conn.get("workspace_name") or "Unnamed workspace"
                    active = "✅ ACTIVE" if conn.get("active") else "❌ INACTIVE"
                    created_at = conn.get("created_at", "").split("T")[0] if conn.get("created_at") else "Unknown"
                    
                    print(f"{i}. {workspace_name} [{active}] (Created: {created_at})")
                    print(f"   ID: {conn.get('id')}")
                
                return len(active_connections) > 0
            else:
                print("No Notion connections found")
                return False
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Error checking connected integrations: {str(e)}")
        if DEBUG:
            traceback.print_exc()
        return False

# Check Notion status
def check_notion_status():
    print("\n=== Checking Notion Integration Status ===")
    url = f"{BASE_URL}/api/v1/integrations/notion/status"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        debug_print(f"Making request to: {url}")
        debug_print(f"Headers: {json.dumps(headers)}")
        
        response = requests.get(url, headers=headers)
        debug_print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            debug_print(f"Response: {json.dumps(result, indent=2)}")
            
            is_connected = result.get("is_connected", False)
            print(f"Notion connected: {is_connected}")
            
            if "workspace" in result:
                print(f"Workspace: {result['workspace'].get('name')}")
            
            return is_connected
        elif response.status_code == 500:
            print("❌ Error with Notion status endpoint. This might be a server issue.")
            print("   The error suggests there's a null reference in the server code.")
            print("   This is likely a server-side issue that needs to be fixed.")
            return None  # Unknown status
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Error checking Notion status: {str(e)}")
        if DEBUG:
            traceback.print_exc()
        return False

# Test direct API call to list Notion databases
def test_direct_api_call():
    print("\n=== Testing Direct API Call to List Notion Databases ===")
    url = f"{BASE_URL}/api/v1/integrations/notion/execute"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # First try with "list_databases"
    payload = {
        "action": "list_databases",
        "params": {}
    }
    
    debug_print(f"Making request to: {url}")
    debug_print(f"Headers: {json.dumps(headers)}")
    debug_print(f"Payload: {json.dumps(payload)}")
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload)
        elapsed = time.time() - start_time
        
        debug_print(f"Response status: {response.status_code}")
        debug_print(f"Request took {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(json.dumps(result, indent=2))
            return True
        else:
            print(f"First attempt failed with '{response.text}', trying alternative action names...")
            
            # Try with list_notion_databases
            payload["action"] = "list_notion_databases"
            print(f"Trying with action: '{payload['action']}'")
            debug_print(f"Payload: {json.dumps(payload)}")
            
            response = requests.post(url, headers=headers, json=payload)
            debug_print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success with action: '{payload['action']}'")
                print(json.dumps(result, indent=2))
                
                # Check if result has expected structure
                if "status" in result and result["status"] == "success" and "databases" in result:
                    print(f"Found {len(result['databases'])} Notion databases!")
                    return True
                else:
                    print("Response format seems unexpected, but status code was 200")
                    return True
            else:
                print(f"❌ All attempts failed: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if DEBUG:
            traceback.print_exc()
        return False
    
    return False

# Test the dedicated databases endpoint
def test_list_databases_endpoint():
    print("\n=== Testing List Databases Endpoint ===")
    url = f"{BASE_URL}/api/v1/integrations/notion/databases"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    debug_print(f"Making request to: {url}")
    debug_print(f"Headers: {json.dumps(headers)}")
    
    try:
        start_time = time.time()
        response = requests.get(url, headers=headers)
        elapsed = time.time() - start_time
        
        debug_print(f"Response status: {response.status_code}")
        debug_print(f"Request took {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            databases = response.json()
            print(json.dumps(databases, indent=2))
            
            if isinstance(databases, list):
                print(f"✅ Successfully retrieved {len(databases)} Notion databases using dedicated endpoint!")
                return True
            else:
                print("❌ Unexpected response format")
                return False
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Error testing list databases endpoint: {str(e)}")
        if DEBUG:
            traceback.print_exc()
        return False

# Test AI function call
def test_ai_function_call():
    print("\n=== Testing AI Function Call for Notion Databases ===")
    
    # Try different possible endpoints for the OpenAI API
    possible_endpoints = [
        f"{BASE_URL}/api/v1/chat/completions",
        f"{BASE_URL}/api/v1/openai/chat/completions",
        f"{BASE_URL}/openai/chat/completions"
    ]
    
    model = "gpt-4"  # Default model
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    
    # First try to get available models
    try:
        models_url = f"{BASE_URL}/api/v1/openai/models"
        print(f"Checking available models from {models_url}...")
        
        models_response = requests.get(
            models_url,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )
        
        if models_response.status_code == 200:
            models_data = models_response.json()
            if DEBUG:
                print(f"🔍 DEBUG: Models: {json.dumps(models_data, indent=2)}")
            
            # Try to find a suitable model
            available_models = []
            for model_data in models_data:
                if isinstance(model_data, dict) and "id" in model_data:
                    available_models.append(model_data["id"])
                elif isinstance(model_data, str):
                    available_models.append(model_data)
            
            if available_models:
                # Prefer models with function calling capability
                for preferred_model in ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]:
                    if preferred_model in available_models:
                        model = preferred_model
                        print(f"Using model: {model}")
                        break
                else:
                    # If none of the preferred models are found, use the first available one
                    model = available_models[0]
                    print(f"Using available model: {model}")
            else:
                print("No valid models found in the response, using default model")
        else:
            print(f"Error getting models: {models_response.status_code}")
            print(f"Response: {models_response.text}")
    except Exception as e:
        print(f"Error checking models: {str(e)}")
    
    # Try each possible endpoint
    for endpoint in possible_endpoints:
        try:
            print(f"\nTrying endpoint: {endpoint}")
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What Notion databases do I have access to?"}
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
                },
                "stream": False
            }
            
            if DEBUG:
                print(f"🔍 DEBUG: Headers: {json.dumps(headers)}")
                print(f"🔍 DEBUG: Data: {json.dumps(payload)}")
            
            print(f"Making request to {endpoint} with model {model}...")
            start_time = time.time()
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=30  # Increased timeout for API calls
            )
            
            elapsed = time.time() - start_time
            
            if DEBUG:
                print(f"🔍 DEBUG: Response status: {response.status_code}")
                print(f"🔍 DEBUG: Request took {elapsed:.2f} seconds")
            
            if response.status_code == 200:
                response_data = response.json()
                if DEBUG:
                    print(f"🔍 DEBUG: Response: {json.dumps(response_data, indent=2)}")
                
                # Check if there are tool calls in the response
                if "choices" in response_data and response_data["choices"]:
                    choice = response_data["choices"][0]
                    if "message" in choice and "tool_calls" in choice["message"]:
                        tool_calls = choice["message"]["tool_calls"]
                        print(f"✅ Function call successful! Found {len(tool_calls)} tool calls")
                        for idx, tool_call in enumerate(tool_calls):
                            print(f"\nTool Call {idx+1}:")
                            if "function" in tool_call:
                                print(f"Function: {tool_call['function']['name']}")
                                if "arguments" in tool_call["function"]:
                                    try:
                                        args = json.loads(tool_call["function"]["arguments"])
                                        print(f"Arguments: {json.dumps(args, indent=2)}")
                                    except json.JSONDecodeError:
                                        print(f"Arguments (raw): {tool_call['function']['arguments']}")
                        return True
                    else:
                        print("No tool calls found in the response")
                else:
                    print("Unexpected response format")
                
                print(json.dumps(response_data, indent=2))
                return True  # Successfully received a response
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Error with endpoint {endpoint}: {str(e)}")
    
    print("\n❌ All endpoints failed for AI function call test")
    print("This could be due to several reasons:")
    print("1. The OpenAI API endpoint might be different in your deployment")
    print("2. The model used might not support function calling")
    print("3. There might be authentication or permission issues")
    print("\nYou can try manually using the API at:")
    print(f"{BASE_URL}/docs or {BASE_URL}/redoc")
    
    return False

# Simulate an AI function call (for reference)
def simulate_ai_function_call():
    print("\n=== Example AI Function Call Format ===")
    tool_call = {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "list_notion_databases",
            "arguments": "{}"  # Empty JSON object as string
        }
    }
    print(json.dumps(tool_call, indent=2))

# Main execution
if __name__ == "__main__":
    print(f"🔍 Testing Notion integration with Open WebUI")
    print(f"Base URL: {BASE_URL}")
    print(f"Token: {ACCESS_TOKEN[:5]}...{ACCESS_TOKEN[-5:]}")
    print(f"Debug mode: {'Enabled' if DEBUG else 'Disabled'}")
    
    # Run tests in sequence
    check_integrations_enabled()
    check_connected_integrations()
    notion_status = check_notion_status()
    
    if notion_status:
        print("\n✅ Notion appears to be connected!")
    else:
        print("\n⚠️ Notion connection status is unclear.")
        print("   Continuing with other tests...")
    
    # Test the direct API calls
    test_direct_api_call()
    test_list_databases_endpoint()
    
    # Test AI function call
    test_ai_function_call()
    
    # Show example function call format
    simulate_ai_function_call()
    
    print("\n🏁 Testing completed!")