import abc
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class QuestionMedia:
    """Media content associated with a question (image, audio, etc.)"""
    content_bytes: bytes
    mime_type: str
    alt_text: str = ""


@dataclass
class Question:
    """Represents a trivia question with its answer and associated media"""
    question_text: str
    answer: str
    media: List[QuestionMedia] = None
    category: str = ""
    difficulty: str = "medium"
    source_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.media is None:
            self.media = []


class QuestionSource(abc.ABC):
    """Abstract base class for different question sources"""
    
    @abc.abstractmethod
    def get_random_question(self) -> Question:
        """Returns a random question from this source"""
        pass
    
    @abc.abstractmethod
    def get_source_name(self) -> str:
        """Returns the name of this question source"""
        pass
    
    @abc.abstractmethod
    def evaluate_answer(self, user_answer: str, correct_answer: str, threshold: int = 80) -> int:
        """
        Evaluates a user's answer against the correct answer
        Returns a score between 0 and 100
        """
        pass
    
    @property
    def requires_image_processing(self) -> bool:
        """Whether this source requires image processing (default: False)"""
        return False
    
    @property
    def max_media_items(self) -> int:
        """Maximum number of media items allowed for this source (default: 0)"""
        return 0
