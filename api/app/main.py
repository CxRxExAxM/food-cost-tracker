from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import products, common_products, distributors, units, recipes

app = FastAPI(
    title="Food Cost Tracker API",
    description="API for managing food costs, tracking prices from multiple distributors, and calculating recipe costs",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router)
app.include_router(common_products.router)
app.include_router(distributors.router)
app.include_router(units.router)
app.include_router(recipes.router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "message": "Food Cost Tracker API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
