import sqlite3
import json
from datetime import datetime

def check_users():
    """List all users and their credentials from the database"""
    try:
        # Connect to the database
        conn = sqlite3.connect('data/webui.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query all users
        cursor.execute("SELECT id, name, email, role, api_key, created_at, updated_at, settings FROM user")
        users = cursor.fetchall()
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"Found {len(users)} users in the database:")
        print("-" * 80)
        
        # Display user information
        for user in users:
            print(f"User ID: {user['id']}")
            print(f"Name: {user['name']}")
            print(f"Email: {user['email']}")
            print(f"Role: {user['role']}")
            print(f"API Key: {user['api_key'] or 'None'}")
            
            # Convert timestamps to readable dates
            if user['created_at']:
                created_at = datetime.fromtimestamp(user['created_at']/1000).strftime('%Y-%m-%d %H:%M:%S')
                print(f"Created: {created_at}")
            
            if user['updated_at']:
                updated_at = datetime.fromtimestamp(user['updated_at']/1000).strftime('%Y-%m-%d %H:%M:%S')
                print(f"Updated: {updated_at}")
            
            # Parse and display settings if available
            if user['settings']:
                try:
                    settings = json.loads(user['settings'])
                    if settings and isinstance(settings, dict):
                        print("Settings:")
                        for key, value in settings.items():
                            print(f"  {key}: {value}")
                    else:
                        print("Settings: Empty or not a dictionary")
                except json.JSONDecodeError:
                    print("Settings: Invalid JSON format")
            else:
                print("Settings: None")
            
            print("-" * 80)
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_users() 