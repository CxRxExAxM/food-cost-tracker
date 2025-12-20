# Combined Dockerfile for Render deployment
# Builds frontend and serves via FastAPI
# Cache bust: 2025-12-19-v2

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

# Build with empty API URL (will use relative paths)
ENV VITE_API_URL=""
RUN npm run build

# Stage 2: Python backend with frontend static files
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY db/ ./db/

# Copy Alembic configuration and migrations
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist ./static

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (Render uses PORT env var)
EXPOSE 8000

# Run migrations then start the application
CMD ["sh", "-c", "alembic upgrade head && uvicorn api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
