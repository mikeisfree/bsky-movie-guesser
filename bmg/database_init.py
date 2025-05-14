import sqlite3
from typing import List, Tuple, Optional


def initialize_trivia_database(db_path: str):
    """Initialize the trivia database with tables and sample questions"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
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
    
    # Check if we already have questions
    cursor.execute("SELECT COUNT(*) FROM trivia_questions")
    question_count = cursor.fetchone()[0]
    
    # Add sample questions if none exist
    if question_count == 0:
        questions = get_sample_questions()
        
        for question, answer, category in questions:
            cursor.execute(
                "INSERT INTO trivia_questions (question, answer, category) VALUES (?, ?, ?)",
                (question, answer, category)
            )
    
    conn.commit()
    conn.close()


def get_sample_questions() -> List[Tuple[str, str, str]]:
    """Return a list of sample trivia questions"""
    return [
        # Geography
        ("What is the capital of France?", "Paris", "Geography"),
        ("Which is the largest ocean on Earth?", "Pacific Ocean", "Geography"),
        ("What is the smallest country in the world?", "Vatican City", "Geography"),
        ("What is the capital of Japan?", "Tokyo", "Geography"),
        ("Which desert is the largest in the world?", "Sahara Desert", "Geography"),
        
        # Science
        ("What is the chemical symbol for gold?", "Au", "Science"),
        ("What planet is known as the Red Planet?", "Mars", "Science"),
        ("What is the hardest natural substance on Earth?", "Diamond", "Science"),
        ("Which animal can be seen on the Porsche logo?", "Horse", "Science"),
        ("What is the closest star to Earth?", "Sun", "Science"),
        
        # History
        ("In what year did World War II end?", "1945", "History"),
        ("Who was the first President of the United States?", "George Washington", "History"),
        ("What year did the Titanic sink?", "1912", "History"),
        ("Who painted the Mona Lisa?", "Leonardo da Vinci", "History"),
        ("What ancient wonder was located in Alexandria?", "Lighthouse", "History"),
        
        # Entertainment
        ("Who played Iron Man in the Marvel Cinematic Universe?", "Robert Downey Jr", "Entertainment"),
        ("What is the name of Harry Potter's owl?", "Hedwig", "Entertainment"),
        ("Who wrote the play 'Romeo and Juliet'?", "William Shakespeare", "Entertainment"),
        ("What is the highest-grossing film of all time?", "Avatar", "Entertainment"),
        ("Who is the lead singer of the band U2?", "Bono", "Entertainment"),
        
        # Sports
        ("In which sport would you perform a slam dunk?", "Basketball", "Sports"),
        ("How many players are there in a standard soccer team?", "11", "Sports"),
        ("Which country won the FIFA World Cup in 2018?", "France", "Sports"),
        ("In which sport would you use a shuttlecock?", "Badminton", "Sports"),
        ("How many Olympic rings are there?", "5", "Sports")
    ]


def add_custom_question(db_path: str, question: str, answer: str, category: str = "General"):
    """Add a custom question to the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO trivia_questions (question, answer, category) VALUES (?, ?, ?)",
        (question, answer, category)
    )
    
    question_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return question_id
