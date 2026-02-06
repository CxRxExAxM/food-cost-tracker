"""
Centralized configuration with environment variable support.

All hardcoded values should be defined here and imported where needed.
Environment variables can override defaults for different deployment environments.
"""
import os


# =============================================================================
# Database Connection Pool
# =============================================================================
DB_MIN_CONNECTIONS = int(os.getenv("DB_MIN_CONNECTIONS", "2"))
DB_MAX_CONNECTIONS = int(os.getenv("DB_MAX_CONNECTIONS", "10"))


# =============================================================================
# Authentication
# =============================================================================
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours


# =============================================================================
# API Pagination Defaults
# =============================================================================
# Default page sizes
DEFAULT_PAGE_LIMIT = int(os.getenv("DEFAULT_PAGE_LIMIT", "100"))
DEFAULT_PAGE_LIMIT_LARGE = int(os.getenv("DEFAULT_PAGE_LIMIT_LARGE", "1000"))

# Maximum allowed limits
MAX_PAGE_LIMIT = int(os.getenv("MAX_PAGE_LIMIT", "500"))
MAX_PAGE_LIMIT_LARGE = int(os.getenv("MAX_PAGE_LIMIT_LARGE", "10000"))


# =============================================================================
# Banquet Menu Defaults
# =============================================================================
DEFAULT_GUEST_COUNT = int(os.getenv("DEFAULT_GUEST_COUNT", "50"))
