from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pathlib import Path

from frontend.database import get_db
from frontend.models import Player, Tournament

public_router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

@public_router.get("/leaderboard", response_class=HTMLResponse)
async def global_leaderboard(
    request: Request,
    tournament_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100)
):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get active tournaments for selector
        cursor.execute(
            """
            SELECT * FROM tournaments 
            WHERE datetime(start_date) <= datetime('now') 
            AND datetime(start_date, '+' || duration_days || ' days') >= datetime('now')
            ORDER BY start_date DESC
            """
        )
        tournaments_data = cursor.fetchall()
        active_tournaments = [Tournament.from_db_row(dict(t)) for t in tournaments_data]
        
        if tournament_id:
            # Tournament specific leaderboard
            cursor.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
            tournament_row = cursor.fetchone()
            if not tournament_row:
                raise HTTPException(status_code=404, detail="Tournament not found")
            
            tournament = Tournament.from_db_row(dict(tournament_row))
            
            # Get total players count
            cursor.execute(
                "SELECT COUNT(*) FROM tournament_results WHERE tournament_id = ?", 
                (tournament_id,)
            )
            total_count = cursor.fetchone()[0]
            
            # Get player results for this tournament with pagination
            cursor.execute(
                """
                SELECT tr.player_id, p.handle, p.display_name, 
                       tr.total_points, tr.final_position, tr.bonus_points
                FROM tournament_results tr
                JOIN players p ON tr.player_id = p.id
                WHERE tr.tournament_id = ?
                ORDER BY tr.total_points DESC
                LIMIT ? OFFSET ?
                """,
                (tournament_id, page_size, (page - 1) * page_size)
            )
            leaderboard_data = cursor.fetchall()
            
            title = f"Tournament: {tournament.name}"
            
        else:
            # Global all-time leaderboard
            cursor.execute("SELECT COUNT(*) FROM players")
            total_count = cursor.fetchone()[0]
            
            cursor.execute(
                """
                SELECT p.id, p.handle, p.display_name,
                    COUNT(CASE WHEN r.correct = 1 THEN 1 END) as correct_count,
                    COUNT(r.id) as total_attempts,
                    SUM(rr.points_earned) as total_points
                FROM players p
                LEFT JOIN player_responses r ON p.id = r.player_id
                LEFT JOIN round_results rr ON p.id = rr.player_id
                GROUP BY p.id, p.handle, p.display_name
                ORDER BY total_points DESC, correct_count DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, (page - 1) * page_size)
            )
            leaderboard_data = cursor.fetchall()
            
            tournament = None
            title = "Global Leaderboard"
    
    total_pages = (total_count + page_size - 1) // page_size
    
    return templates.TemplateResponse(
        "public/leaderboard.html",
        {
            "request": request,
            "leaderboard": leaderboard_data,
            "title": title,
            "tournament": tournament,
            "active_tournaments": active_tournaments,
            "page": page,
            "total_pages": total_pages
        }
    )

@public_router.get("/players/{handle}", response_class=HTMLResponse)
async def player_profile(request: Request, handle: str):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get player details
        cursor.execute("SELECT * FROM players WHERE handle = ?", (handle,))
        player_row = cursor.fetchone()
        if not player_row:
            raise HTTPException(status_code=404, detail="Player not found")
        
        player = Player(**dict(player_row))
        
        # Get player statistics
        cursor.execute(
            """
            SELECT 
                COUNT(CASE WHEN pr.correct = 1 THEN 1 END) as correct_count,
                COUNT(pr.id) as total_attempts,
                (SELECT COUNT(DISTINCT r.id) FROM rounds r) as total_rounds,
                (SELECT COUNT(DISTINCT r.id) 
                 FROM rounds r 
                 JOIN player_responses p ON r.id = p.round_id 
                 WHERE p.player_id = ?) as participated_rounds
            FROM player_responses pr
            WHERE pr.player_id = ?
            """,
            (player.id, player.id)
        )
        stats = dict(cursor.fetchone())
        
        # Get player tournament history
        cursor.execute(
            """
            SELECT tr.tournament_id, t.name, tr.total_points, tr.final_position, tr.bonus_points
            FROM tournament_results tr
            JOIN tournaments t ON tr.tournament_id = t.id
            WHERE tr.player_id = ?
            ORDER BY t.start_date DESC
            """,
            (player.id,)
        )
        tournaments = cursor.fetchall()
        
        # Get recent game results
        cursor.execute(
            """
            SELECT r.id, r.start_time, r.question_type, pr.correct, pr.position
            FROM player_responses pr
            JOIN rounds r ON pr.round_id = r.id
            WHERE pr.player_id = ?
            ORDER BY r.start_time DESC
            LIMIT 10
            """,
            (player.id,)
        )
        recent_games = cursor.fetchall()
        
        # Get correctness by category
        cursor.execute(
            """
            SELECT 
                CASE
                    WHEN r.question_type = 'movie' THEN 'Movies'
                    WHEN r.question_type = 'trivia' THEN 
                        (SELECT category FROM trivia_questions WHERE id = r.question_id)
                    ELSE r.question_type
                END as category,
                COUNT(pr.id) as attempts,
                SUM(CASE WHEN pr.correct = 1 THEN 1 ELSE 0 END) as correct
            FROM player_responses pr
            JOIN rounds r ON pr.round_id = r.id
            WHERE pr.player_id = ?
            GROUP BY category
            ORDER BY attempts DESC
            """,
            (player.id,)
        )
        categories = cursor.fetchall()
    
    return templates.TemplateResponse(
        "public/player_profile.html",
        {
            "request": request,
            "player": player,
            "stats": stats,
            "tournaments": tournaments,
            "recent_games": recent_games,
            "categories": categories
        }
    )

@public_router.get("/tournaments", response_class=HTMLResponse)
async def tournament_list(request: Request):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all tournaments
        cursor.execute(
            """
            SELECT t.*, 
                   COUNT(DISTINCT tr.player_id) as player_count,
                   (datetime(t.start_date, '+' || t.duration_days || ' days') < datetime('now')) as is_completed
            FROM tournaments t
            LEFT JOIN tournament_results tr ON t.id = tr.tournament_id
            GROUP BY t.id
            ORDER BY 
                CASE 
                    WHEN datetime(t.start_date) <= datetime('now') AND 
                         datetime(t.start_date, '+' || t.duration_days || ' days') >= datetime('now')
                    THEN 0
                    WHEN datetime(t.start_date) > datetime('now')
                    THEN 1
                    ELSE 2
                END,
                t.start_date DESC
            """
        )
        tournaments_data = cursor.fetchall()
    
    return templates.TemplateResponse(
        "public/tournaments.html",
        {
            "request": request,
            "tournaments": tournaments_data
        }
    )

@public_router.get("/tournaments/{tournament_id}", response_class=HTMLResponse)
async def tournament_detail(request: Request, tournament_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get tournament details
        cursor.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
        tournament_row = cursor.fetchone()
        if not tournament_row:
            raise HTTPException(status_code=404, detail="Tournament not found")
        
        tournament = Tournament.from_db_row(dict(tournament_row))
        
        # Get tournament top players
        cursor.execute(
            """
            SELECT tr.player_id, p.handle, p.display_name, 
                   tr.total_points, tr.final_position, tr.bonus_points
            FROM tournament_results tr
            JOIN players p ON tr.player_id = p.id
            WHERE tr.tournament_id = ?
            ORDER BY tr.final_position IS NULL, tr.final_position ASC, tr.total_points DESC
            LIMIT 10
            """,
            (tournament_id,)
        )
        top_players = cursor.fetchall()
        
        # Get tournament rounds
        cursor.execute(
            """
            SELECT r.id, r.start_time, r.question_type, 
                   COUNT(pr.id) as response_count,
                   SUM(CASE WHEN pr.correct = 1 THEN 1 ELSE 0 END) as correct_count
            FROM rounds r
            LEFT JOIN player_responses pr ON r.id = pr.round_id
            WHERE r.tournament_id = ?
            GROUP BY r.id
            ORDER BY r.start_time DESC
            LIMIT 20
            """,
            (tournament_id,)
        )
        rounds = cursor.fetchall()
        
        # Get tournament statistics
        cursor.execute(
            """
            SELECT 
                COUNT(DISTINCT pr.player_id) as total_players,
                COUNT(DISTINCT r.id) as total_rounds,
                SUM(CASE WHEN pr.correct = 1 THEN 1 ELSE 0 END) as total_correct,
                COUNT(pr.id) as total_responses,
                CASE 
                    WHEN COUNT(pr.id) > 0 
                    THEN ROUND(SUM(CASE WHEN pr.correct = 1 THEN 1.0 ELSE 0.0 END) / COUNT(pr.id) * 100, 1)
                    ELSE 0
                END as success_rate
            FROM rounds r
            LEFT JOIN player_responses pr ON r.id = pr.round_id
            WHERE r.tournament_id = ?
            """,
            (tournament_id,)
        )
        stats = dict(cursor.fetchone())
    
    return templates.TemplateResponse(
        "public/tournament_detail.html",
        {
            "request": request,
            "tournament": tournament,
            "top_players": top_players,
            "rounds": rounds,
            "stats": stats
        }
    )

@public_router.get("/", response_class=HTMLResponse)
async def public_home(request: Request):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get overall statistics
        cursor.execute(
            """
            SELECT 
                COUNT(DISTINCT r.id) as total_rounds,
                COUNT(DISTINCT pr.player_id) as total_players,
                SUM(CASE WHEN pr.correct = 1 THEN 1 ELSE 0 END) as total_correct,
                COUNT(pr.id) as total_responses,
                CASE 
                    WHEN COUNT(pr.id) > 0 
                    THEN ROUND(SUM(CASE WHEN pr.correct = 1 THEN 1.0 ELSE 0.0 END) / COUNT(pr.id) * 100, 1)
                    ELSE 0
                END as success_rate
            FROM rounds r
            LEFT JOIN player_responses pr ON r.id = pr.round_id
            """
        )
        stats = dict(cursor.fetchone())
        
        # Get top players
        cursor.execute(
            """
            SELECT p.id, p.handle, p.display_name,
                COUNT(CASE WHEN pr.correct = 1 THEN 1 END) as correct_count,
                COUNT(pr.id) as total_attempts,
                SUM(rr.points_earned) as total_points
            FROM players p
            LEFT JOIN player_responses pr ON p.id = pr.player_id
            LEFT JOIN round_results rr ON p.id = rr.player_id
            GROUP BY p.id, p.handle, p.display_name
            HAVING total_attempts > 0
            ORDER BY total_points DESC
            LIMIT 5
            """
        )
        top_players = cursor.fetchall()
        
        # Get active tournaments
        cursor.execute(
            """
            SELECT t.id, t.name, t.start_date, t.duration_days,
                   COUNT(DISTINCT tr.player_id) as player_count
            FROM tournaments t
            LEFT JOIN tournament_results tr ON t.id = tr.tournament_id
            WHERE datetime(t.start_date) <= datetime('now') 
            AND datetime(t.start_date, '+' || t.duration_days || ' days') >= datetime('now')
            GROUP BY t.id
            ORDER BY t.start_date ASC
            LIMIT 3
            """
        )
        active_tournaments = cursor.fetchall()
        
        # Get recent rounds
        cursor.execute(
            """
            SELECT r.id, r.start_time, r.question_type, 
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
    
    return templates.TemplateResponse(
        "public/index.html",
        {
            "request": request,
            "stats": stats,
            "top_players": top_players,
            "active_tournaments": active_tournaments,
            "recent_rounds": recent_rounds
        }
    )
