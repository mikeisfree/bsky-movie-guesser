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
        
        # For movie questions, store in the movie property for backwards compatibility
        if self.current_source.get_source_name() == "Movie Trivia":
            self.movie = Movie(
                id=self.current_question.source_info.get("tmdb_id", 0),
                title=self.current_question.answer,
                release_date=self.current_question.source_info.get("release_date", ""),
                cleaned_title=Match.clean(self.current_question.answer)
            )
            
            # Process images if needed
            processed_media = []
            for media_item in self.current_question.media:
                if self.current_source.requires_image_processing:
                    processed_media.append(self.imgp.prepare(media_item.content_bytes))
                else:
                    processed_media.append(media_item.content_bytes)
                    
            self.movie.images = processed_media

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

        for reply in thread.replies:
            score = self.get_reply_score(reply.post.record.text)

            if score >= self.threshold:
                self.correct_attempts += 1
                self.bsky.client.like(reply.post.uri, reply.post.cid)

            self.attempts += 1

        end = datetime.now()

        self.logger.info(f'Thread matching ended. Timing result: {end - start}')

        self.percent = round(self.correct_attempts / self.attempts * 100)

        self.logger.info(
                f'Round #{self.round_number} results: '
                f'{self.correct_attempts}/{self.attempts} = {self.percent}%'
        )

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
            
        # Customize post text based on question source
        post_text = GamePosts.round(self.round_number)
        if self.current_source:
            post_text = f"🎮 BlueTrivia: {self.current_source.get_source_name()} 🎮\n\n"
            post_text += self.current_question.question_text
            post_text += f"\n\nYou have 30 minutes to make a guess. Good luck!"

        self.posts.round = self.bsky.post_images(
                post_text,
                self.movie.images
        ).uri

        self.logger.info("Round sent to Bsky")

        db_posts_rowid: int = self.db.posts.create(self.posts.round)
        db_round_rowid: int = self.db.rounds.create(
                self.round_number,
                self.state,
                self.movie.title,
                db_posts_rowid
        )

        self.logger.info("Round created on database")

        self.wait(30)

        self.logger.info(f"Round wait time over")

        self.state = GameState.CALCULATION

        self.posts.end = self.bsky.post(GamePosts.end(self.round_number)).uri

        if self.calculate_correctness_percentage() is False:
            self.delete_end_post()
            self.posts.error = self.bsky.post(
                    GamePosts.insufficient(self.round_number)
            )
            self.logger.info('Not enough users. Retrying in 15 minutes...')
            self.wait(15)
            return

        self.db.posts.update_end_uri(db_posts_rowid, self.posts.end)
        self.db.rounds.update_state(db_round_rowid, self.state)
        self.db.rounds.update_percent(db_round_rowid, self.percent)
        self.db.rounds.update_attempts(db_round_rowid, self.attempts)
        self.db.commit()

        self.state = GameState.RESULTS

        self.delete_end_post()
        self.db.posts.update_end_uri(db_posts_rowid, None)

        self.posts.results = self.bsky.post(
                GamePosts.results(
                        self.movie.title,
                        self.round_number,
                        self.percent,
                        self.attempts
                )
        ).uri

        now = datetime.now().isoformat()
        self.db.posts.update_results_uri(db_posts_rowid, self.posts.results)
        self.db.rounds.update_state(db_round_rowid, self.state)
        self.db.rounds.update_ended_in(db_round_rowid, now)
        self.db.commit()

        self.wait(30)

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
                        f'Untreated exception. Repeating in 15 minutes.',
                        exc_info=err,
                        stack_info=True
                )
                self.bsky.post(GamePosts.critical())

                if self.posts.round:
                    self.bsky.delete_post(self.posts.round)

                self.wait(15)
