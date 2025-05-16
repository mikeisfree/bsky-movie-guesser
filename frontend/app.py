from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
import secrets
import os
from pathlib import Path
from datetime import datetime, timedelta

# Conditionally import routers to prevent errors if they don't exist yet
try:
    from frontend.admin.routes import admin_router
    admin_router_available = True
except ImportError:
    admin_router_available = False

try:
    from frontend.public.routes import public_router
    public_router_available = True
except ImportError:
    public_router_available = False

from frontend.config import Settings
from frontend.database import get_db

# Initialize FastAPI app
app = FastAPI(title="BlueTrivia Admin")
settings = Settings()

# Set up security
security = HTTPBasic()

# Set up template and static directories
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# Mount static files if directory exists
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Authentication middleware
def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, settings.admin_username)
    correct_password = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Include routers if available
if admin_router_available:
    app.include_router(admin_router, prefix="/admin", dependencies=[])  # Removed authentication for testing

if public_router_available:
    app.include_router(public_router, prefix="/public")

def get_statistics():
    """Get overall game statistics for the dashboard"""
    with get_db() as conn:
        cursor = conn.cursor()
        stats = {}
        
        # Get total rounds count
        try:
            cursor.execute("SELECT COUNT(*) FROM rounds")
            stats["total_rounds"] = cursor.fetchone()[0] or 0
        except Exception as e:
            print(f"Error getting rounds count: {e}")
            stats["total_rounds"] = 0
            
        # Get total players count - FIX: Use players table directly
        try:
            cursor.execute("SELECT COUNT(*) FROM players")
            stats["total_players"] = cursor.fetchone()[0] or 0
        except Exception as e:
            print(f"Error getting players count: {e}")
            stats["total_players"] = 0
            
        # Get correct answer ratio - FIX: Use correct column name (is_correct) 
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN correct = 1 OR is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM player_responses
            """)
            result = cursor.fetchone()
            
            # If the first query fails, try with the other column name
            if not result or result["correct"] == 0:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
                    FROM player_responses
                """)
                result = cursor.fetchone()
            
            total_answers = result["total"] if result else 0
            correct_answers = result["correct"] if result else 0
            stats["total_answers"] = total_answers
            stats["correct_answers"] = correct_answers
            stats["success_rate"] = round((correct_answers / total_answers) * 100) if total_answers > 0 else 0
        except Exception as e:
            print(f"Error getting answer statistics: {e}")
            stats["total_answers"] = 0
            stats["correct_answers"] = 0
            stats["success_rate"] = 0
        
        return stats

def get_recent_winners(limit=2):
    """Get winners from the last few rounds"""
    with get_db() as conn:
        cursor = conn.cursor()
        winners = []
        
        try:
            cursor.execute("""
                SELECT 
                    pr.round_id,
                    p.handle,
                    p.display_name,
                    pr.position,
                    r.question_type,
                    (
                        CASE 
                            WHEN r.question_type = 'trivia' AND tq.question IS NOT NULL THEN tq.question
                            ELSE NULL
                        END
                    ) as question
                FROM player_responses pr
                JOIN players p ON pr.player_id = p.id
                JOIN rounds r ON pr.round_id = r.id
                LEFT JOIN trivia_questions tq ON r.question_type = 'trivia' AND r.question_id = tq.id
                WHERE pr.position = 1 AND pr.correct = 1
                ORDER BY r.start_time DESC
                LIMIT ?
            """, (limit,))
            
            winners = cursor.fetchall()
        except Exception:
            pass
        
        return winners

def get_category_stats():
    """Get success rate by category"""
    with get_db() as conn:
        cursor = conn.cursor()
        categories = []
        
        try:
            cursor.execute("""
                SELECT 
                    CASE
                        WHEN r.question_type = 'movie' THEN 'Movies'
                        WHEN r.question_type = 'trivia' THEN 
                            COALESCE((SELECT category FROM trivia_questions WHERE id = r.question_id), 'Trivia')
                        ELSE r.question_type
                    END as name,
                    COUNT(*) as total,
                    SUM(CASE WHEN pr.correct = 1 THEN 1 ELSE 0 END) as correct
                FROM player_responses pr
                JOIN rounds r ON pr.round_id = r.id
                GROUP BY name
                ORDER BY total DESC
            """)
            
            for row in cursor.fetchall():
                total = row["total"]
                correct = row["correct"]
                success_rate = round((correct / total) * 100) if total > 0 else 0
                categories.append({
                    "name": row["name"],
                    "total": total,
                    "correct": correct,
                    "success_rate": success_rate
                })
        except Exception:
            pass
        
        return categories

