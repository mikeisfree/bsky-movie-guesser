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
    """Initialize the database with necessary tables and add missing columns"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create players table if it doesn't exist
        print("Creating players table if not exists")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handle TEXT UNIQUE NOT NULL,
            display_name TEXT,
            total_points INTEGER DEFAULT 0,
            correct_guesses INTEGER DEFAULT 0,
            total_guesses INTEGER DEFAULT 0,
            first_seen INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
        )
        ''')
        
        # Query existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [table[0] for table in cursor.fetchall()]
        print(f"Existing tables: {existing_tables}")
        
        # Check player_responses table structure to determine if it uses 'correct' or 'is_correct'
        correct_column_name = None
        try:
            cursor.execute("PRAGMA table_info(player_responses)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'correct' in columns:
                correct_column_name = 'correct'
            elif 'is_correct' in columns:
                correct_column_name = 'is_correct'
            
            print(f"Using '{correct_column_name}' as the correctness column in player_responses")
            
            # If neither column exists, add one
            if correct_column_name is None and 'player_responses' in existing_tables:
                print("Adding 'correct' column to player_responses table")
                cursor.execute("ALTER TABLE player_responses ADD COLUMN correct BOOLEAN")
                correct_column_name = 'correct'
        except Exception as e:
            print(f"Error checking player_responses table: {e}")
        
        # Check if tournaments table exists and add missing column if needed
        if 'tournaments' in existing_tables:
            # Check if duration_days column exists
            cursor.execute("PRAGMA table_info(tournaments)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'duration_days' not in columns:
                print("Adding duration_days column to tournaments table")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN duration_days INTEGER NOT NULL DEFAULT 7")
            
            # Check and add other potentially missing columns
            if 'questions_per_day' not in columns:
                print("Adding questions_per_day column to tournaments table")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN questions_per_day INTEGER NOT NULL DEFAULT 4")
            
            if 'source_distribution' not in columns:
                print("Adding source_distribution column to tournaments table")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN source_distribution TEXT NOT NULL DEFAULT '{\"movie\": 0.5, \"trivia\": 0.5}'")
                
            if 'bonus_first' not in columns:
                print("Adding bonus points columns to tournaments table")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN bonus_first INTEGER NOT NULL DEFAULT 10")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN bonus_second INTEGER NOT NULL DEFAULT 5")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN bonus_third INTEGER NOT NULL DEFAULT 3")
                
            if 'active' not in columns:
                print("Adding active column to tournaments table")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN active BOOLEAN NOT NULL DEFAULT 1")
        else:
            # Create tournaments table if it doesn't exist
            print("Creating tournaments table")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                duration_days INTEGER NOT NULL DEFAULT 7,
                questions_per_day INTEGER NOT NULL DEFAULT 4,
                source_distribution TEXT NOT NULL DEFAULT '{"movie": 0.5, "trivia": 0.5}',
                bonus_first INTEGER NOT NULL DEFAULT 10,
                bonus_second INTEGER NOT NULL DEFAULT 5,
                bonus_third INTEGER NOT NULL DEFAULT 3,
                is_active BOOLEAN DEFAULT TRUE,
                total_rounds INTEGER DEFAULT 0
            )
            ''')
            
        # Check if trivia_questions table exists and add missing column if needed
        if 'trivia_questions' in existing_tables:
            # Check if image_url column exists
            cursor.execute("PRAGMA table_info(trivia_questions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'image_url' not in columns:
                print("Adding image_url column to trivia_questions table")
                cursor.execute("ALTER TABLE trivia_questions ADD COLUMN image_url TEXT")
        else:
            # Create trivia_questions table if it doesn't exist
            print("Creating trivia_questions table")
            cursor.execute('''
            CREATE TABLE trivia_questions (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                difficulty TEXT DEFAULT 'medium',
                image_url TEXT
            )
            ''')
            
            # Insert some sample trivia questions
            sample_questions = [
                ('Movies', 'What 1994 film had the tagline "Life is like a box of chocolates"?', 'Forrest Gump', 'easy', None),
                ('Science', 'What is the chemical symbol for gold?', 'Au', 'easy', None),
                ('History', 'Who was the first president of the United States?', 'George Washington', 'easy', None),
                ('Geography', 'What is the capital of Japan?', 'Tokyo', 'easy', None),
                ('Sports', 'Which sport is played at Wimbledon?', 'Tennis', 'easy', None)
            ]
            cursor.executemany(
                'INSERT INTO trivia_questions (category, question, answer, difficulty, image_url) VALUES (?, ?, ?, ?, ?)', 
                sample_questions
            )
            
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
        
        # Drop existing triggers first
        print("Dropping existing triggers")
        cursor.execute("DROP TRIGGER IF EXISTS register_player_on_response")
        cursor.execute("DROP TRIGGER IF EXISTS update_player_stats_on_response")
        
        # Create trigger for automatic player registration
        print("Creating trigger for automatic player registration")
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS register_player_on_response
        AFTER INSERT ON player_responses
        WHEN NOT EXISTS (
            SELECT 1 FROM players WHERE handle = NEW.handle
        )
        BEGIN
            INSERT INTO players (
                handle, 
                first_seen, 
                total_points,
                total_guesses,
                correct_guesses
            )
            VALUES (
                NEW.handle, 
                NEW.response_time,
                CASE WHEN NEW.is_correct = 1 OR NEW.correct = 1 THEN 1 ELSE 0 END,
                1,
                CASE WHEN NEW.is_correct = 1 OR NEW.correct = 1 THEN 1 ELSE 0 END
            );
        END;
        ''')

        # Create trigger to update player stats
        print("Creating trigger for automatic player stats update")
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_player_stats_on_response
        AFTER INSERT ON player_responses
        BEGIN
            UPDATE players 
            SET total_guesses = total_guesses + 1,
                correct_guesses = correct_guesses + CASE WHEN NEW.is_correct = 1 OR NEW.correct = 1 THEN 1 ELSE 0 END,
                total_points = total_points + CASE WHEN NEW.is_correct = 1 OR NEW.correct = 1 THEN 1 ELSE 0 END
            WHERE handle = NEW.handle;
        END;
        ''')

        # Ensure all changes are committed
        conn.commit()
