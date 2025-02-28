import sys
from open_webui.internal.db import get_db
from open_webui.config import Config

def enable_signup():
    """Enable user signups in the Open WebUI configuration"""
    try:
        with get_db() as db:
            # Get the latest config entry
            config = db.query(Config).order_by(Config.id.desc()).first()
            
            if not config:
                print("No configuration found in the database.")
                return False
            
            # Get current data
            config_data = config.data or {}
            
            # Initialize ui section if it doesn't exist
            if 'ui' not in config_data:
                config_data['ui'] = {}
            
            # Enable signup in the ui section
            config_data['ui']['enable_signup'] = True
            
            # Update the config
            config.data = config_data
            db.commit()
            
            print("User signups have been enabled successfully!")
            return True
    except Exception as e:
        print(f"Error enabling signups: {e}")
        return False

if __name__ == "__main__":
    enable_signup() 