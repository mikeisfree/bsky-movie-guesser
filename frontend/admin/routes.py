from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict
from datetime import datetime
import json
import sqlite3
from pathlib import Path

from frontend.database import get_db
from frontend.models import Tournament, TriviaQuestion, Player

admin_router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Dashboard route
@admin_router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get summary statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM tournaments")
            tournament_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            tournament_count = 0
            
        try:
            cursor.execute("SELECT COUNT(*) FROM trivia_questions")
            question_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            question_count = 0
            
        try:
            cursor.execute("SELECT COUNT(*) FROM players")
            player_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            player_count = 0
            
        try:
            cursor.execute("SELECT COUNT(*) FROM rounds")
            round_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            round_count = 0
        
        # Get active tournaments
        active_tournaments = []
        try:
            cursor.execute(
                """
                SELECT * FROM tournaments 
                WHERE datetime(start_date) <= datetime('now') 
                AND datetime(start_date, '+' || duration_days || ' days') >= datetime('now')
                AND active = 1
                ORDER BY start_date DESC
                """
            )
            active_tournaments_data = cursor.fetchall()
            for t in active_tournaments_data:
                tournament = {
                    "id": t["id"],
                    "name": t["name"],
                    "start_date": t["start_date"],
                    "duration_days": t["duration_days"],
                }
                active_tournaments.append(tournament)
        except sqlite3.OperationalError:
            pass
        
        # Get recent rounds
        recent_rounds = []
        try:
            cursor.execute(
                """
                SELECT r.id, r.start_time, r.question_type, r.question_id, 
                       COUNT(pr.id) as response_count,
                       SUM(CASE WHEN pr.correct = 1 THEN 1 ELSE 0 END) as correct_count
                FROM rounds r
                LEFT JOIN player_responses pr ON r.id = pr.round_id
                GROUP BY r.id
                ORDER BY r.start_time DESC
                LIMIT 5
                """
            )
            recent_rounds = cursor.fetchall()
        except sqlite3.OperationalError:
            pass
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "stats": {
                "tournaments": tournament_count,
                "questions": question_count,
                "players": player_count,
                "rounds": round_count
            },
            "active_tournaments": active_tournaments,
            "recent_rounds": recent_rounds
        }
    )

