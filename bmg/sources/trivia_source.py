import random
import sqlite3
from typing import List, Optional

from fuzzywuzzy import fuzz

from bmg.question_source import QuestionSource, Question, QuestionMedia
from bmg.matcher import Match


class TriviaQuestionSource(QuestionSource):
    """Question source for custom trivia questions stored in the database"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_table_exists()
    
    def get_random_question(self) -> Question:
        """Returns a random trivia question from the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get random trivia question
            cursor.execute("""
                SELECT id, question, answer, category, difficulty
                FROM trivia_questions
                ORDER BY RANDOM()
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if not row:
                raise ValueError("No trivia questions found in database")
            
            # Get any associated media
            media_items = self._get_media_for_question(conn, row['id'])
            
            # Create and return the question
            return Question(
                question_text=row['question'],
                answer=row['answer'],
                media=media_items,
                category=row['category'],
                difficulty=row['difficulty']
            )
    
    def get_source_name(self) -> str:
        return "General Trivia"
    
    def evaluate_answer(self, user_answer: str, correct_answer: str, threshold: int = 80) -> int:
        """Evaluates trivia answer using the existing matcher"""
        # Use existing Match utility
        user_clean = Match.clean(user_answer)
        correct_clean = Match.clean(correct_answer)
        
        # Calculate similarity score
        return Match.str(correct_clean, user_clean)
    
    @property
    def requires_image_processing(self) -> bool:
        return False  # We don't need to censor trivia images
    
    @property
    def max_media_items(self) -> int:
        return 1  # Trivia questions can have 0 or 1 image
    
    def add_question(self, question: str, answer: str, category: str = "General", 
                    difficulty: str = "medium", image_bytes: Optional[bytes] = None) -> int:
        """Adds a new trivia question to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert question
            cursor.execute("""
                INSERT INTO trivia_questions (question, answer, category, difficulty)
                VALUES (?, ?, ?, ?)
            """, (question, answer, category, difficulty))
            
            question_id = cursor.lastrowid
            
            # Add image if provided
            if image_bytes:
                cursor.execute("""
                    INSERT INTO trivia_media (question_id, content_bytes, mime_type)
                    VALUES (?, ?, ?)
                """, (question_id, image_bytes, "image/jpeg"))
            
            conn.commit()
            return question_id
    
    def _ensure_table_exists(self) -> None:
        """Ensures that the required database tables exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create questions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trivia_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT DEFAULT 'General',
                    difficulty TEXT DEFAULT 'medium',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create media table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trivia_media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    content_bytes BLOB NOT NULL,
                    mime_type TEXT NOT NULL,
                    alt_text TEXT DEFAULT '',
                    FOREIGN KEY (question_id) REFERENCES trivia_questions (id)
                        ON DELETE CASCADE
                )
            """)
            
            conn.commit()
    
    def _get_media_for_question(self, conn, question_id: int) -> List[QuestionMedia]:
        """Get associated media for a question"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content_bytes, mime_type, alt_text
            FROM trivia_media
            WHERE question_id = ?
        """, (question_id,))
        
        media_items = []
        for row in cursor.fetchall():
            media_items.append(QuestionMedia(
                content_bytes=row['content_bytes'],
                mime_type=row['mime_type'],
                alt_text=row['alt_text'] or ""
            ))
        
        return media_items
