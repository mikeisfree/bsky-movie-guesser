""" main.py

    Main Python script. It will prepare the bmg and schedules for obtaining
    movie data from the API.
    
    Author: João Iacillo <john@iacillo.dev.br>
"""

import os
import sys
import logging
import dotenv as dotenv
import time  # Import time explicitly for timestamp generation

from bmg.bsky import BskyClient
from bmg.database import Database
from bmg.database_init import initialize_trivia_database
from bmg.game import Game, GameConfig
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
    # Use the existing logs directory structure for consistent logging
    os.makedirs('.logs', exist_ok=True)
    log_filename = f".logs/{int(time.time())}.log"
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def main():
    """Entry point for BlueTrivia"""
    print("Starting BlueTrivia (test mode with 1-minute rounds)...")
    
    # Load environment variables from .env file
    dotenv.load_dotenv()
    print("Environment variables loaded from .env file")
    
    # Set up logger before initializing components
    logger = setup_logger()
    
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
        print("Please set TMDB_API_KEY, BSKY_USERNAME, and BSKY_PASSWORD in the .env file.")
        sys.exit(1)
    
    # Initialize the database with sample trivia questions
    print("Initializing trivia database...")
    initialize_trivia_database(db_path)
    print("Database initialized with sample questions")
    
    # Initialize components
    # Pass the logger to components that require it
    bsky_client = BskyClient(bsky_username, bsky_password, logger)
    tmdb_client = TmdbClient(tmdb_api_key)
    image_preparer = ImagePreparer(tmdb_image_quality, logger)  # Added logger parameter
    database = Database(db_path, logger)  # Added logger parameter
    
    # Initialize question sources
    movie_source = MovieQuestionSource(tmdb_client)
    trivia_source = TriviaQuestionSource(db_path)
    
    print("Component initialization complete")
    
    # Configure game controller with 1-minute rounds for testing
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
    
    print("Starting game with 1-minute rounds...")
    
    # Start game loop
    game = Game(config)
    game.start()


if __name__ == "__main__":
    main()
