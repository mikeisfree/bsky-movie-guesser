import random
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from bmg.bsky import BskyClient
from bmg.database import Database
from bmg.image import ImagePreparer
from bmg.question_source import QuestionSource, Question
from bmg.tmdb import TmdbClient


@dataclass
class GameConfig:
    bsky: BskyClient
    tmdb: TmdbClient
    imgp: ImagePreparer
    db: Database
    question_sources: List[QuestionSource]
    threshold: int = 80
    round_time_seconds: int = 60  # 1 minute (changed from 1800 for testing)
    wait_between_rounds_seconds: int = 60  # 1 minute (changed from 300 for testing)


class GameController:
    """Main controller for the BlueTrivia game"""
    
    def __init__(self, config: GameConfig):
        self.bsky = config.bsky
        self.tmdb = config.tmdb
        self.imgp = config.imgp
        self.db = config.db
        self.question_sources = config.question_sources
        self.threshold = config.threshold
        self.round_time_seconds = config.round_time_seconds
        self.wait_between_rounds_seconds = config.wait_between_rounds_seconds
        
        # Round state
        self.current_question = None
        self.question_post_id = None
        self.round_start_time = 0
        self.correct_attempts = 0
        self.attempts = 0
        self.percent = 0
        self.current_source = None
    
    def start(self):
        """Starts the game loop"""
        while True:
            try:
                # Start a new round
                self.run_round()
                
                # Wait between rounds
                time.sleep(self.wait_between_rounds_seconds)
            except Exception as e:
                print(f"Error in game loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def run_round(self):
        """Runs a single game round"""
        # 1. Select a random question source
        self.current_source = random.choice(self.question_sources)
        print(f"Selected source: {self.current_source.get_source_name()}")
        
        # 2. Get a random question
        self.current_question = self.current_source.get_random_question()
        print(f"Selected question with answer: {self.current_question.answer}")
        
        # 3. Process media if needed
        processed_media = self._process_media()
        
        # 4. Post the question
        self.question_post_id = self._post_question(processed_media)
        self.round_start_time = time.time()
        
        # Store round info in database
        round_id = self.db.store_round(
            source_name=self.current_source.get_source_name(),
            question_text=self.current_question.question_text,
            answer=self.current_question.answer,
            post_id=self.question_post_id
        )
        
        # 5. Wait for round to complete
        time.sleep(self.round_time_seconds)
        
        # 6. Calculate results
        self._calculate_results()
        
        # 7. Post results
        self._post_results()
        
        # 8. Update database with results
        self.db.update_round_results(
            round_id=round_id,
            attempts=self.attempts,
            correct_attempts=self.correct_attempts,
            percentage=self.percent
        )
    
    def _process_media(self) -> List[bytes]:
        """Processes the question's media items"""
        processed_media = []
        
        if not self.current_question.media:
            return processed_media
        
        for media_item in self.current_question.media:
            media_bytes = media_item.content_bytes
            
            # Apply image processing if required by the source
            if self.current_source.requires_image_processing:
                media_bytes = self.imgp.prepare(media_bytes)
            
            processed_media.append(media_bytes)
        
        return processed_media
    
    def _post_question(self, media_bytes: List[bytes]) -> str:
        """Posts the question to BlueSky and returns the post ID"""
        # Build post text
        source_name = self.current_source.get_source_name()
        post_text = f"🎮 BlueTrivia: {source_name} 🎮\n\n"
        post_text += self.current_question.question_text
        post_text += f"\n\nYou have {self.round_time_seconds // 60} minute to reply with your answer! (TEST MODE)"
        
        # Post to BlueSky with media attachments
        post_id = self.bsky.post_with_images(
            text=post_text,
            images=media_bytes
        )
        
        return post_id
    
    def _calculate_results(self):
        """Calculates the results of the round"""
        # Get all replies to the question post
        thread = self.bsky.get_post_thread(self.question_post_id)
        
        self.attempts = 0
        self.correct_attempts = 0
        
        if thread and thread.replies:
            for reply in thread.replies:
                user_answer = reply.post.record.text
                self.attempts += 1
                
                # Evaluate answer
                score = self.current_source.evaluate_answer(
                    user_answer=user_answer,
                    correct_answer=self.current_question.answer,
                    threshold=self.threshold
                )
                
                if score >= self.threshold:
                    self.correct_attempts += 1
                    
                    # Store correct guess in database
                    self.db.store_player_guess(
                        handle=reply.post.author.handle,
                        round_post_id=self.question_post_id,
                        guess=user_answer,
                        is_correct=True,
                        score=score
                    )
                else:
                    # Store incorrect guess
                    self.db.store_player_guess(
                        handle=reply.post.author.handle,
                        round_post_id=self.question_post_id,
                        guess=user_answer,
                        is_correct=False,
                        score=score
                    )
        
        # Calculate percentage
        self.percent = 0
        if self.attempts > 0:
            self.percent = round(self.correct_attempts / self.attempts * 100)
    
    def _post_results(self):
        """Posts the round results to BlueSky"""
        # Build results text
        results_text = f"📊 BlueTrivia Results 📊\n\n"
        results_text += f"The answer was: {self.current_question.answer}\n\n"
        
        if self.attempts > 0:
            results_text += f"Success rate: {self.percent}%\n"
            results_text += f"Correct guesses: {self.correct_attempts}/{self.attempts}\n\n"
        else:
            results_text += "No one attempted to answer this question!\n\n"
        
        results_text += f"A new round will start in {self.wait_between_rounds_seconds // 60} minute! (TEST MODE) 🎲"
        
        # Post results as reply to question post
        self.bsky.post_as_reply(
            text=results_text,
            reply_to=self.question_post_id
        )