# Tournament routes
@admin_router.get("/tournaments", response_class=HTMLResponse)
async def list_tournaments(request: Request):
    tournaments = []
    with get_db() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, start_date, duration_days, questions_per_day, 
                       source_distribution, bonus_first, bonus_second, bonus_third, active
                FROM tournaments 
                ORDER BY start_date DESC
            """)
            for row in cursor.fetchall():
                tournaments.append({
                    "id": row["id"],
                    "name": row["name"],
                    "start_date": row["start_date"],
                    "duration_days": row["duration_days"],
                    "questions_per_day": row["questions_per_day"],
                    "source_distribution": row["source_distribution"],
                    "bonus_first": row["bonus_first"],
                    "bonus_second": row["bonus_second"],
                    "bonus_third": row["bonus_third"],
                    "active": bool(row["active"])
                })
        except sqlite3.OperationalError as e:
            print(f"Database error: {e}")
    
    return templates.TemplateResponse(
        "admin/tournaments.html",
        {"request": request, "tournaments": tournaments}
    )

@admin_router.get("/tournaments/new", response_class=HTMLResponse)
async def new_tournament_form(request: Request):
    return templates.TemplateResponse(
        "admin/tournament_form.html",
        {"request": request, "tournament": None}
    )

@admin_router.post("/tournaments/new")
async def create_tournament(
    request: Request,
    name: str = Form(...),
    start_date: str = Form(...),
    duration_days: int = Form(...),
    questions_per_day: int = Form(...),
    movie_weight: float = Form(0.5),
    trivia_weight: float = Form(0.5),
    bonus_first: int = Form(10),
    bonus_second: int = Form(5),
    bonus_third: int = Form(3),
):
    try:
        # Create source distribution JSON
        source_dist = {
            "movie": float(movie_weight),
            "trivia": float(trivia_weight)
        }
        
        # Format the date properly for SQLite
        try:
            parsed_date = datetime.fromisoformat(start_date)
            formatted_date = parsed_date.isoformat()
        except ValueError:
            formatted_date = start_date  # Use as-is if already in correct format
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tournaments (
                    name, start_date, duration_days, questions_per_day, 
                    source_distribution, bonus_first, bonus_second, bonus_third, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    name,
                    formatted_date,
                    duration_days,
                    questions_per_day,
                    json.dumps(source_dist),
                    bonus_first,
                    bonus_second,
                    bonus_third
                )
            )
            conn.commit()
            tournament_id = cursor.lastrowid
        
        return RedirectResponse(url=f"/admin/tournaments/{tournament_id}", status_code=303)
    except Exception as e:
        print(f"Error creating tournament: {e}")
        return templates.TemplateResponse(
            "admin/tournament_form.html",
            {
                "request": request, 
                "tournament": None,
                "error": str(e)
            },
            status_code=400
        )

@admin_router.get("/tournaments/{tournament_id}", response_class=HTMLResponse)
async def view_tournament(request: Request, tournament_id: int):
    tournament = None
    rounds = []
    players = []
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Get tournament details
        cursor.execute(
            """
            SELECT id, name, start_date, duration_days, questions_per_day, 
                   source_distribution, bonus_first, bonus_second, bonus_third, active
            FROM tournaments 
            WHERE id = ?
            """, 
            (tournament_id,)
        )
        row = cursor.fetchone()
        if row:
            tournament = {
                "id": row["id"],
                "name": row["name"],
                "start_date": row["start_date"],
                "duration_days": row["duration_days"],
                "questions_per_day": row["questions_per_day"],
                "source_distribution": json.loads(row["source_distribution"]) if row["source_distribution"] else {},
                "bonus_first": row["bonus_first"],
                "bonus_second": row["bonus_second"],
                "bonus_third": row["bonus_third"],
                "active": bool(row["active"])
            }
            
            # Get tournament rounds
            try:
                cursor.execute(
                    """
                    SELECT r.id, r.start_time, r.question_type, r.completed,
                           COUNT(pr.id) as response_count
                    FROM rounds r
                    LEFT JOIN player_responses pr ON r.id = pr.round_id
                    WHERE r.tournament_id = ?
                    GROUP BY r.id
                    ORDER BY r.start_time DESC
                    """,
                    (tournament_id,)
                )
                rounds = cursor.fetchall()
            except sqlite3.OperationalError:
                pass
                
            # Get tournament players
            try:
                cursor.execute(
                    """
                    SELECT p.id, p.handle, p.display_name,
                           tr.total_points, tr.final_position
                    FROM tournament_results tr
                    JOIN players p ON tr.player_id = p.id
                    WHERE tr.tournament_id = ?
                    ORDER BY tr.total_points DESC
                    """,
                    (tournament_id,)
                )
                players = cursor.fetchall()
            except sqlite3.OperationalError:
                pass
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    return templates.TemplateResponse(
        "admin/tournament_detail.html",
        {
            "request": request, 
            "tournament": tournament,
            "rounds": rounds,
            "players": players
        }
    )

@admin_router.post("/tournaments/{tournament_id}/update")
async def update_tournament(
    request: Request,
    tournament_id: int,
    name: str = Form(...),
    duration_days: int = Form(...),
    questions_per_day: int = Form(...),
    movie_weight: float = Form(0.5),
    trivia_weight: float = Form(0.5),
    bonus_first: int = Form(10),
    bonus_second: int = Form(5),
    bonus_third: int = Form(3),
    active: bool = Form(True),
):
    try:
        # Create source distribution JSON
        source_dist = {
            "movie": float(movie_weight),
            "trivia": float(trivia_weight)
        }
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE tournaments SET
                    name = ?, 
                    duration_days = ?, 
                    questions_per_day = ?, 
                    source_distribution = ?, 
                    bonus_first = ?, 
                    bonus_second = ?, 
                    bonus_third = ?,
                    active = ?
                WHERE id = ?
                """,
                (
                    name,
                    duration_days,
                    questions_per_day,
                    json.dumps(source_dist),
                    bonus_first,
                    bonus_second,
                    bonus_third,
                    1 if active else 0,
                    tournament_id
                )
            )
            conn.commit()
        
        return RedirectResponse(url=f"/admin/tournaments/{tournament_id}", status_code=303)
    except Exception as e:
        print(f"Error updating tournament: {e}")
        # Fetch the tournament again to redisplay the form with error
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
            row = cursor.fetchone()
            tournament = dict(row) if row else None
        
        return templates.TemplateResponse(
            "admin/tournament_edit.html",
            {
                "request": request, 
                "tournament": tournament,
                "error": str(e)
            },
            status_code=400
        )

