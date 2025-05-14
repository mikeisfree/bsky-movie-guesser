from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
import json


class Tournament(BaseModel):
    id: Optional[int] = None
    name: str
    start_date: datetime
    duration_days: int
    questions_per_day: int
    source_distribution: Dict[str, float]
    bonus_first: int
    bonus_second: int
    bonus_third: int
    
    def to_db_dict(self):
        return {
            "name": self.name,
            "start_date": self.start_date.isoformat(),
            "duration_days": self.duration_days,
            "questions_per_day": self.questions_per_day,
            "source_distribution": json.dumps(self.source_distribution),
            "bonus_first": self.bonus_first,
            "bonus_second": self.bonus_second,
            "bonus_third": self.bonus_third
        }
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row["id"],
            name=row["name"],
            start_date=datetime.fromisoformat(row["start_date"]),
            duration_days=row["duration_days"],
            questions_per_day=row["questions_per_day"],
            source_distribution=json.loads(row["source_distribution"]),
            bonus_first=row["bonus_first"],
            bonus_second=row["bonus_second"],
            bonus_third=row["bonus_third"]
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
    total_correct: int = 0
    total_attempts: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return round(self.total_correct / self.total_attempts * 100, 1)


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
