import sqlite3
import bcrypt
import uuid
import sys

def create_auth_for_user(email, password):
    """Create an auth record for an existing user"""
    try:
        # Connect to the database
        conn = sqlite3.connect('data/webui.db')
        cursor = conn.cursor()
        
        # Find the user to get their ID
        cursor.execute("SELECT id, name FROM user WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"No user found with email: {email}")
            return False
        
        user_id, user_name = user
        
        # Check if auth record already exists
        cursor.execute("SELECT id FROM auth WHERE email = ?", (email,))
        existing_auth = cursor.fetchone()
        
        if existing_auth:
            print(f"Auth record already exists for user: {email}")
            
            # Update the existing auth record with new password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute(
                "UPDATE auth SET password = ?, active = 1 WHERE email = ?",
                (hashed_password, email)
            )
            conn.commit()
            print(f"Updated password for user: {email}")
            return True
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create a new auth record
        auth_id = user_id  # Use user's ID as auth ID
        cursor.execute(
            "INSERT INTO auth (id, email, password, active) VALUES (?, ?, ?, ?)",
            (auth_id, email, hashed_password, 1)
        )
        
        # Commit the changes
        conn.commit()
        print(f"Created auth record for user: {user_name} ({email})")
        print(f"User ID: {user_id}")
        print(f"Auth ID: {auth_id}")
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
    if len(sys.argv) != 3:
        print("Usage: python create_auth.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    create_auth_for_user(email, password) 