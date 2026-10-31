import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, db_manager
from app.api.routes import auth, users, profiles, resumes, applications, autofill, ai
from app.services.seeder_service import seed_sample_development_account

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("applyforme")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB and verify indexes
    print("[ApplyForMe] Startup: connecting to database...", flush=True)
    await connect_to_mongo()
    print("[ApplyForMe] Startup: database connected.", flush=True)
    
    # Auto-seed sample dev user in development/test environments
    if settings.APP_ENV in ("development", "test") or settings.DEBUG:
        try:
            await seed_sample_development_account(db_manager.db)
            print("[ApplyForMe] Startup: sample development account verified/seeded.", flush=True)
        except Exception as e:
            logger.warning(f"[ApplyForMe] Startup seeder warning: {e}")
            
    yield
    # Shutdown: Cleanly close DB connection pool
    print("[ApplyForMe] Shutdown: closing database...", flush=True)
    await close_mongo_connection()


app = FastAPI(
    title="ApplyForMe API",
    version="1.0.0",
    description="One Profile. Smarter Applications. AI-Powered Job Application Assistant backend API.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration to allow Chrome extensions and web frontend
# Wildcard '*' is excluded when allow_credentials=True to satisfy browser CORS security standards
cors_origins = [o for o in settings.CORS_ORIGINS if o != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(profiles.router, prefix=f"{settings.API_V1_PREFIX}/profiles")
app.include_router(profiles.router, prefix=f"{settings.API_V1_PREFIX}/profile")
app.include_router(resumes.router, prefix=settings.API_V1_PREFIX)
app.include_router(resumes.router, prefix=f"{settings.API_V1_PREFIX}/resume")
app.include_router(applications.router, prefix=settings.API_V1_PREFIX)
app.include_router(autofill.router, prefix=settings.API_V1_PREFIX)
app.include_router(ai.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    """Service health and readiness check."""
    return {
        "status": "healthy",
        "service": "ApplyForMe Backend",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/test-form", response_class=FileResponse, tags=["Testing"])
@app.get("/test_application_form.html", response_class=FileResponse, tags=["Testing"])
async def serve_test_form():
    """Serve the local test job application form for end-to-end autofill verification."""
    candidate_paths = [
        Path(__file__).resolve().parent.parent.parent / "extension" / "public" / "test_application_form.html",
        Path(__file__).resolve().parent.parent / "public" / "test_application_form.html",
        Path("extension/public/test_application_form.html").resolve(),
    ]
    for p in candidate_paths:
        if p.is_file():
            return FileResponse(str(p), media_type="text/html")
    return HTMLResponse("<h3>Test application form not found on disk.</h3>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