def get_active_tournaments():
    """Get currently active tournaments with progress info"""
    with get_db() as conn:
        cursor = conn.cursor()
        tournaments = []
        
        try:
            # First try with strict date range check
            cursor.execute("""
                SELECT 
                    t.id, 
                    t.name, 
                    t.start_date, 
                    t.duration_days, 
                    t.questions_per_day,
                    (SELECT COUNT(DISTINCT player_id) FROM tournament_results WHERE tournament_id = t.id) as player_count,
                    (SELECT COUNT(*) FROM rounds WHERE tournament_id = t.id) as questions_completed
                FROM tournaments t
                WHERE datetime(t.start_date) <= datetime('now') 
                  AND datetime(t.start_date, '+' || t.duration_days || ' days') >= datetime('now')
                  AND t.active = 1
                ORDER BY t.start_date DESC
            """)
            
            rows = cursor.fetchall()
            
            # If no tournaments found, get any active tournaments or most recent
            if not rows:
                cursor.execute("""
                    SELECT 
                        t.id, 
                        t.name, 
                        t.start_date, 
                        t.duration_days, 
                        t.questions_per_day,
                        (SELECT COUNT(DISTINCT player_id) FROM tournament_results WHERE tournament_id = t.id) as player_count,
                        (SELECT COUNT(*) FROM rounds WHERE tournament_id = t.id) as questions_completed
                    FROM tournaments t
                    WHERE t.active = 1
                    ORDER BY t.start_date DESC
                    LIMIT 1
                """)
                rows = cursor.fetchall()
            
            # If still no rows, get any tournament
            if not rows:
                cursor.execute("""
                    SELECT 
                        t.id, 
                        t.name, 
                        t.start_date, 
                        t.duration_days, 
                        t.questions_per_day,
                        0 as player_count,
                        0 as questions_completed
                    FROM tournaments t
                    ORDER BY t.start_date DESC
                    LIMIT 1
                """)
                rows = cursor.fetchall()
            
            for row in cursor.fetchall():
                # Handle the case where duration_days might be NULL or not exist
                duration_days = row.get("duration_days", 7)
                if duration_days is None:
                    duration_days = 7
                
                # Handle the case where questions_per_day might be NULL or not exist
                questions_per_day = row.get("questions_per_day", 4)
                if questions_per_day is None:
                    questions_per_day = 4
                
                # Parse date safely
                try:
                    start_date = datetime.fromisoformat(row["start_date"]) if row["start_date"] else datetime.now()
                except ValueError:
                    start_date = datetime.now()
                    
                end_date = start_date + timedelta(days=duration_days)
                days_remaining = (end_date - datetime.now()).days
                days_remaining = max(0, days_remaining)
                
                total_questions = questions_per_day * duration_days
                questions_completed = row["questions_completed"] or 0
                progress = round((questions_completed / total_questions) * 100) if total_questions > 0 else 0
                
                tournaments.append({
                    "id": row["id"],
                    "name": row["name"],
                    "start_date": row["start_date"],
                    "days_remaining": days_remaining,
                    "player_count": row["player_count"] or 0,
                    "questions_completed": questions_completed,
                    "total_questions": total_questions,
                    "progress": progress
                })
        except Exception as e:
            print(f"Error getting active tournaments: {e}")
            # Return dummy data if there's an error
            tournaments = [{
                "id": 1,
                "name": "Default Tournament",
                "start_date": datetime.now().isoformat(),
                "days_remaining": 7,
                "player_count": 0,
                "questions_completed": 0,
                "total_questions": 28,
                "progress": 0
            }]
        
        return tournaments

