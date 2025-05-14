import sqlite3
from sqlite3 import Connection
from contextlib import contextmanager
from typing import Generator
import os
from pathlib import Path

from frontend.config import settings


@contextmanager
def get_db() -> Generator[Connection, None, None]:
    """Create a database connection context manager"""
    conn = None
    try:
        # Use the database file in the root directory
        db_path = "bluetrivia.db"
        
        # If that specific path doesn't exist, try fallback options
        if not os.path.exists(db_path):
            # Try the environment variable if set
            if settings.db_file and os.path.exists(settings.db_file):
                db_path = settings.db_file
            # Or try the configured path
            elif os.path.exists(settings.db_path):
                db_path = settings.db_path
        
        print(f"Connecting to database at: {db_path}")
        
        # Connect to the database with read/write permissions
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        
        yield conn
    finally:
        if conn:
            conn.close()


def init_db():
    """Initialize the database with necessary tables if they don't exist"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Query existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [table[0] for table in cursor.fetchall()]
        print(f"Existing tables: {existing_tables}")
        
        # Create tournaments table if it doesn't exist
        if 'tournaments' not in existing_tables:
            print("Creating tournaments table")
            cursor.execute('''
            CREATE TABLE tournaments (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                start_date TIMESTAMP NOT NULL,
                duration_days INTEGER NOT NULL,
                questions_per_day INTEGER NOT NULL,
                source_distribution TEXT NOT NULL,  -- JSON string
                bonus_first INTEGER NOT NULL,
                bonus_second INTEGER NOT NULL, 
                bonus_third INTEGER NOT NULL,
                active BOOLEAN NOT NULL DEFAULT 1
            )
            ''')
        
        # Create tournament_results table if it doesn't exist
        if 'tournament_results' not in existing_tables:
            print("Creating tournament_results table")
            cursor.execute('''
            CREATE TABLE tournament_results (
                tournament_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                total_points INTEGER NOT NULL DEFAULT 0,
                final_position INTEGER,
                bonus_points INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (tournament_id, player_id)
            )
            ''')
            
        # Create round_results table if it doesn't exist
        if 'round_results' not in existing_tables:
            print("Creating round_results table")
            cursor.execute('''
            CREATE TABLE round_results (
                id INTEGER PRIMARY KEY,
                round_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                correct BOOLEAN NOT NULL,
                position INTEGER,
                points_earned INTEGER NOT NULL
            )
            ''')
            
        # Add additional tables only if needed
        
        # Ensure all changes are committed
        conn.commit()
