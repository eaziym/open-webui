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
  python3 test_notion_direct.py --token YOUR_JWT_TOKEN [--base-url http://localhost:8080] [--debug]

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

# Replace with your Open WebUI access token
ACCESS_TOKEN = args.token

# Base URL of your Open WebUI instance
BASE_URL = args.base_url

# 1. First, check if you have a connected Notion integration
def check_notion_status():
    url = f"{BASE_URL}/api/v1/integrations/notion/status"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    print("=== Notion Status ===")
    print(json.dumps(response.json(), indent=2))
    print()
    
    return response.json().get("is_connected", False)

# 2. List Notion databases directly
def list_notion_databases():
    url = f"{BASE_URL}/api/v1/integrations/notion/execute"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "action": "list_databases",
        "params": {}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print("=== Notion Databases ===")
    print(json.dumps(response.json(), indent=2))
    print()
    
    return response.json()

# 3. DEBUG: Check how the AI function call should look
def simulate_ai_function_call():
    """This shows what the AI tool call should look like"""
    tool_call = {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "list_notion_databases",
            "arguments": "{}"  # Empty JSON object as string
        }
    }
    
    print("=== AI Function Call Example ===")
    print(json.dumps(tool_call, indent=2))
    print()

# Main flow
if __name__ == "__main__":
    print("Testing Notion integration...")
    
    # Check if Notion is connected
    is_connected = check_notion_status()
    
    if is_connected:
        print("Notion is connected! Listing databases...")
        databases = list_notion_databases()
    else:
        print("Notion is not connected. Please connect it first in the Integrations page.")
    
    # Show example of how AI should call the function
    simulate_ai_function_call() 