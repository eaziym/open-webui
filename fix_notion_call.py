#!/usr/bin/env python3
"""
Notion Function Call Fix

This script demonstrates how to properly call and handle the list_notion_databases
function in the Notion integration for Open WebUI.

This emulates what happens inside the OpenWebUI when an AI calls a function,
but with better error handling and debugging to understand what's happening.
"""

import json
import requests
import argparse
import traceback
import sys

def test_notion_databases(token, base_url="http://localhost:8080"):
    """Test Notion database listing through the direct API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test direct call to API endpoint for listing databases
    try:
        print("\n=== Testing direct API call ===")
        databases_url = f"{base_url}/api/v1/integrations/notion/databases"
        print(f"Calling endpoint: {databases_url}")
        
        response = requests.get(databases_url, headers=headers)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            databases = response.json()
            print(f"Found {len(databases)} databases:")
            for i, db in enumerate(databases, 1):
                print(f"  {i}. {db.get('title', 'Untitled')} - {db.get('id')}")
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()

def test_execute_endpoint(token, base_url="http://localhost:8080"):
    """Test the execute endpoint with the correct action name"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        print("\n=== Testing execute endpoint ===")
        execute_url = f"{base_url}/api/v1/integrations/notion/execute"
        print(f"Calling endpoint: {execute_url}")
        
        # First try with list_databases (incorrect)
        payload = {
            "action": "list_databases",
            "params": {}
        }
        
        print(f"Payload (incorrect action): {json.dumps(payload)}")
        response = requests.post(execute_url, headers=headers, json=payload)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Result: {json.dumps(result, indent=2)}")
        else:
            print(f"Error response: {response.text}")
        
        # Now try with list_notion_databases (correct)
        payload = {
            "action": "list_notion_databases",
            "params": {}
        }
        
        print(f"\nPayload (correct action): {json.dumps(payload)}")
        response = requests.post(execute_url, headers=headers, json=payload)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Result: {json.dumps(result, indent=2)}")
            
            if "databases" in result:
                print(f"Found {len(result['databases'])} databases:")
                for i, db in enumerate(result['databases'], 1):
                    print(f"  {i}. {db.get('title', 'Untitled')} - {db.get('id')}")
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()

def emulate_ai_function_call(token, base_url="http://localhost:8080"):
    """Emulate an AI function call to the Notion integration"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        print("\n=== Emulating AI function call ===")
        endpoint = f"{base_url}/api/v1/chat/completions"
        print(f"Endpoint: {endpoint}")
        
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "List my Notion databases."}
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
        
        print(f"Payload: {json.dumps(payload, indent=2)}")
        response = requests.post(endpoint, headers=headers, json=payload)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Result: {json.dumps(result, indent=2)}")
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Fix and test Notion function call handling")
    parser.add_argument("--token", required=True, help="JWT token for authentication")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL of the API")
    args = parser.parse_args()
    
    print(f"Testing Notion integration with token: {args.token[:10]}...")
    
    # Test direct database listing
    test_notion_databases(args.token, args.url)
    
    # Test execute endpoint
    test_execute_endpoint(args.token, args.url)
    
    # Emulate AI function call
    emulate_ai_function_call(args.token, args.url)
    
    print("\n=== Summary ===")
    print("Based on these tests, we can determine:")
    print("1. The correct action name is 'list_notion_databases' (not 'list_databases')")
    print("2. The function mapping in handle_notion_function_execution should use 'list_notion_databases'")
    print("3. Make sure the API server is running when using the AI function call")

if __name__ == "__main__":
    main() 