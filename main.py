""" main.py

    Main Python script. It will prepare the bmg and schedules for obtaining
    movie data from the API.
    
    Author: João Iacillo <john@iacillo.dev.br>
"""

import os
import sys
import logging

from bmg.bsky import BskyClient
from bmg.database import Database
from bmg.game.config import GameConfig
from bmg.game.game import Game
from bmg.image import ImagePreparer
from bmg.sources.movie_source import MovieQuestionSource
from bmg.sources.trivia_source import TriviaQuestionSource
from bmg.tmdb import TmdbClient


def setup_logger():
    """Set up and return a logger"""
    logger = logging.getLogger("bluetrivia")
    logger.setLevel(logging.INFO)
    
    # Console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # File handler
    file_handler = logging.FileHandler("bluetrivia.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def add_sample_trivia_questions(trivia_source):
    """Adds sample trivia questions if none exist"""
    try:
        # Try to get a random question - if this succeeds, we have questions
        trivia_source.get_random_question()
    except ValueError:
        # No questions found, add sample questions
        print("Adding sample trivia questions...")
        
        sample_questions = [
            ("What is the capital of France?", "Paris", "Geography"),
            ("Who wrote 'Romeo and Juliet'?", "William Shakespeare", "Literature"),
            ("What is the chemical symbol for gold?", "Au", "Science"),
            ("What year did the Titanic sink?", "1912", "History"),
            ("How many sides does a hexagon have?", "6", "Mathematics")
        ]
        
        for question, answer, category in sample_questions:
            trivia_source.add_question(question, answer, category)


def main():
    """Entry point for BlueTrivia"""
    print("Starting BlueTrivia...")
    
    # Load configuration from environment variables
    tmdb_api_key = os.environ.get("TMDB_API_KEY")
    tmdb_image_quality = int(os.environ.get("TMDB_IMAGE_QUALITY", "75"))
    bot_threshold = int(os.environ.get("BOT_THRESHOLD", "80"))
    bsky_username = os.environ.get("BSKY_USERNAME")
    bsky_password = os.environ.get("BSKY_PASSWORD")
    db_path = os.environ.get("DB_PATH", "bluetrivia.db")
    skip_on_input = os.environ.get("SKIP_ON_INPUT", "False").lower() in ("true", "1", "yes")
    
    # Validate required configuration
    if not all([tmdb_api_key, bsky_username, bsky_password]):
        print("Missing required environment variables.")
        print("Please set TMDB_API_KEY, BSKY_USERNAME, and BSKY_PASSWORD.")
        sys.exit(1)
    
    # Set up logger
    logger = setup_logger()
    
    # Initialize components
    bsky_client = BskyClient(bsky_username, bsky_password)
    tmdb_client = TmdbClient(tmdb_api_key)
    image_preparer = ImagePreparer(tmdb_image_quality)
    database = Database(db_path)
    
    # Initialize question sources
    movie_source = MovieQuestionSource(tmdb_client)
    trivia_source = TriviaQuestionSource(db_path)
    
    # Add some initial trivia questions if the database is new
    add_sample_trivia_questions(trivia_source)
    
    # Configure game controller
    config = GameConfig(
        bsky=bsky_client,
        tmdb=tmdb_client,
        imgp=image_preparer,
        db=database,
        logger=logger,
        threshold=bot_threshold,
        skip_on_input=skip_on_input,
        question_sources=[movie_source, trivia_source]
    )
    
    # Start game loop
    game = Game(config)
    game.start()


if __name__ == "__main__":
    main()
