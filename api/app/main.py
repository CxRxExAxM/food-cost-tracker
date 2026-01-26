import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .routers import products, common_products, distributors, units, recipes, uploads, auth, organizations, outlets, super_admin, ai_parse, banquet_menus, vessels, base_conversions
from .db_startup import initialize_database

app = FastAPI(
    title="RestauranTek API",
    description="Food Cost Tracker Module - API for managing food costs, tracking prices from multiple distributors, and calculating recipe costs",
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

# Initialize database on startup (PostgreSQL with Alembic migrations)
initialize_database()

# Include routers with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")
app.include_router(outlets.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(common_products.router, prefix="/api")
app.include_router(distributors.router, prefix="/api")
app.include_router(units.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(super_admin.router, prefix="/api")
app.include_router(banquet_menus.router, prefix="/api")
app.include_router(vessels.router, prefix="/api")
app.include_router(base_conversions.router, prefix="/api")
app.include_router(ai_parse.router)


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
        # Don't serve index.html for API routes or special endpoints
        if full_path.startswith(("api/", "docs", "openapi.json", "health")):
            return {"detail": "Not found"}

        # Serve index.html for all other routes (React Router will handle routing)
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
