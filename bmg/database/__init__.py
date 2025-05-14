""" database module

    Main Python script. It will prepare the bmg and schedules for obtaining
    movie data from the API.

    Author: João Iacillo <john@iacillo.dev.br>
"""

from sqlite3 import connect, Connection
from logging import Logger

from .posts import Posts
from .rounds import Rounds
from .player_responses import PlayerResponses
from .tournaments import Tournaments


class Database:
    def __init__(self, path: str, logger: Logger):
        self.logger = logger
        self.con = connect(path)
        self.cursor = self.con.cursor()
        
        self.posts = Posts(self.con, self.cursor)
        self.rounds = Rounds(self.con, self.cursor)
        self.player_responses = PlayerResponses(self.con, self.cursor)
        self.tournaments = Tournaments(self.con, self.cursor)
        
        self.logger.info(f"SQLite3 database connected in \"{path}\"")

    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()
