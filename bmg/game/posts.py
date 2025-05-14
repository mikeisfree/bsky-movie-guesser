from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from random import choice
from typing import List, Optional

from bmg.database.rounds import RoundModel
from bmg.database.types import LatePostUri

# Note: We'll add the import for PlayerResponseModel but make it conditional
# to avoid import errors if the class doesn't exist yet
try:
    from bmg.database.player_responses import PlayerResponseModel
except ImportError:
    # Define a simple placeholder class if it doesn't exist yet
    @dataclass
    class PlayerResponseModel:
        rowid: int
        round_id: int
        handle: str
        response_text: str
        is_correct: bool
        score: int
        response_time: str
        position: int


@dataclass
class GamePostUris:
    round: LatePostUri
    error: LatePostUri
    end: LatePostUri
    results: LatePostUri


class GamePosts:
    """ Creates the post contents for each kind of post. """

    TIPS = (
        'In case you commit typos, don\'t panic, if you write mostly right, '
        'you will still be correct!',
        'We will like your post at the end of the match in case you\'ve '
        'guessed the title right.',
        'You can still comment on others comments. It won\'t affect the final '
        'result.'
    )

    # BlueSky post length limit
    MAX_POST_LENGTH = 280  # Using 280 to be safe (actual limit is 300)

    @staticmethod
    def after_30_min():
        # Changed to 1 minute for testing
        ahead = datetime.now(timezone.utc) + timedelta(minutes=1)
        return f'{ahead.strftime("%d/%m/%Y, %I:%M%p")} UTC'

    @classmethod
    def round(cls, round_number: int, question_type: str = "Movie"):
        """Creates text for a new round, with support for different question types"""
        emoji = "🎥" if question_type == "Movie" else "🎮"
        return (
            f'{emoji} Guess the {question_type}! (Round #{round_number})\n\n'
            f'You have 1 minute ({cls.after_30_min()}) to make ' # Changed to 1 minute
            f'a guess. Good luck! (TEST MODE)\n\n'
            f'(TIP: {choice(cls.TIPS)})'
        )

    @staticmethod
    def insufficient(round_number: int):
        return (
            '😥 Not a single user has commented in the round '
            f'{round_number}.\n\n'
            'Skipping it for now...'
        )

    @staticmethod
    def end(round_number: int):
        return (
            f'⏰ The time is up, everyone! (Round #{round_number})\n\n'
            'You\'ve made your guesses, and we\'re counting all of them. In a '
            'moment we\'ll post the results!'
        )

    @classmethod
    def results(
            cls,
            movie: str,
            round_number: int,
            percent: int,
            attempts: int,
            question_type: str = "movie",
            top_players: Optional[List[PlayerResponseModel]] = None,
            tournament_name: Optional[str] = None
    ):
        """Updated to support different question types, top players, and tournaments
        while enforcing BlueSky character limits"""
        
        # Base result text components
        if percent < 50:
            base_components = [
                f'😿 Round #{round_number}: {percent}% success.\n',
                f'The {question_type} was: {movie}.\n',
                f'Attempts: {attempts}\n'
            ]
        else:
            base_components = [
                f'🏆 Round #{round_number}: {percent}% success! Congrats!\n',
                f'The {question_type} was: {movie}.\n',
                f'Attempts: {attempts}\n'
            ]

        # Optional components
        player_components = []
        if top_players and len(top_players) > 0:
            player_components.append("🥇 Fastest correct answers:\n")
            medals = ["🥇", "🥈", "🥉"]
            for i, player in enumerate(top_players):
                if i < len(medals):
                    medal = medals[i]
                    player_components.append(f"{medal} @{player.handle}\n")

        # Tournament component
        tournament_component = []
        if tournament_name:
            tournament_component = [f"🏆 Tournament: {tournament_name}\n"]

        # Next round info is always included
        next_round_component = [f'Next round in 1 min ({cls.after_30_min()})']
        
        # Combine all components, ensuring we don't exceed character limit
        all_components = base_components + player_components + tournament_component + next_round_component
        
        # Start with base components and add others until we hit the limit
        result_text = ""
        for component in all_components:
            if len(result_text) + len(component) <= cls.MAX_POST_LENGTH:
                result_text += component
            else:
                # If adding next component would exceed limit, stop
                break
        
        return result_text

    @staticmethod
    def error(last_round: RoundModel):
        return (
            f'⚠️ It looks like there was a problem and we had to remove the '
            f'last round of number #{last_round.num}. The movie was "'
            f'{last_round.movie}".\n\nWe\'re very sorry. A new round is '
            f'coming '
            f'right up!'
        )

    @staticmethod
    def critical():
        return (
            '😵 Oops! It looks like we had run into an internal problem. '
            'We\'ll be investigating the issue and the game will resume ASAP'
        )
