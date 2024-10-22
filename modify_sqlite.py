import sqlite3
import sys
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

# Dictionary of valid SQLite types and their Python equivalents
VALID_TYPES = {
    'INTEGER': int,
    'TEXT': str,
    'REAL': float,
    'BLOB': bytes,
    'BOOLEAN': bool,  # Will be stored as INTEGER in SQLite
    'DATETIME': str,  # Will be stored as TEXT in SQLite
    'NUMERIC': (int, float)  # Can accept both integers and floats
}

def find_db_files(directory: str) -> List[Path]:
    """
    Recursively find all .db files in the given directory.
    
    Args:
        directory: Root directory to search in
        
    Returns:
        List of Path objects for all found .db files
    """
    db_files = []
    root_path = Path(directory)
    
    try:
        for path in root_path.rglob('*.db'):
            if path.is_file():
                db_files.append(path)
    except Exception as e:
        print(f"Error searching directory {directory}: {e}")
        sys.exit(1)
        
    return db_files

def validate_column_type(col_type: str) -> bool:
    """
    Validate if the provided column type is supported in SQLite.
    
    Args:
        col_type: The column type to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return col_type.upper() in VALID_TYPES

def get_default_value(col_type: str) -> Any:
    """
    Get a sensible default value for the given column type.
    
    Args:
        col_type: The SQLite column type
        
    Returns:
        A default value appropriate for the type
    """
    col_type = col_type.upper()
    defaults = {
        'INTEGER': 0,
        'TEXT': '',
        'REAL': 0.0,
        'BLOB': None,
        'BOOLEAN': 0,
        'DATETIME': None,
        'NUMERIC': 0
    }
    return defaults.get(col_type)

def is_valid_sqlite_db(db_path: Path) -> bool:
    """
    Check if the file is a valid SQLite database.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        bool: True if valid SQLite database, False otherwise
    """
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        conn.close()
        return True
    except sqlite3.Error:
        return False

def add_column_to_table(
    db_path: Path,
    table_name: str,
    col_name: str,
    col_type: str,
    default_value: Optional[Any] = None
) -> bool:
    """
    Add a new column to an existing SQLite table with validation.
    
    Args:
        db_path: Path to the SQLite database
        table_name: Name of the table to modify
        col_name: Name of the column to add
        col_type: Type of the column to add
        default_value: Optional default value for the column
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Validate column type
    col_type = col_type.upper()
    if not validate_column_type(col_type):
        valid_types = ', '.join(VALID_TYPES.keys())
        print(f"Invalid column type: {col_type}. Valid types are: {valid_types}")
        return False

    # Use provided default value or get a sensible default
    if default_value is None:
        default_value = get_default_value(col_type)

    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        if not cursor.fetchone():
            print(f"Table '{table_name}' does not exist in {db_path.name}")
            conn.close()
            return False

        # Check if column already exists
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]
        if col_name in columns:
            print(f"Column '{col_name}' already exists in table '{table_name}' in {db_path.name}")
            conn.close()
            return False

        # Add the new column
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")

        # Set default value if provided
        if default_value is not None:
            cursor.execute(
                f"UPDATE {table_name} SET {col_name} = ?",
                (default_value,)
            )

        # Commit the changes and close the connection
        conn.commit()
        conn.close()
        print(f"Successfully added '{col_name}' ({col_type}) to the {table_name} table in {db_path.name}")
        return True
    
    except sqlite3.Error as e:
        print(f"Database error occurred in {db_path.name}: {e}")
        return False

def process_directory(
    directory: str,
    table_name: str,
    col_name: str,
    col_type: str,
    default_value: Optional[Any] = None
) -> None:
    """
    Process all .db files in a directory and its subdirectories.
    
    Args:
        directory: Root directory to search for .db files
        table_name: Name of the table to modify
        col_name: Name of the column to add
        col_type: Type of the column to add
        default_value: Optional default value for the column
    """
    db_files = find_db_files(directory)
    
    if not db_files:
        print(f"No .db files found in {directory}")
        return
    
    print(f"Found {len(db_files)} database files:")
    for db_path in db_files:
        print(f"Processing: {db_path}")
        if not is_valid_sqlite_db(db_path):
            print(f"Skipping {db_path.name}: Not a valid SQLite database")
            continue
            
        add_column_to_table(db_path, table_name, col_name, col_type, default_value)
    
    print("\nProcessing complete!")

if __name__ == "__main__":
    if len(sys.argv) not in [4, 5, 6]:
        print("Usage: python script_name.py <directory_path> <table_name> <column_name> <column_type> [default_value]\n")
        print("Valid SQL types:")
        for sql_type, py_type in VALID_TYPES.items():
            print(f"{sql_type} ({py_type})")

        sys.exit(1)
    
    directory = sys.argv[1]
    table_name = sys.argv[2]
    col_name = sys.argv[3]
    col_type = sys.argv[4] if len(sys.argv) >= 5 else 'INTEGER'
    default_value = sys.argv[5] if len(sys.argv) >= 6 else None

    process_directory(directory, table_name, col_name, col_type, default_value)