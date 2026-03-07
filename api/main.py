"""
FastAPI Application - Event Lifecycle Management System
Main entry point for REST API
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import time
import os

from api.routes import events, registrations, attendance, analytics
from db.base import init_db
from utils.logger import logger


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    - Startup: Initialize database
    - Shutdown: Cleanup resources
    """
    # Startup
    try:
        logger.info("[API] Starting EventEngine API server...")
        init_db()
        logger.info("[API] Database initialized successfully")
    except Exception as e:
        logger.error(f"[API] Database initialization failed: {e}")
        logger.info("[API] Continuing without database initialization...")
    
    yield
    
    # Shutdown
    logger.info("[API] Shutting down EventEngine API server...")


# Create FastAPI application
app = FastAPI(
    title="EventEngine API",
    description="Autonomous Event Lifecycle Management System with AI-powered insights",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS Configuration - Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        f"[API] {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )
    
    return response


# Health check endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint - API status"""
    return {
        "service": "EventEngine API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "EventEngine API",
        "timestamp": time.time()
    }


# Mount routers
app.include_router(
    events.router,
    prefix="/api/events",
    tags=["Events"]
)

app.include_router(
    registrations.router,
    prefix="/api/registrations",
    tags=["Registrations"]
)

app.include_router(
    attendance.router,
    prefix="/api/attendance",
    tags=["Attendance"]
)

app.include_router(
    analytics.router,
    prefix="/api/analytics",
    tags=["Analytics"]
)


# Mount static files for frontend
# Get the path to the frontend directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Mount frontend static files
if os.path.exists(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    logger.info(f"[API] Frontend mounted at /frontend from {FRONTEND_DIR}")
else:
    logger.warning(f"[API] Frontend directory not found at {FRONTEND_DIR}")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(f"[API] Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("[API] Starting server on http://localhost:8000")
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
