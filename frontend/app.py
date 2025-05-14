from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
import secrets
import os
from pathlib import Path

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
    app.include_router(admin_router, prefix="/admin", dependencies=[Depends(verify_admin)])

if public_router_available:
    app.include_router(public_router, prefix="/public")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Check if index.html template exists
    if (templates_path / "index.html").exists():
        return templates.TemplateResponse("index.html", {"request": request, "title": "BlueTrivia"})
    else:
        # Provide a simple HTML response if template doesn't exist
        html_content = """
        <!DOCTYPE html>
        <html>
            <head>
                <title>BlueTrivia</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    h1 { color: #0066cc; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Welcome to BlueTrivia Admin</h1>
                    <div class="card">
                        <h2>Navigation</h2>
                        <p><a href="/admin">Admin Interface</a></p>
                        <p><a href="/public">Public Statistics</a></p>
                    </div>
                    <div class="card">
                        <h2>Setup in Progress</h2>
                        <p>The frontend is still being set up. You can access the admin interface 
                        or public statistics using the links above.</p>
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
