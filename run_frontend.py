"""
Run script for the BlueTrivia frontend.
This allows the frontend module to be run as a standalone application.
"""
import uvicorn
import os
import sys
from pathlib import Path
import sqlite3

# Add the project root directory to the path so Python can find the frontend module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_database_access():
    """Check if the database file exists and is accessible for read/write"""
    db_path = "bluetrivia.db"
    if not os.path.exists(db_path):
        print(f"❌ Database file not found at {db_path}")
        print("Creating a new database file with required tables.")
        return False
    
    try:
        # Test connection and write permission
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version")
        
        # Print database table information
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ Found {len(tables)} tables in database: {', '.join(t[0] for t in tables)}")
        
        # Check for players
        try:
            cursor.execute("SELECT COUNT(*) FROM players")
            player_count = cursor.fetchone()[0]
            print(f"✅ Found {player_count} players in database")
        except sqlite3.OperationalError:
            print("⚠️ No players table found in database")
        
        # Check for responses
        try:
            cursor.execute("SELECT COUNT(*) FROM player_responses")
            response_count = cursor.fetchone()[0]
            print(f"✅ Found {response_count} player responses in database")
            
            # Check correct/is_correct column
            try:
                cursor.execute("PRAGMA table_info(player_responses)")
                columns = [column[1] for column in cursor.fetchall()]
                if 'correct' in columns:
                    cursor.execute("SELECT COUNT(*) FROM player_responses WHERE correct = 1")
                    correct_count = cursor.fetchone()[0]
                    print(f"✅ Found {correct_count} correct answers (using 'correct' column)")
                elif 'is_correct' in columns:
                    cursor.execute("SELECT COUNT(*) FROM player_responses WHERE is_correct = 1")
                    correct_count = cursor.fetchone()[0]
                    print(f"✅ Found {correct_count} correct answers (using 'is_correct' column)")
                else:
                    print("⚠️ No correct/is_correct column found in player_responses")
            except Exception as e:
                print(f"⚠️ Error checking correct answers: {e}")
        except sqlite3.OperationalError:
            print("⚠️ No player_responses table found in database")
        
        # Check for tournaments
        try:
            cursor.execute("SELECT COUNT(*) FROM tournaments")
            tournament_count = cursor.fetchone()[0]
            print(f"✅ Found {tournament_count} tournaments in database")
        except sqlite3.OperationalError:
            print("⚠️ No tournaments table found in database")
        
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("ROLLBACK")
        conn.close()
        print(f"✅ Database at {db_path} is accessible with read/write permissions")
        return True
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        print("Make sure the database file has read/write permissions for the current user")
        return False

def ensure_directories():
    """Ensure all necessary directories exist for the frontend"""
    Path("frontend/static").mkdir(parents=True, exist_ok=True)
    Path("frontend/templates").mkdir(parents=True, exist_ok=True)
    Path("frontend/admin/templates/admin").mkdir(parents=True, exist_ok=True)
    Path("frontend/public/templates/public").mkdir(parents=True, exist_ok=True)
    Path("frontend/static/css").mkdir(parents=True, exist_ok=True)
    Path("frontend/static/js").mkdir(parents=True, exist_ok=True)

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import pydantic_settings
        import fastapi
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r frontend/requirements.txt")
        return False

if __name__ == "__main__":
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check database access
    if not check_database_access():
        print("⚠️ Will attempt to continue with limited database functionality")
    
    # Ensure directories exist
    ensure_directories()
    
    # Initialize database
    try:
        from frontend.database import init_db
        init_db()
        print("✅ Database schema initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        print("Attempting to continue anyway...")
    
    print("\n=== BlueTrivia Frontend ===")
    print("Starting FastAPI application on http://0.0.0.0:8000")
    print("- Main Dashboard: http://0.0.0.0:8000/")
    print("- Admin interface: http://0.0.0.0:8000/admin")
    
    # Run the FastAPI application
    try:
        uvicorn.run("frontend.app:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        print(f"❌ Error starting FastAPI application: {e}")
        sys.exit(1)
