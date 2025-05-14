from dataclasses import dataclass
from datetime import datetime
from sqlite3 import Connection, Cursor
from typing import Union


@dataclass
class RoundModel:
    rowid: int
    num: int
    state: int
    movie: str  # Keep as "movie" for backward compatibility
    posts: int
    percent: Union[int, None]
    attempts: Union[int, None]
    created_in: str
    ended_in: Union[str, None]


class Rounds:
    def __init__(self, con: Connection, cursor: Cursor):
        self.con = con
        self.cursor = cursor

        self._create_table()
        self._check_and_migrate_schema()

    def _create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS rounds (
            NUM         INTEGER PRIMARY KEY,
            STATE       INTEGER,
            MOVIE       TEXT,
            POSTS       INTEGER,
            PERCENT     INTEGER,
            ATTEMPTS    INTEGER,
            CREATED_IN  TEXT,
            ENDED_IN    TEXT,
            
            FOREIGN KEY (POSTS) REFERENCES posts (rowid)
        )
        """

        self.cursor.execute(query)

    def _check_and_migrate_schema(self):
        """Check if we need to migrate the schema to add new columns"""
        # Get current columns in the rounds table
        self.cursor.execute("PRAGMA table_info(rounds)")
        columns = [column[1] for column in self.cursor.fetchall()]
        
        # Add columns if they don't exist
        if "QUESTION_SOURCE" not in columns:
            self.cursor.execute("ALTER TABLE rounds ADD COLUMN QUESTION_SOURCE TEXT DEFAULT 'Movie Trivia'")
        
        if "QUESTION_TYPE" not in columns:
            self.cursor.execute("ALTER TABLE rounds ADD COLUMN QUESTION_TYPE TEXT DEFAULT 'General'")
            
        if "TOURNAMENT_ID" not in columns:
            self.cursor.execute("ALTER TABLE rounds ADD COLUMN TOURNAMENT_ID INTEGER")
        
        self.con.commit()

    def create(self, num: int, state: int, movie: str, posts_rowid: int,
               question_source: str = "Movie Trivia", question_type: str = "General", 
               tournament_id: Union[int, None] = None):
        now = datetime.now().isoformat()

        # Use MOVIE column name for backward compatibility
        query = """
        INSERT INTO rounds (NUM, POSTS, MOVIE, QUESTION_SOURCE, QUESTION_TYPE, 
                          TOURNAMENT_ID, CREATED_IN, STATE)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.cursor.execute(
                query,
                (num, posts_rowid, movie, question_source, question_type, 
                 tournament_id, now, state)
        )
        self.con.commit()
        return self.cursor.lastrowid

    def get_by_rowid(self, rowid: int):
        query = ('SELECT NUM, STATE, MOVIE, POSTS, PERCENT, ATTEMPTS, '
                 'CREATED_IN, ENDED_IN FROM rounds WHERE rowid=?')
        self.cursor.execute(query, (rowid,))
        data = self.cursor.fetchone()
        return RoundModel(rowid, *data)

    def last_round(self):
        self.cursor.execute(
                'SELECT rowid, NUM, STATE, MOVIE, POSTS, PERCENT, ATTEMPTS, '
                'CREATED_IN, ENDED_IN FROM rounds ORDER BY NUM DESC'
        )
        data = self.cursor.fetchone()
        return RoundModel(*data) if data else None

    def update_state(self, rowid: int, state: int):
        query = 'UPDATE rounds SET STATE=? WHERE rowid=?'
        self.cursor.execute(query, (state, rowid))

    def update_percent(self, rowid: int, percent: int):
        query = 'UPDATE rounds SET PERCENT=? WHERE rowid=?'
        self.cursor.execute(query, (percent, rowid))

    def update_attempts(self, rowid: int, attempts: int):
        query = 'UPDATE rounds SET ATTEMPTS=? WHERE rowid=?'
        self.cursor.execute(query, (attempts, rowid))

    def update_ended_in(self, rowid: int, ended_in: int):
        query = 'UPDATE rounds SET ENDED_IN=? WHERE rowid=?'
        self.cursor.execute(query, (ended_in, rowid))
        
    def update_question_source(self, rowid: int, question_source: str):
        query = 'UPDATE rounds SET QUESTION_SOURCE=? WHERE rowid=?'
        self.cursor.execute(query, (question_source, rowid))
        
    def update_question_type(self, rowid: int, question_type: str):
        query = 'UPDATE rounds SET QUESTION_TYPE=? WHERE rowid=?'
        self.cursor.execute(query, (question_type, rowid))
        
    def update_tournament_id(self, rowid: int, tournament_id: int):
        query = 'UPDATE rounds SET TOURNAMENT_ID=? WHERE rowid=?'
        self.cursor.execute(query, (tournament_id, rowid))

    def delete(self, num: int):
        self.cursor.execute('DELETE from rounds WHERE NUM=?', (num,))
        self.con.commit()
