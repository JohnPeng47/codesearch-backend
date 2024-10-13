import sqlite3
import sys

def add_use_cache_field(db_path):
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Add the use_cache column to the serializedlmp table
        cursor.execute("ALTER TABLE serializedlmp ADD COLUMN use_cache INTEGER")

        # Set a default value for existing rows (0 for False)
        cursor.execute("UPDATE serializedlmp SET use_cache = 0")

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

        print("Successfully added 'use_cache' field to the serializedlmp table.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <path_to_sqlite_db>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    add_use_cache_field(db_path)