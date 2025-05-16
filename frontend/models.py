from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
import json


class Tournament(BaseModel):
    id: Optional[int] = None
    name: str
    start_time: int
    end_time: int
    duration_days: int = 7
    questions_per_day: int = 4
    source_distribution: Dict[str, float] = {"movie": 0.5, "trivia": 0.5}
    bonus_first: int = 10
    bonus_second: int = 5
    bonus_third: int = 3
    is_active: bool = True
    total_rounds: int = 0
    
    def to_db_dict(self):
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_days": self.duration_days,
            "questions_per_day": self.questions_per_day,
            "source_distribution": json.dumps(self.source_distribution),
            "bonus_first": self.bonus_first,
            "bonus_second": self.bonus_second,
            "bonus_third": self.bonus_third,
            "is_active": self.is_active,
            "total_rounds": self.total_rounds
        }
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row["id"],
            name=row["name"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            duration_days=row["duration_days"],
            questions_per_day=row["questions_per_day"],
            source_distribution=json.loads(row["source_distribution"]),
            bonus_first=row["bonus_first"],
            bonus_second=row["bonus_second"],
            bonus_third=row["bonus_third"],
            is_active=bool(row["is_active"]),
            total_rounds=row["total_rounds"]
        )


class TriviaQuestion(BaseModel):
    id: Optional[int] = None
    category: str
    question: str
    answer: str
    difficulty: str = "medium"
    image_url: Optional[str] = None
    
    def to_db_dict(self):
        return {
            "category": self.category,
            "question": self.question,
            "answer": self.answer,
            "difficulty": self.difficulty,
            "image_url": self.image_url
        }


class Player(BaseModel):
    id: Optional[int] = None
    handle: str
    display_name: Optional[str] = None
    total_points: int = 0
    correct_guesses: int = 0
    total_guesses: int = 0
    first_seen: Optional[int] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_guesses == 0:
            return 0.0
        return round(self.correct_guesses / self.total_guesses * 100, 1)


class RoundResult(BaseModel):
    id: Optional[int] = None
    round_id: int
    player_id: int
    correct: bool
    position: Optional[int] = None
    points_earned: int


class TournamentResult(BaseModel):
    tournament_id: int
    player_id: int
    total_points: int = 0
    final_position: Optional[int] = None
    bonus_points: int = 0