@admin_router.get("/tournaments/{tournament_id}/edit", response_class=HTMLResponse)
async def edit_tournament_form(request: Request, tournament_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tournaments WHERE id = ?", 
            (tournament_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tournament not found")
        
        tournament = {
            "id": row["id"],
            "name": row["name"],
            "start_date": row["start_date"],
            "duration_days": row["duration_days"],
            "questions_per_day": row["questions_per_day"],
            "source_distribution": json.loads(row["source_distribution"]) if row["source_distribution"] else {},
            "bonus_first": row["bonus_first"],
            "bonus_second": row["bonus_second"],
            "bonus_third": row["bonus_third"],
            "active": bool(row["active"])
        }
    
    return templates.TemplateResponse(
        "admin/tournament_edit.html",
        {"request": request, "tournament": tournament}
    )

@admin_router.post("/tournaments/{tournament_id}/delete")
async def delete_tournament(tournament_id: int):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # First check if there are any rounds associated with this tournament
            cursor.execute("SELECT COUNT(*) FROM rounds WHERE tournament_id = ?", (tournament_id,))
            round_count = cursor.fetchone()[0]
            
            if round_count > 0:
                # If there are rounds, just set the tournament to inactive
                cursor.execute(
                    "UPDATE tournaments SET active = 0 WHERE id = ?",
                    (tournament_id,)
                )
            else:
                # If no rounds, we can safely delete
                cursor.execute(
                    "DELETE FROM tournament_results WHERE tournament_id = ?",
                    (tournament_id,)
                )
                cursor.execute(
                    "DELETE FROM tournaments WHERE id = ?",
                    (tournament_id,)
                )
            
            conn.commit()
        
        return RedirectResponse(url="/admin/tournaments", status_code=303)
    except Exception as e:
        print(f"Error deleting tournament: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Trivia questions routes
@admin_router.get("/trivia", response_class=HTMLResponse)
async def list_trivia_questions(
    request: Request,
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    questions = []
    categories = []
    total_count = 0
    
    with get_db() as conn:
        try:
            cursor = conn.cursor()
            
            # Get categories for filter
            cursor.execute("SELECT DISTINCT category FROM trivia_questions ORDER BY category")
            categories = [row[0] for row in cursor.fetchall()]
            
            # Build query
            query = "SELECT * FROM trivia_questions"
            params = []
            
            if category:
                query += " WHERE category = ?"
                params.append(category)
                
            # Count total for pagination
            count_query = f"SELECT COUNT(*) FROM ({query})"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Add pagination
            query += " ORDER BY category, id LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])
            
            # Execute final query
            cursor.execute(query, params)
            questions = [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.OperationalError as e:
            print(f"Database error in trivia listing: {e}")
    
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    
    return templates.TemplateResponse(
        "admin/trivia_list.html",
        {
            "request": request,
            "questions": questions,
            "categories": categories,
            "current_category": category,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count
        }
    )

@admin_router.get("/trivia/new", response_class=HTMLResponse)
async def new_trivia_form(request: Request):
    categories = []
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT category FROM trivia_questions ORDER BY category")
            categories = [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # If table doesn't exist yet
            categories = ["Movies", "Science", "History", "Geography", "Sports", "Entertainment"]
    
    return templates.TemplateResponse(
        "admin/trivia_form.html",
        {"request": request, "question": None, "categories": categories}
    )

@admin_router.post("/trivia/new")
async def create_trivia(
    request: Request,
    category: str = Form(...),
    question: str = Form(...),
    answer: str = Form(...),
    difficulty: str = Form("medium"),
    image_url: Optional[str] = Form(None),
):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO trivia_questions (
                    category, question, answer, difficulty, image_url
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    category,
                    question,
                    answer,
                    difficulty,
                    image_url
                )
            )
            conn.commit()
            question_id = cursor.lastrowid
        
        return RedirectResponse(url="/admin/trivia", status_code=303)
    except Exception as e:
        print(f"Error creating trivia question: {e}")
        categories = ["Movies", "Science", "History", "Geography", "Sports", "Entertainment"]
        
        with get_db() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT category FROM trivia_questions ORDER BY category")
                categories = [row[0] for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                pass
        
        return templates.TemplateResponse(
            "admin/trivia_form.html",
            {
                "request": request,
                "question": {
                    "category": category,
                    "question": question,
                    "answer": answer,
                    "difficulty": difficulty,
                    "image_url": image_url
                },
                "categories": categories,
                "error": str(e)
            },
            status_code=400
        )

@admin_router.post("/trivia/{question_id}/delete")
async def delete_trivia_question(question_id: int):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # First check if the question exists
            cursor.execute("SELECT id FROM trivia_questions WHERE id = ?", (question_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Question not found")
            
            # Delete the question
            cursor.execute("DELETE FROM trivia_questions WHERE id = ?", (question_id,))
            conn.commit()
        
        return RedirectResponse(url="/admin/trivia", status_code=303)
    except Exception as e:
        print(f"Error deleting trivia question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Player management routes
@admin_router.get("/players", response_class=HTMLResponse)
async def list_players(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    players = []
    total_count = 0
    
    with get_db() as conn:
        try:
            cursor = conn.cursor()
            
            # Get total count for pagination
            cursor.execute("SELECT COUNT(*) FROM players")
            total_count = cursor.fetchone()[0]
            
            # Get players with response counts
            cursor.execute(
                """
                SELECT 
                    p.id, 
                    p.handle, 
                    p.display_name,
                    COUNT(pr.id) as response_count,
                    SUM(CASE WHEN pr.correct = 1 THEN 1 ELSE 0 END) as correct_count
                FROM players p
                LEFT JOIN player_responses pr ON p.id = pr.player_id
                GROUP BY p.id
                ORDER BY correct_count DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, (page - 1) * page_size)
            )
            players = cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(f"Database error in player listing: {e}")
    
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    
    return templates.TemplateResponse(
        "admin/players.html",
        {
            "request": request,
            "players": players,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count
        }
    )
