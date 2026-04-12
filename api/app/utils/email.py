"""Email utility for EHC module.

Handles transactional email sending via Resend API.
Used for QR code distribution, test emails, and notifications.

Requires RESEND_API_KEY environment variable.
Domain must be verified in Resend dashboard (restaurantek.io).
"""
import os
from typing import Optional
from datetime import datetime

# Resend is optional - gracefully handle if not configured
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    resend = None

# Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDER_EMAIL = "RestauranTek EHC <noreply@restaurantek.io>"
SENDER_NAME = "RestauranTek EHC"


def is_email_configured() -> bool:
    """Check if email sending is properly configured."""
    return RESEND_AVAILABLE and bool(RESEND_API_KEY)


def get_email_status() -> dict:
    """Get email configuration status for UI display."""
    if not RESEND_AVAILABLE:
        return {
            "configured": False,
            "error": "Resend package not installed",
            "sender": None
        }

    if not RESEND_API_KEY:
        return {
            "configured": False,
            "error": "RESEND_API_KEY not set",
            "sender": None
        }

    return {
        "configured": True,
        "error": None,
        "sender": SENDER_EMAIL
    }


def send_email(
    to_email: str,
    subject: str,
    html: str,
    to_name: Optional[str] = None,
    reply_to: Optional[str] = None
) -> dict:
    """Send an email via Resend.

    Returns:
        dict with 'success', 'resend_id', and optionally 'error'
    """
    if not is_email_configured():
        return {
            "success": False,
            "resend_id": None,
            "error": "Email not configured"
        }

    # Initialize Resend with API key
    resend.api_key = RESEND_API_KEY

    try:
        # Build recipient
        to_address = f"{to_name} <{to_email}>" if to_name else to_email

        params = {
            "from": SENDER_EMAIL,
            "to": [to_address],
            "subject": subject,
            "html": html,
        }

        if reply_to:
            params["reply_to"] = reply_to

        response = resend.Emails.send(params)

        return {
            "success": True,
            "resend_id": response.get("id"),
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "resend_id": None,
            "error": str(e)
        }


def send_form_qr_email(
    to_email: str,
    to_name: str,
    outlet_name: str,
    form_name: str,
    period_label: str,
    form_url: str,
    qr_image_base64: Optional[str] = None,
    custom_message: Optional[str] = None
) -> dict:
    """Send a form QR code email to a contact.

    Args:
        to_email: Recipient email address
        to_name: Recipient name
        outlet_name: Name of the outlet (e.g., "Main Kitchen")
        form_name: Name of the form (e.g., "Kitchen Audit Checklist")
        period_label: Period label (e.g., "April 2026")
        form_url: Direct URL to the form
        qr_image_base64: Optional base64-encoded QR code image
        custom_message: Optional custom message to include

    Returns:
        dict with 'success', 'resend_id', and optionally 'error'
    """
    subject = f"EHC Form: {form_name} - {outlet_name} ({period_label})"

    html = render_form_email_html(
        to_name=to_name,
        outlet_name=outlet_name,
        form_name=form_name,
        period_label=period_label,
        form_url=form_url,
        qr_image_base64=qr_image_base64,
        custom_message=custom_message
    )

    return send_email(
        to_email=to_email,
        subject=subject,
        html=html,
        to_name=to_name
    )


def send_test_email(to_email: str, to_name: str) -> dict:
    """Send a test email to verify configuration.

    Args:
        to_email: Recipient email address
        to_name: Recipient name

    Returns:
        dict with 'success', 'resend_id', and optionally 'error'
    """
    subject = "RestauranTek EHC - Test Email"

    html = render_test_email_html(to_name=to_name)

    return send_email(
        to_email=to_email,
        subject=subject,
        html=html,
        to_name=to_name
    )


