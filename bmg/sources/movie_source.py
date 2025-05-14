from typing import List

from bmg.matcher import Match
from bmg.question_source import QuestionSource, Question, QuestionMedia
from bmg.tmdb import TmdbClient, TmdbMovieUtils


class MovieQuestionSource(QuestionSource):
    """Question source that uses TMDB movies as trivia questions"""
    
    def __init__(self, tmdb_client: TmdbClient):
        self.tmdb = tmdb_client
        
    def get_random_question(self) -> Question:
        """Returns a random movie-based question"""
        # Get a random movie with sufficient backdrop images
        movie = self.tmdb.get_random_movie()
        backdrops = TmdbMovieUtils.get_n_movie_backdrops(
            self.tmdb,
            movie.id
        )
        
        media_items = []
        
        # Create media items from backdrop images
        for backdrop in backdrops:
            media_items.append(QuestionMedia(
                content_bytes=backdrop,
                mime_type="image/jpeg",
                alt_text=f"Censored image from movie"
            ))
        
        # Create and return the question with safe source_info
        # Remove the release_date that's causing issues
        return Question(
            question_text="Can you guess the movie title from these images?",
            answer=movie.title,
            media=media_items,
            category="Movies",
            source_info={"tmdb_id": movie.id}  # Removed release_date
        )
    
    def get_source_name(self) -> str:
        return "Movie Trivia"
    
    def evaluate_answer(self, user_answer: str, correct_answer: str, threshold: int = 80) -> int:
        """Evaluates movie title guesses using fuzzy matching"""
        # Use Match utility for consistency
        user_clean = Match.clean(user_answer)
        correct_clean = Match.clean(correct_answer)
        
        # Calculate similarity score
        return Match.str(correct_clean, user_clean)
    
    @property
    def requires_image_processing(self) -> bool:
        return True
    
    @property
    def max_media_items(self) -> int:
        return 4
