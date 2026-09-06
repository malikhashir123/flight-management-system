from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.database import engine, Base
from backend.app.api import auth, admin, flights, bookings, waitlist, support

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize tables on startup if not already created
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Clean up engine
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Flight Management System REST API.\n\n"
        "Built strictly according to flight_management_system_feature_list.pdf.\n"
        "Features: FastAPI live transactional write path, Supabase PostgreSQL ledger, "
        "n8n background automation, Grounded RAG with Pinecone, and Gmail notifications."
    ),
    lifespan=lifespan
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(flights.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(waitlist.router, prefix="/api/v1")
app.include_router(support.router, prefix="/api/v1")

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=b"", media_type="image/x-icon", status_code=204)


# Mount static asset directories
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
css_dir = os.path.join(frontend_dir, "css")
js_dir = os.path.join(frontend_dir, "js")

if os.path.exists(css_dir):
    app.mount("/css", StaticFiles(directory=css_dir), name="css")
if os.path.exists(js_dir):
    app.mount("/js", StaticFiles(directory=js_dir), name="js")

@app.get("/health", tags=["Health & System Status"])
async def health_check():
    """Health check endpoint for Render/Fly.io/K8s liveness probes."""
    return {
        "status": "HEALTHY",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database_backend": "PostgreSQL" if "postgres" in settings.DATABASE_URL else "SQLite"
    }

@app.get("/", tags=["Passenger Web Portal"])
@app.get("/index.html", tags=["Passenger Web Portal"])
async def serve_passenger_portal():
    """Passenger Portal: Open to public with zero password required."""
    index_file = os.path.join(frontend_dir, "index.html")
    return FileResponse(index_file)

@app.get("/admin", tags=["Admin Web Portal"])
@app.get("/admin/", tags=["Admin Web Portal"])
@app.get("/admin.html", tags=["Admin Web Portal"])
async def serve_admin_portal():
    """Operations & Fleet Admin Portal: Protected by passcode 'admin123'."""
    admin_file = os.path.join(frontend_dir, "admin.html")
    return FileResponse(admin_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
