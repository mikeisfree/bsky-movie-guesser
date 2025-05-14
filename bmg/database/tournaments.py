from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlite3 import Connection, Cursor
from typing import Union, List


@dataclass
class TournamentModel:
    rowid: int
    name: str
    start_date: str
    end_date: str
    is_active: bool
    rounds_total: int
    rounds_completed: int


@dataclass
class TournamentPlayerModel:
    rowid: int
    tournament_id: int
    handle: str
    points: int
    correct_answers: int
    total_answers: int


class Tournaments:
    def __init__(self, con: Connection, cursor: Cursor):
        self.con = con
        self.cursor = cursor

        self._create_tables()

    def _create_tables(self):
        # Tournaments table
        query = """
        CREATE TABLE IF NOT EXISTS tournaments (
            NAME             TEXT,
            START_DATE       TEXT,
            END_DATE         TEXT,
            IS_ACTIVE        INTEGER DEFAULT 1,
            ROUNDS_TOTAL     INTEGER DEFAULT 0,
            ROUNDS_COMPLETED INTEGER DEFAULT 0
        )
        """
        self.cursor.execute(query)
        
        # Tournament players table
        query = """
        CREATE TABLE IF NOT EXISTS tournament_players (
            TOURNAMENT_ID    INTEGER,
            HANDLE           TEXT,
            POINTS           INTEGER DEFAULT 0,
            CORRECT_ANSWERS  INTEGER DEFAULT 0,
            TOTAL_ANSWERS    INTEGER DEFAULT 0,
            
            FOREIGN KEY (TOURNAMENT_ID) REFERENCES tournaments (rowid),
            PRIMARY KEY (TOURNAMENT_ID, HANDLE)
        )
        """
        self.cursor.execute(query)

    def create_tournament(self, name: str, rounds_total: int, duration_days: int = 7):
        start_date = datetime.now().isoformat()
        end_date = (datetime.now() + timedelta(days=duration_days)).isoformat()

        query = """
        INSERT INTO tournaments (NAME, START_DATE, END_DATE, ROUNDS_TOTAL)
            VALUES (?, ?, ?, ?)
        """

        self.cursor.execute(query, (name, start_date, end_date, rounds_total))
        self.con.commit()
        return self.cursor.lastrowid

    def get_active_tournament(self):
        query = ('SELECT rowid, NAME, START_DATE, END_DATE, IS_ACTIVE, '
                 'ROUNDS_TOTAL, ROUNDS_COMPLETED FROM tournaments WHERE IS_ACTIVE=1')
        self.cursor.execute(query)
        data = self.cursor.fetchone()
        return TournamentModel(*data) if data else None
    
    def update_tournament_progress(self, tournament_id: int):
        """Increment the completed rounds count for a tournament"""
        query = 'UPDATE tournaments SET ROUNDS_COMPLETED = ROUNDS_COMPLETED + 1 WHERE rowid=?'
        self.cursor.execute(query, (tournament_id,))
        self.con.commit()
        
    def add_player_points(self, tournament_id: int, handle: str, points: int = 1, 
                          is_correct: bool = True):
        """Add points for a player in a tournament"""
        # First check if player exists in tournament
        self.cursor.execute('SELECT rowid FROM tournament_players WHERE TOURNAMENT_ID=? AND HANDLE=?',
                          (tournament_id, handle))
        player = self.cursor.fetchone()
        
        correct_increment = 1 if is_correct else 0
        
        if player:
            # Update existing player
            query = """
            UPDATE tournament_players 
            SET POINTS = POINTS + ?, 
                CORRECT_ANSWERS = CORRECT_ANSWERS + ?,
                TOTAL_ANSWERS = TOTAL_ANSWERS + 1
            WHERE TOURNAMENT_ID=? AND HANDLE=?
            """
            self.cursor.execute(query, (points, correct_increment, tournament_id, handle))
        else:
            # Insert new player
            query = """
            INSERT INTO tournament_players (TOURNAMENT_ID, HANDLE, POINTS, CORRECT_ANSWERS, TOTAL_ANSWERS)
                VALUES (?, ?, ?, ?, 1)
            """
            self.cursor.execute(query, (tournament_id, handle, points, correct_increment))
            
        self.con.commit()
    
    def get_tournament_leaderboard(self, tournament_id: int, limit: int = 10):
        """Get top players for a tournament"""
        query = ('SELECT rowid, TOURNAMENT_ID, HANDLE, POINTS, CORRECT_ANSWERS, '
                 'TOTAL_ANSWERS FROM tournament_players WHERE TOURNAMENT_ID=? '
                 'ORDER BY POINTS DESC LIMIT ?')
        self.cursor.execute(query, (tournament_id, limit))
        data = self.cursor.fetchall()
        return [TournamentPlayerModel(*row) for row in data] if data else []
