import sqlite3
import json
import uuid
import secrets
import bcrypt
import time
import sys

def create_admin_user(username, email, password):
    """Create a new admin user in the database"""
    try:
        # Connect to the database
        conn = sqlite3.connect('data/webui.db')
        cursor = conn.cursor()
        
        # Check if user with same email already exists
        cursor.execute("SELECT id FROM user WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"User with email {email} already exists.")
            return False
        
        # Generate a unique ID for the user
        user_id = str(uuid.uuid4())
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Prepare the auth entry
        auth_id = str(uuid.uuid4())
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        
        # Insert the auth entry
        cursor.execute(
            "INSERT INTO auth (id, hashed_password, user_id) VALUES (?, ?, ?)",
            (auth_id, hashed_password, user_id)
        )
        
        # Insert the user entry
        cursor.execute(
            "INSERT INTO user (id, name, email, role, profile_image_url, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, email, "admin", "", current_time, current_time, current_time)
        )
        
        # Commit the changes
        conn.commit()
        print(f"Admin user '{username}' created successfully!")
        print(f"User ID: {user_id}")
        print(f"Email: {email}")
        print(f"Role: admin")
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <username> <email> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    create_admin_user(username, email, password) 