def render_form_email_html(
    to_name: str,
    outlet_name: str,
    form_name: str,
    period_label: str,
    form_url: str,
    qr_image_base64: Optional[str] = None,
    custom_message: Optional[str] = None
) -> str:
    """Render HTML email for form QR distribution.

    Uses inline CSS for email client compatibility.
    """
    current_year = datetime.now().year

    qr_section = ""
    if qr_image_base64:
        qr_section = f'''
        <div style="text-align: center; margin: 24px 0;">
            <img src="data:image/png;base64,{qr_image_base64}"
                 alt="QR Code"
                 style="width: 200px; height: 200px; border: 1px solid #e5e5e5; border-radius: 8px;"
            />
            <p style="font-size: 12px; color: #666; margin-top: 8px;">
                Scan with your phone camera
            </p>
        </div>
        '''

    custom_section = ""
    if custom_message:
        custom_section = f'''
        <div style="background: #f8f9fa; border-left: 3px solid #2d8653; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; color: #333; font-size: 14px;">{custom_message}</p>
        </div>
        '''

    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{form_name}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 520px; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

                    <!-- Header -->
                    <tr>
                        <td style="background: #1a1a1a; padding: 24px 32px; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; font-size: 20px; font-weight: 600; color: #ffffff;">
                                RestauranTek EHC
                            </h1>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 32px;">
                            <p style="margin: 0 0 16px; font-size: 16px; color: #333;">
                                Hi {to_name},
                            </p>

                            <p style="margin: 0 0 24px; font-size: 16px; color: #333; line-height: 1.5;">
                                Your <strong>{form_name}</strong> for <strong>{outlet_name}</strong> is ready for <strong>{period_label}</strong>.
                            </p>

                            {custom_section}

                            {qr_section}

                            <!-- CTA Button -->
                            <div style="text-align: center; margin: 28px 0;">
                                <a href="{form_url}"
                                   style="display: inline-block; padding: 14px 32px; background: #2d8653; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 600; border-radius: 6px;">
                                    Open Form
                                </a>
                            </div>

                            <p style="margin: 24px 0 0; font-size: 13px; color: #666; line-height: 1.5;">
                                You can also copy and paste this link into your browser:<br>
                                <a href="{form_url}" style="color: #2d8653; word-break: break-all;">{form_url}</a>
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 32px; background: #f8f9fa; border-top: 1px solid #e5e5e5; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0; font-size: 12px; color: #999; text-align: center;">
                                Sent by RestauranTek EHC<br>
                                &copy; {current_year} RestauranTek. All rights reserved.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
'''


def render_test_email_html(to_name: str) -> str:
    """Render HTML for test email."""
    current_year = datetime.now().year
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Email</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 520px; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

                    <!-- Header -->
                    <tr>
                        <td style="background: #1a1a1a; padding: 24px 32px; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; font-size: 20px; font-weight: 600; color: #ffffff;">
                                RestauranTek EHC
                            </h1>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 32px; text-align: center;">
                            <div style="width: 64px; height: 64px; margin: 0 auto 20px; background: #d4edda; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                <span style="font-size: 32px;">&#10003;</span>
                            </div>

                            <h2 style="margin: 0 0 16px; font-size: 24px; color: #2d8653;">
                                Email Configuration Working!
                            </h2>

                            <p style="margin: 0 0 8px; font-size: 16px; color: #333;">
                                Hi {to_name},
                            </p>

                            <p style="margin: 0 0 24px; font-size: 16px; color: #666; line-height: 1.5;">
                                This test email confirms that your RestauranTek EHC email integration is properly configured.
                            </p>

                            <div style="background: #f8f9fa; padding: 16px; border-radius: 6px; margin: 24px 0;">
                                <p style="margin: 0; font-size: 14px; color: #666;">
                                    <strong>Sent:</strong> {timestamp}
                                </p>
                            </div>

                            <p style="margin: 0; font-size: 14px; color: #666;">
                                You can now use the email features to distribute QR codes and form links to your team.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 32px; background: #f8f9fa; border-top: 1px solid #e5e5e5; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0; font-size: 12px; color: #999; text-align: center;">
                                Sent by RestauranTek EHC<br>
                                &copy; {current_year} RestauranTek. All rights reserved.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
'''
