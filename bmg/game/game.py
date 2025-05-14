from datetime import datetime
from logging import Logger
from time import sleep
from typing import Union, List
import random

from bmg.bsky import BskyClient
from bmg.database import Database
from bmg.database.rounds import RoundModel
from bmg.image import ImagePreparer
from bmg.matcher import Match
from bmg.question_source import QuestionSource, Question
from bmg.tmdb import Movie, TmdbClient, TmdbMovieUtils
from bmg.types import GameState
from .config import GameConfig
from .posts import GamePostUris, GamePosts


class Game:
    """
    Game controller that supports both movie guessing and general trivia.
    """

    def __init__(self, config: GameConfig):
        self.bsky: BskyClient = config.bsky
        self.tmdb: TmdbClient = config.tmdb
        self.imgp: ImagePreparer = config.imgp
        self.db: Database = config.db
        self.logger: Logger = config.logger
        self.skip_on_input = config.skip_on_input
        
        # Support for multiple question sources
        self.question_sources: List[QuestionSource] = config.question_sources or []
        self.current_source = None
        self.current_question = None
        
        self.last_round: Union[RoundModel, None] = self.db.rounds.last_round()

        self.state: int = GameState.STOPPED
        self.round_number = self.last_round.num if self.last_round else 0
        self.threshold: int = config.threshold

        self.movie: Union[Movie, None] = None
        self.posts = GamePostUris(None, None, None, None)

        self.attempts = 0
        self.correct_attempts = 0
        self.percent = -1

    def select_random_movie(self):
        """Legacy method for backwards compatibility"""
        movie: Union[Movie, None] = None
        backdrops: Union[list[bytes], None] = None

        # Movies that have under 4 backdrops must not be selected.
        while backdrops is None:
            movie = self.tmdb.get_random_movie()
            backdrops = TmdbMovieUtils.get_n_movie_backdrops(
                    self.tmdb,
                    movie.id
            )

        movie.images = [self.imgp.prepare(i) for i in backdrops]

        self.logger.info(f'Selected movie: {movie.title}')
        self.movie = movie
        
    def select_random_question(self):
        """Select a random question from available sources"""
        if not self.question_sources:
            # If no question sources are configured, fall back to movie selection
            self.logger.info("No question sources configured, falling back to movie selection")
            self.select_random_movie()
            return
            
        # Select a random question source
        self.current_source = random.choice(self.question_sources)
        self.logger.info(f"Selected source: {self.current_source.get_source_name()}")
        
        # Get a random question from this source
        self.current_question = self.current_source.get_random_question()
        self.logger.info(f"Selected question with answer: {self.current_question.answer}")
        
        # Process any media items for the question
        media_bytes = []
        if self.current_question.media:
            for media_item in self.current_question.media:
                if self.current_source.requires_image_processing:
                    media_bytes.append(self.imgp.prepare(media_item.content_bytes))
                else:
                    media_bytes.append(media_item.content_bytes)
        
        # For movie questions, store in the movie property for backwards compatibility
        if self.current_source.get_source_name() == "Movie Trivia":
            # Create Movie object with all required parameters including images
            self.movie = Movie(
                id=self.current_question.source_info.get("tmdb_id", 0),
                title=self.current_question.answer,
                cleaned_title=Match.clean(self.current_question.answer),
                images=media_bytes  # Add images parameter
            )
        else:
            # For non-movie questions, we still need a movie object for compatibility
            self.movie = Movie(
                id=0,
                title=self.current_question.answer,
                cleaned_title=Match.clean(self.current_question.answer),
                images=media_bytes  # Add images parameter
            )

    def get_reply_score(self, reply: str):
        """Get score for a reply using appropriate source"""
        if self.current_source:
            # Use the question source's evaluation method
            return self.current_source.evaluate_answer(
                reply, 
                self.current_question.answer, 
                self.threshold
            )
        else:
            # Legacy method
            reply = Match.clean(reply)
            score = Match.str(self.movie.cleaned_title, reply)
            return score

    def calculate_correctness_percentage(self):
        self.attempts = 0
        self.correct_attempts = 0

        thread_res = self.bsky.get_thread(self.posts.round)
        thread = thread_res.thread

        if not len(thread.replies):
            self.logger.info("No players participated in this round. Skipping")
            return False

        self.logger.info(f'Matching {len(thread.replies)} comments')
        start = datetime.now()

        # Get the current round ID from the database to associate responses
        current_round = self.db.rounds.last_round()
        
        # Keep track of position for responses
        position = 1
        
        # Get the active tournament, if any
        try:
            active_tournament = self.db.tournaments.get_active_tournament()
            tournament_id = active_tournament.rowid if active_tournament else None
        except:
            self.logger.info("No active tournament or tournaments table not yet created")
            tournament_id = None

        for reply in thread.replies:
            score = self.get_reply_score(reply.post.record.text)
            is_correct = score >= self.threshold
            
            if is_correct:
                self.correct_attempts += 1
                self.bsky.client.like(reply.post.uri, reply.post.cid)
            
            # Store the player response in the database
            try:
                self.db.player_responses.create(
                    round_id=current_round.rowid,
                    handle=reply.post.author.handle,
                    response_text=reply.post.record.text,
                    is_correct=is_correct,
                    score=score,
                    position=position
                )
                
                # If there's an active tournament, update player points
                if tournament_id:
                    # First correct answer gets 3 points, second gets 2, third gets 1, others get 0
                    points = 0
                    if is_correct:
                        if position == 1:
                            points = 3
                        elif position == 2:
                            points = 2
                        elif position == 3:
                            points = 1
                    
                    self.db.tournaments.add_player_points(
                        tournament_id=tournament_id,
                        handle=reply.post.author.handle,
                        points=points,
                        is_correct=is_correct
                    )
            except Exception as e:
                self.logger.error(f"Failed to store player response: {e}")

            self.attempts += 1
            position += 1  # Increment the position counter

        end = datetime.now()

        self.logger.info(f'Thread matching ended. Timing result: {end - start}')

        self.percent = round(self.correct_attempts / self.attempts * 100)

        self.logger.info(
                f'Round #{self.round_number} results: '
                f'{self.correct_attempts}/{self.attempts} = {self.percent}%'
        )
        
        # If this round is part of a tournament, update the tournament progress
        if tournament_id:
            try:
                self.db.tournaments.update_tournament_progress(tournament_id)
            except Exception as e:
                self.logger.error(f"Failed to update tournament progress: {e}")

        return True

    def delete_end_post(self):
        self.bsky.delete_post(self.posts.end)
        self.posts.end = None

    def wait(self, minutes: int):
        if self.skip_on_input:
            print(f"Press ENTER to skip {minutes} minutes:", end=' ')
            input()
            print('Skipped.')
            return
        sleep(60 * minutes)

    def new_round(self):
        self.state = GameState.INITIAL
        self.round_number += 1
        self.logger.info(f'===== Round #{self.round_number} =====')

        # Use new question source selection if available, otherwise use legacy
        if hasattr(self, 'question_sources') and self.question_sources:
            self.select_random_question()
        else:
            self.select_random_movie()
            
        # Get the active tournament, if any
        tournament_name = None
        tournament_id = None
        try:
            active_tournament = self.db.tournaments.get_active_tournament()
            if active_tournament:
                tournament_id = active_tournament.rowid
                tournament_name = active_tournament.name
        except:
            self.logger.info("No active tournament or tournaments table not yet created")
            
        question_type = "Tournament" if tournament_id else "General"
            
        # Customize post text based on question source
        post_text = GamePosts.round(self.round_number)
        if self.current_source:
            question_source = self.current_source.get_source_name()
            is_movie = question_source == "Movie Trivia"
            question_type_text = "Movie" if is_movie else "Trivia"
            
            post_text = GamePosts.round(self.round_number, question_type_text)
            if not is_movie:
                post_text = f"🎮 BlueTrivia: {question_source} 🎮\n\n"
                post_text += self.current_question.question_text
                post_text += f"\n\nYou have 1 minute to make a guess. Good luck! (TEST MODE)"
                
            # Add tournament info if applicable
            if tournament_name:
                post_text += f"\n\n🏆 This is a tournament round! 🏆\nTournament: {tournament_name}"

        self.posts.round = self.bsky.post_images(
                post_text,
                self.movie.images if hasattr(self.movie, 'images') and self.movie.images else []
        ).uri

        self.logger.info("Round sent to Bsky")

        db_posts_rowid: int = self.db.posts.create(self.posts.round)
        
        # Store more metadata about the question
        question_source = self.current_source.get_source_name() if self.current_source else "Movie Trivia"
        
        try:
            db_round_rowid: int = self.db.rounds.create(
                    self.round_number,
                    self.state,
                    self.movie.title,
                    db_posts_rowid,
                    question_source,
                    question_type,
                    tournament_id
            )
        except Exception as e:
            # Fallback to the basic create method if the extended one fails
            self.logger.error(f"Failed to create round with extended fields: {e}")
            db_round_rowid: int = self.db.rounds.create(
                    self.round_number,
                    self.state,
                    self.movie.title,
                    db_posts_rowid
            )

        self.logger.info("Round created on database")

        # Wait only 1 minute for testing
        self.wait(1)

        self.logger.info(f"Round wait time over")

        self.state = GameState.CALCULATION

        self.posts.end = self.bsky.post(GamePosts.end(self.round_number)).uri

        if self.calculate_correctness_percentage() is False:
            self.delete_end_post()
            self.posts.error = self.bsky.post(
                    GamePosts.insufficient(self.round_number)
            )
            self.logger.info('Not enough users. Retrying in 1 minute...')
            self.wait(1)  # Changed to 1 minute for testing
            return

        self.db.posts.update_end_uri(db_posts_rowid, self.posts.end)
        self.db.rounds.update_state(db_round_rowid, self.state)
        self.db.rounds.update_percent(db_round_rowid, self.percent)
        self.db.rounds.update_attempts(db_round_rowid, self.attempts)
        self.db.commit()

        self.state = GameState.RESULTS

        self.delete_end_post()
        self.db.posts.update_end_uri(db_posts_rowid, None)

        # Get top players for this round
        top_players = []
        try:
            top_players = self.db.player_responses.get_top_players_by_round(db_round_rowid, 3)
        except Exception as e:
            self.logger.error(f"Failed to get top players: {e}")

        # Customize result text based on question source
        question_type = "movie"
        if self.current_source and self.current_source.get_source_name() != "Movie Trivia":
            question_type = "answer"
            
        self.posts.results = self.bsky.post(
                GamePosts.results(
                        self.movie.title,
                        self.round_number,
                        self.percent,
                        self.attempts,
                        question_type,
                        top_players,
                        tournament_name
                )
        ).uri

        now = datetime.now().isoformat()
        self.db.posts.update_results_uri(db_posts_rowid, self.posts.results)
        self.db.rounds.update_state(db_round_rowid, self.state)
        self.db.rounds.update_ended_in(db_round_rowid, now)
        self.db.commit()

        # Wait only 1 minute for testing
        self.wait(1)

    def check_for_last_rounds(self):
        """
        Checks if there are any unfinished rounds. If so, deletes the posts
        and warns the users.
        """

        last_round = self.db.rounds.last_round()
        if last_round is None:
            return

        posts = self.db.posts.get_by_rowid(last_round.posts)
        self.bsky.delete_post(posts.round_uri)

        self.db.rounds.delete(last_round.num)

        self.bsky.post(GamePosts.error(last_round))

        self.logger.warning(
                f'Round #{last_round.num} wasn\'t in RESULTS '
                f'stage. Post removed from database and Bsky. '
        )

    def start(self):
        """ Starts the first round """

        self.check_for_last_rounds()

        while True:
            try:
                self.new_round()
            except Exception as err:
                self.logger.critical(
                        f'Untreated exception. Repeating in 1 minute.',
                        exc_info=err,
                        stack_info=True
                )
                self.bsky.post(GamePosts.critical())

                if self.posts.round:
                    self.bsky.delete_post(self.posts.round)

                self.wait(1)  # Changed to 1 minute for testing
