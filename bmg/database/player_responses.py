from dataclasses import dataclass
from datetime import datetime
from sqlite3 import Connection, Cursor
from typing import Union, List


@dataclass
class PlayerResponseModel:
    rowid: int
    round_id: int
    handle: str
    response_text: str
    is_correct: bool
    score: int
    response_time: str
    position: int  # Order of response (1st, 2nd, 3rd)


class PlayerResponses:
    def __init__(self, con: Connection, cursor: Cursor):
        self.con = con
        self.cursor = cursor

        self._create_table()

    def _create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS player_responses (
            ROUND_ID        INTEGER,
            HANDLE          TEXT,
            RESPONSE_TEXT   TEXT,
            IS_CORRECT      INTEGER,
            SCORE           INTEGER,
            RESPONSE_TIME   TEXT,
            POSITION        INTEGER,
            
            FOREIGN KEY (ROUND_ID) REFERENCES rounds (rowid)
        )
        """

        self.cursor.execute(query)

    def create(self, round_id: int, handle: str, response_text: str, 
               is_correct: bool, score: int, position: int):
        now = datetime.now().isoformat()

        query = """
        INSERT INTO player_responses (ROUND_ID, HANDLE, RESPONSE_TEXT, IS_CORRECT, 
                                     SCORE, RESPONSE_TIME, POSITION)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        self.cursor.execute(
                query,
                (round_id, handle, response_text, 1 if is_correct else 0, 
                 score, now, position)
        )
        self.con.commit()
        return self.cursor.lastrowid

    def get_responses_by_round(self, round_id: int):
        query = ('SELECT rowid, ROUND_ID, HANDLE, RESPONSE_TEXT, IS_CORRECT, SCORE, '
                 'RESPONSE_TIME, POSITION FROM player_responses WHERE ROUND_ID=? '
                 'ORDER BY POSITION')
        self.cursor.execute(query, (round_id,))
        data = self.cursor.fetchall()
        return [PlayerResponseModel(*row) for row in data] if data else []
    
    def get_correct_responses_by_round(self, round_id: int):
        query = ('SELECT rowid, ROUND_ID, HANDLE, RESPONSE_TEXT, IS_CORRECT, SCORE, '
                 'RESPONSE_TIME, POSITION FROM player_responses WHERE ROUND_ID=? '
                 'AND IS_CORRECT=1 ORDER BY POSITION')
        self.cursor.execute(query, (round_id,))
        data = self.cursor.fetchall()
        return [PlayerResponseModel(*row) for row in data] if data else []
    
    def get_top_players_by_round(self, round_id: int, limit: int = 3):
        # Get top players (first correct responses)
        query = ('SELECT rowid, ROUND_ID, HANDLE, RESPONSE_TEXT, IS_CORRECT, SCORE, '
                 'RESPONSE_TIME, POSITION FROM player_responses WHERE ROUND_ID=? '
                 'AND IS_CORRECT=1 ORDER BY POSITION LIMIT ?')
        self.cursor.execute(query, (round_id, limit))
        data = self.cursor.fetchall()
        return [PlayerResponseModel(*row) for row in data] if data else []
