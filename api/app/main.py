import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .routers import products, common_products, distributors, units, recipes, uploads, auth
from .database import init_db

app = FastAPI(
    title="Food Cost Tracker API",
    description="API for managing food costs, tracking prices from multiple distributors, and calculating recipe costs",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],  # React dev servers + production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
init_db()

# Include routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(common_products.router)
app.include_router(distributors.router)
app.include_router(units.router)
app.include_router(recipes.router)
app.include_router(uploads.router)


# Note: Root endpoint is defined conditionally below based on whether frontend is built


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Serve static frontend files in production
# This must come AFTER all API routes
STATIC_DIR = Path(__file__).parent.parent.parent / "static"

if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    # Serve static assets (JS, CSS, images)
    if (STATIC_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # Root route serves SPA
    @app.get("/")
    async def serve_spa_root():
        """Serve the React SPA at root."""
        return FileResponse(STATIC_DIR / "index.html")

    # Catch-all route for SPA - serve index.html for any non-API route
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the React SPA for any non-API routes."""
        # Don't serve index.html for API routes
        if full_path.startswith(("api/", "docs", "openapi.json", "health")):
            return {"detail": "Not found"}

        index_file = STATIC_DIR / "index.html"
        return FileResponse(index_file)
else:
    # No frontend built - serve API info at root
    @app.get("/")
    def root():
        """Root endpoint with API information."""
        return {
            "message": "Food Cost Tracker API",
            "version": "1.0.0",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
