import sqlite3
import bcrypt
import sys

def reset_password(email, new_password):
    """Reset password for a user with the given email"""
    try:
        # Connect to the database
        conn = sqlite3.connect('data/webui.db')
        cursor = conn.cursor()
        
        # Find the user
        cursor.execute("SELECT id FROM user WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"No user found with email: {email}")
            return False
        
        user_id = user[0]
        
        # Hash the new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Find the auth record for this user
        cursor.execute("SELECT id FROM auth WHERE user_id = ?", (user_id,))
        auth = cursor.fetchone()
        
        if not auth:
            print(f"No auth record found for user: {email}")
            # If no auth record exists, create one
            auth_id = user_id  # Use user_id as auth_id for simplicity
            cursor.execute(
                "INSERT INTO auth (id, hashed_password, user_id) VALUES (?, ?, ?)",
                (auth_id, hashed_password, user_id)
            )
            print(f"Created new auth record for user: {email}")
        else:
            # Update the existing auth record
            cursor.execute(
                "UPDATE auth SET hashed_password = ? WHERE user_id = ?",
                (hashed_password, user_id)
            )
        
        # Commit the changes
        conn.commit()
        print(f"Password reset successfully for user: {email}")
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
        print("Usage: python reset_password.py <email> <new_password>")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    reset_password(email, new_password) 