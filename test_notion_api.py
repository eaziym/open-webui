#!/usr/bin/env python3
"""
Direct Notion API Test Script

This script directly accesses the Notion API through the Open WebUI API endpoints,
bypassing the AI function call mechanism that might be causing issues.

This helps verify:
1. That your Notion integration is working correctly
2. That you can access your Notion databases
3. The format of the database information returned by the API

Usage:
  python3 test_notion_api.py --token YOUR_JWT_TOKEN [--url http://localhost:8080]
"""

import requests
import json
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Test Notion API directly")
    parser.add_argument("--token", required=True, help="Your JWT token")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL of the API")
    args = parser.parse_args()

    token = args.token
    base_url = args.url
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("Testing Notion API directly...")
    
    # First, check if Notion is connected
    print("\n1. Checking Notion status...")
    try:
        status_url = f"{base_url}/api/v1/integrations/notion/status"
        response = requests.get(status_url, headers=headers)
        
        if response.status_code == 200:
            status = response.json()
            print(f"Status response: {json.dumps(status, indent=2)}")
            print(f"Notion connected: {status.get('is_connected', False)}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error checking status: {str(e)}")
    
    # Try to list databases using the dedicated endpoint
    print("\n2. Listing databases using dedicated endpoint...")
    try:
        databases_url = f"{base_url}/api/v1/integrations/notion/databases"
        response = requests.get(databases_url, headers=headers)
        
        if response.status_code == 200:
            databases = response.json()
            print(f"Found {len(databases)} databases:")
            for i, db in enumerate(databases, 1):
                print(f"  {i}. {db.get('title', 'Untitled')} (ID: {db.get('id')})")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error listing databases: {str(e)}")
    
    # Try using the execute endpoint with list_notion_databases action
    print("\n3. Testing execute endpoint with list_notion_databases action...")
    try:
        execute_url = f"{base_url}/api/v1/integrations/notion/execute"
        payload = {
            "action": "list_notion_databases",
            "params": {}
        }
        
        response = requests.post(execute_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Result: {json.dumps(result, indent=2)}")
            
            if "databases" in result:
                print(f"Found {len(result['databases'])} databases:")
                for i, db in enumerate(result['databases'], 1):
                    print(f"  {i}. {db.get('title', 'Untitled')} (ID: {db.get('id')})")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error executing action: {str(e)}")

if __name__ == "__main__":
    main() 