def get_leaderboard_data():
    """Get leaderboard data for all time, tournament, and monthly views"""
    with get_db() as conn:
        cursor = conn.cursor()
        results = {
            "all_time": [],
            "tournament": [],
            "monthly": []
        }
        
        # All time leaderboard - FIX: Check both correct and is_correct columns
        try:
            cursor.execute("""
                SELECT 
                    p.id, 
                    p.handle, 
                    p.display_name,
                    COUNT(pr.id) as attempt_count,
                    SUM(CASE 
                        WHEN pr.correct = 1 OR pr.is_correct = 1 THEN 1 
                        ELSE 0 
                    END) as correct_count
                FROM players p
                LEFT JOIN player_responses pr ON p.id = pr.player_id
                GROUP BY p.id
                HAVING attempt_count > 0
                ORDER BY correct_count DESC
                LIMIT 10
            """)
            
            rows = cursor.fetchall()
            
            # If no results, try with just is_correct
            if not rows or all(row["correct_count"] == 0 for row in rows):
                cursor.execute("""
                    SELECT 
                        p.id, 
                        p.handle, 
                        p.display_name,
                        COUNT(pr.id) as attempt_count,
                        SUM(CASE WHEN pr.is_correct = 1 THEN 1 ELSE 0 END) as correct_count
                    FROM players p
                    LEFT JOIN player_responses pr ON p.id = pr.player_id
                    GROUP BY p.id
                    HAVING attempt_count > 0
                    ORDER BY correct_count DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()
            
            # If still no results, simply get all players
            if not rows:
                cursor.execute("""
                    SELECT 
                        p.id, 
                        p.handle, 
                        p.display_name,
                        0 as attempt_count,
                        0 as correct_count
                    FROM players p
                    LIMIT 10
                """)
                rows = cursor.fetchall()
            
            for row in rows:
                attempt_count = row["attempt_count"] or 0
                correct_count = row["correct_count"] or 0
                success_rate = round((correct_count / attempt_count) * 100) if attempt_count > 0 else 0
                
                results["all_time"].append({
                    "id": row["id"],
                    "handle": row["handle"],
                    "display_name": row["display_name"],
                    "attempt_count": attempt_count,
                    "correct_count": correct_count,
                    "success_rate": success_rate
                })
        except Exception as e:
            print(f"Error getting all time leaderboard: {e}")
        
        # Tournament leaderboard (active tournaments)
        try:
            cursor.execute("""
                SELECT 
                    p.id, 
                    p.handle, 
                    p.display_name,
                    tr.total_points
                FROM tournament_results tr
                JOIN players p ON tr.player_id = p.id
                JOIN tournaments t ON tr.tournament_id = t.id
                WHERE t.active = 1
                ORDER BY tr.total_points DESC
                LIMIT 10
            """)
            
            rows = cursor.fetchall()
            
            # If no results, get player statistics as an approximation
            if not rows:
                cursor.execute("""
                    SELECT 
                        p.id, 
                        p.handle, 
                        p.display_name,
                        COUNT(pr.id) as total_points
                    FROM players p
                    LEFT JOIN player_responses pr ON p.id = pr.player_id
                    WHERE pr.correct = 1 OR pr.is_correct = 1
                    GROUP BY p.id
                    ORDER BY total_points DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()
            
            for row in rows:
                results["tournament"].append({
                    "id": row["id"],
                    "handle": row["handle"],
                    "display_name": row["display_name"],
                    "total_points": row["total_points"] or 0
                })
        except Exception as e:
            print(f"Error getting tournament leaderboard: {e}")
        
        # Monthly leaderboard
        try:
            cursor.execute("""
                SELECT 
                    p.id, 
                    p.handle, 
                    p.display_name,
                    COUNT(pr.id) as attempt_count,
                    SUM(CASE 
                        WHEN pr.correct = 1 OR pr.is_correct = 1 THEN 1 
                        ELSE 0 
                    END) as correct_count
                FROM players p
                JOIN player_responses pr ON p.id = pr.player_id
                JOIN rounds r ON pr.round_id = r.id
                WHERE strftime('%Y-%m', r.start_time) = strftime('%Y-%m', 'now')
                GROUP BY p.id
                HAVING attempt_count > 0
                ORDER BY correct_count DESC
                LIMIT 10
            """)
            
            rows = cursor.fetchall()
            
            if not rows:
                # Fall back to all-time data if no monthly data
                results["monthly"] = results["all_time"]
            else:
                for row in rows:
                    attempt_count = row["attempt_count"] or 0
                    correct_count = row["correct_count"] or 0
                    success_rate = round((correct_count / attempt_count) * 100) if attempt_count > 0 else 0
                    
                    results["monthly"].append({
                        "id": row["id"],
                        "handle": row["handle"],
                        "display_name": row["display_name"],
                        "attempt_count": attempt_count,
                        "correct_count": correct_count,
                        "success_rate": success_rate
                    })
        except Exception as e:
            print(f"Error getting monthly leaderboard: {e}")
            # Use all-time data as fallback
            results["monthly"] = results["all_time"]
        
        return results

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    try:
        # Get all statistics for the dashboard
        stats = get_statistics()
        recent_winners = get_recent_winners(limit=2)
        category_stats = get_category_stats()
        active_tournaments = get_active_tournaments()
        leaderboard_data = get_leaderboard_data()
        
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "title": "BlueTrivia",
            "stats": stats,
            "recent_winners": recent_winners,
            "category_stats": category_stats,
            "active_tournaments": active_tournaments,
            "all_time_leaders": leaderboard_data["all_time"],
            "tournament_leaders": leaderboard_data["tournament"],
            "monthly_leaders": leaderboard_data["monthly"]
        })
    except Exception as e:
        # If there's an error rendering the statistics, provide a simple page
        print(f"Error rendering dashboard: {e}")
        html_content = """
        <!DOCTYPE html>
        <html>
            <head>
                <title>BlueTrivia</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    h1 { color: #0066cc; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Welcome to BlueTrivia</h1>
                    <div class="card">
                        <h2>Navigation</h2>
                        <p><a href="/admin">Admin Interface</a></p>
                    </div>
                    <div class="card">
                        <h2>Error Loading Dashboard</h2>
                        <p>There was an error loading the dashboard statistics. This might happen if the database is not yet fully set up.</p>
                        <p>You can continue to the admin interface using the link above.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "app_name": settings.app_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
