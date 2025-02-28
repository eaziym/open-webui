import sqlite3
import json

def check_auth():
    """Check the auth table for authentication information"""
    try:
        # Connect to the database
        conn = sqlite3.connect('data/webui.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query auth table
        cursor.execute("SELECT * FROM auth")
        auth_records = cursor.fetchall()
        
        if not auth_records:
            print("No auth records found in the database.")
            return
        
        print(f"Found {len(auth_records)} auth records in the database:")
        print("-" * 80)
        
        # Get user information for reference
        cursor.execute("SELECT id, name, email FROM user")
        users = {row['id']: {'name': row['name'], 'email': row['email']} for row in cursor.fetchall()}
        
        # Display auth information
        for auth in auth_records:
            print(f"Auth ID: {auth['id']}")
            
            # Get associated user information
            user_id = auth.get('user_id')
            if user_id and user_id in users:
                print(f"User: {users[user_id]['name']} ({users[user_id]['email']})")
                print(f"User ID: {user_id}")
            else:
                print(f"User ID: {user_id} (User not found)")
            
            # Show if password is set
            if 'hashed_password' in auth and auth['hashed_password']:
                print("Password: [Set]")
            else:
                print("Password: [Not set]")
            
            print("-" * 80)
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_auth() 