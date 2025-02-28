import sqlite3

def list_tables():
    """List all tables in the database and their schema"""
    try:
        # Connect to the database
        conn = sqlite3.connect('data/webui.db')
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} tables in the database:")
        
        # Print schema for each table
        for table in tables:
            table_name = table[0]
            print(f"\n{'='*40}")
            print(f"TABLE: {table_name}")
            print(f"{'='*40}")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # Print column details
            print(f"{'Column Name':<20} {'Type':<15} {'Not Null':<10} {'Primary Key':<15}")
            print(f"{'-'*20} {'-'*15} {'-'*10} {'-'*15}")
            for col in columns:
                col_id, name, data_type, not_null, default_val, primary_key = col
                print(f"{name:<20} {data_type:<15} {'Yes' if not_null else 'No':<10} {'Yes' if primary_key else 'No':<15}")
            
            # Print row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            print(f"\nTotal rows: {row_count}")
            
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    list_tables() 