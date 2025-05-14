import sqlite3
import time
from typing import Dict, Any, List, Optional, Tuple


class Database:
    """Database manager for BlueTrivia"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the database schema if needed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Game rounds table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    start_time INTEGER NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    correct_attempts INTEGER DEFAULT 0,
                    percentage INTEGER DEFAULT 0,
                    tournament_id INTEGER DEFAULT NULL,
                    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
                )
            """)
            
            # Player guesses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_guesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    handle TEXT NOT NULL,
                    round_post_id TEXT NOT NULL,
                    guess TEXT NOT NULL,
                    is_correct BOOLEAN NOT NULL,
                    score INTEGER NOT NULL,
                    timestamp INTEGER NOT NULL
                )
            """)
            
            # Players table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    handle TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    total_points INTEGER DEFAULT 0,
                    correct_guesses INTEGER DEFAULT 0,
                    total_guesses INTEGER DEFAULT 0,
                    first_seen INTEGER NOT NULL
                )
            """)
            
            # Tournaments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    start_time INTEGER NOT NULL,
                    end_time INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    total_rounds INTEGER DEFAULT 0
                )
            """)
            
            # Tournament players table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournament_players (
                    tournament_id INTEGER NOT NULL,
                    player_id INTEGER NOT NULL,
                    points INTEGER DEFAULT 0,
                    PRIMARY KEY (tournament_id, player_id),
                    FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
                    FOREIGN KEY (player_id) REFERENCES players(id)
                )
            """)
            
            conn.commit()
    
    def store_round(self, source_name: str, question_text: str, answer: str, post_id: str) -> int:
        """Stores a new game round and returns its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            current_time = int(time.time())
            
            cursor.execute("""
                INSERT INTO rounds (source_name, question_text, answer, post_id, start_time)
                VALUES (?, ?, ?, ?, ?)
            """, (source_name, question_text, answer, post_id, current_time))
            
            return cursor.lastrowid
    
    def update_round_results(self, round_id: int, attempts: int, correct_attempts: int, percentage: int):
        """Updates a round with its results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE rounds
                SET attempts = ?, correct_attempts = ?, percentage = ?
                WHERE id = ?
            """, (attempts, correct_attempts, percentage, round_id))
            
            conn.commit()
    
    def store_player_guess(self, handle: str, round_post_id: str, guess: str, 
                           is_correct: bool, score: int):
        """Stores a player's guess and updates their stats"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            current_time = int(time.time())
            
            # Store the guess
            cursor.execute("""
                INSERT INTO player_guesses (handle, round_post_id, guess, is_correct, score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (handle, round_post_id, guess, is_correct, score, current_time))
            
            # Update player stats
            self._update_player_stats(conn, handle, is_correct)
            
            conn.commit()
    
    def _update_player_stats(self, conn, handle: str, is_correct: bool):
        """Updates a player's statistics"""
        cursor = conn.cursor()
        
        # Check if player exists
        cursor.execute("SELECT id FROM players WHERE handle = ?", (handle,))
        player = cursor.fetchone()
        
        current_time = int(time.time())
        
        if player:
            # Update existing player
            points_to_add = 1 if is_correct else 0
            correct_to_add = 1 if is_correct else 0
            
            cursor.execute("""
                UPDATE players
                SET total_points = total_points + ?,
                    correct_guesses = correct_guesses + ?,
                    total_guesses = total_guesses + 1
                WHERE handle = ?
            """, (points_to_add, correct_to_add, handle))
        else:
            # Create new player
            points = 1 if is_correct else 0
            correct = 1 if is_correct else 0
            
            cursor.execute("""
                INSERT INTO players (handle, total_points, correct_guesses, total_guesses, first_seen)
                VALUES (?, ?, ?, 1, ?)
            """, (handle, points, correct, current_time))
    
    def get_player_stats(self, handle: str) -> Optional[Dict[str, Any]]:
        """Gets statistics for a player"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT handle, display_name, total_points, correct_guesses, total_guesses
                FROM players
                WHERE handle = ?
            """, (handle,))
            
            player = cursor.fetchone()
            
            if player:
                return dict(player)
            return None
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Gets the top players by points"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT handle, display_name, total_points, correct_guesses, total_guesses
                FROM players
                ORDER BY total_points DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def create_tournament(self, name: str, duration_days: int = 7) -> int:
        """Creates a new tournament"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            current_time = int(time.time())
            end_time = current_time + (duration_days * 24 * 60 * 60)
            
            cursor.execute("""
                INSERT INTO tournaments (name, start_time, end_time)
                VALUES (?, ?, ?)
            """, (name, current_time, end_time))
            
            return cursor.lastrowid
    
    def get_active_tournament(self) -> Optional[Dict[str, Any]]:
        """Gets the currently active tournament if any"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            current_time = int(time.time())
            
            cursor.execute("""
                SELECT id, name, start_time, end_time, total_rounds
                FROM tournaments
                WHERE is_active = TRUE AND end_time > ?
                ORDER BY start_time DESC
                LIMIT 1
            """, (current_time,))
            
            tournament = cursor.fetchone()
            
            if tournament:
                return dict(tournament)
            return None
