import sys
from open_webui.internal.db import get_db
from open_webui.models.auths import Auth
from open_webui.models.users import User

def delete_user_by_email(email):
    """Delete a user by their email address"""
    try:
        with get_db() as db:
            # Find the auth record
            auth = db.query(Auth).filter_by(email=email).first()
            
            if not auth:
                print(f"No user found with email: {email}")
                return False
            
            # Get the user ID from auth
            user_id = auth.id
            
            # Delete the user record
            user_deleted = db.query(User).filter_by(id=user_id).delete()
            
            # Delete the auth record
            auth_deleted = db.query(Auth).filter_by(id=user_id).delete()
            
            db.commit()
            
            print(f"User with email {email} deleted successfully.")
            print(f"Records deleted: User: {user_deleted}, Auth: {auth_deleted}")
            return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False

def delete_all_users():
    """Delete all users from the database"""
    try:
        with get_db() as db:
            # Get all auth records
            auth_records = db.query(Auth).all()
            
            if not auth_records:
                print("No users found in the database.")
                return False
            
            count = 0
            for auth in auth_records:
                # Delete user record
                db.query(User).filter_by(id=auth.id).delete()
                # Delete auth record
                db.query(Auth).filter_by(id=auth.id).delete()
                count += 1
            
            db.commit()
            
            print(f"All users deleted successfully. Total: {count}")
            return True
    except Exception as e:
        print(f"Error deleting all users: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments, delete all users
        print("WARNING: This will delete ALL users from the database.")
        confirmation = input("Are you sure you want to continue? (yes/no): ")
        if confirmation.lower() == "yes":
            delete_all_users()
        else:
            print("Operation cancelled.")
    elif len(sys.argv) == 2:
        # Delete specific user by email
        email = sys.argv[1]
        delete_user_by_email(email)
    else:
        print("Usage: python delete_users.py [email]")
        print("       - With no arguments: Deletes ALL users (will ask for confirmation)")
        print("       - With email argument: Deletes only the specified user") 