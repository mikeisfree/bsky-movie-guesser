from collections import namedtuple
from typing import List, Optional

from bmg.question_source import QuestionSource

# Extend the existing GameConfig to support question sources
GameConfig = namedtuple(
        'GameConfig',
        ('bsky', 'tmdb', 'imgp', 'db', 'logger', 'threshold', 'skip_on_input', 
         'question_sources')
)

# Add default empty list for question_sources to maintain backward compatibility
GameConfig.__new__.__defaults__ = (None,)
