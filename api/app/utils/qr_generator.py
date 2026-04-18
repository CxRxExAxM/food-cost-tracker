"""QR Code generation utilities for EHC Digital Forms.

Generates QR codes that encode form link URLs for staff to scan.
"""
import qrcode
from io import BytesIO
import base64
import os


def get_frontend_url() -> str:
    """Get the frontend URL for form links.

    Uses FRONTEND_URL env var, falls back to production URL.
    """
    return os.environ.get(
        "FRONTEND_URL",
        "https://food-cost-tracker.onrender.com"
    )


def generate_form_url(token: str) -> str:
    """Generate the full URL for a form link.

    Args:
        token: The form link token (43-char URL-safe string)

    Returns:
        Full URL like https://domain.com/form/abc123...
    """
    base_url = get_frontend_url().rstrip("/")
    return f"{base_url}/form/{token}"


def generate_qr_code(url: str, box_size: int = 10, border: int = 4) -> str:
    """Generate QR code as base64 PNG string.

    Args:
        url: The URL to encode in the QR code
        box_size: Size of each box in pixels (default 10)
        border: Border size in boxes (default 4, minimum per spec)

    Returns:
        Base64-encoded PNG image string (without data:image/png;base64, prefix)
    """
    qr = qrcode.QRCode(
        version=1,  # Auto-size based on content
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # 15% error correction
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def generate_qr_code_bytes(url: str, box_size: int = 10, border: int = 4) -> bytes:
    """Generate QR code as raw PNG bytes.

    Useful for endpoints that return the image directly.

    Args:
        url: The URL to encode in the QR code
        box_size: Size of each box in pixels (default 10)
        border: Border size in boxes (default 4)

    Returns:
        Raw PNG bytes
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.getvalue()


def generate_form_qr(token: str, box_size: int = 10) -> str:
    """Convenience function: generate QR code for a form token.

    Combines URL generation and QR encoding in one call.

    Args:
        token: The form link token
        box_size: Size of each box in pixels (default 10)

    Returns:
        Base64-encoded PNG image string
    """
    url = generate_form_url(token)
    return generate_qr_code(url, box_size=box_size)


def generate_daily_log_url(token: str) -> str:
    """Generate the full URL for a daily log public access link.

    Args:
        token: The outlet's daily_log_token (43-char URL-safe string)

    Returns:
        Full URL like https://domain.com/daily-log/public/abc123...
    """
    base_url = get_frontend_url().rstrip("/")
    return f"{base_url}/daily-log/public/{token}"


def generate_daily_log_qr(token: str, box_size: int = 10) -> str:
    """Generate QR code for daily log public access.

    Args:
        token: The outlet's daily_log_token
        box_size: Size of each box in pixels (default 10)

    Returns:
        Base64-encoded PNG image string
    """
    url = generate_daily_log_url(token)
    return generate_qr_code(url, box_size=box_size)
