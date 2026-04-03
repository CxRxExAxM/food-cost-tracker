"""EHC Form PDF Generation Service

Generates PDFs for completed forms using ReportLab.
Templates match original EHC record formats.
"""

from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any, Optional
import base64

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas
from PIL import Image as PILImage


# ============================================
# Styles
# ============================================

def get_styles():
    """Get custom paragraph styles for EHC PDFs."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='EHCTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a1a1a')
    ))

    styles.add(ParagraphStyle(
        name='EHCSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#666666')
    ))

    styles.add(ParagraphStyle(
        name='EHCBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        leading=14
    ))

    styles.add(ParagraphStyle(
        name='EHCSmall',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#888888')
    ))

    styles.add(ParagraphStyle(
        name='EHCFooter',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#888888')
    ))

    return styles


# ============================================
# Helper Functions
# ============================================

def decode_signature_image(signature_data: str, max_width: float = 1.5*inch, max_height: float = 0.5*inch) -> Optional[Image]:
    """Convert base64 signature to ReportLab Image with constrained size."""
    if not signature_data:
        return None

    try:
        # Handle both with and without data URI prefix
        if signature_data.startswith('data:'):
            # Extract base64 part after comma
            signature_data = signature_data.split(',', 1)[1]

        # Decode base64
        img_bytes = base64.b64decode(signature_data)

        # Open with PIL to get dimensions
        pil_img = PILImage.open(BytesIO(img_bytes))
        orig_width, orig_height = pil_img.size

        # Calculate scale to fit within bounds while preserving aspect ratio
        width_ratio = max_width / orig_width
        height_ratio = max_height / orig_height
        scale = min(width_ratio, height_ratio)

        final_width = orig_width * scale
        final_height = orig_height * scale

        # Create ReportLab Image
        img_buffer = BytesIO(img_bytes)
        return Image(img_buffer, width=final_width, height=final_height)

    except Exception as e:
        print(f"Error processing signature: {e}")
        return None


def format_date(dt) -> str:
    """Format datetime for display."""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    if isinstance(dt, datetime):
        return dt.strftime('%m/%d/%Y %H:%M')
    return str(dt) if dt else ''


def format_date_short(dt) -> str:
    """Format datetime as short date only."""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    if isinstance(dt, datetime):
        return dt.strftime('%m/%d/%Y')
    return str(dt) if dt else ''


# ============================================
# Record 11: Staff Declaration Summary
# ============================================

def generate_record_11_pdf(
    title: str,
    property_name: str,
    cycle_year: int,
    responses: List[Dict[str, Any]],
    expected_count: Optional[int] = None
) -> bytes:
    """
    Generate PDF for Record 11 (Staff Food Safety Declaration).

    Format: Summary table with Name | Date | Signature columns.
    Auto-paginates for large response sets.
    """
    buffer = BytesIO()
    styles = get_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    elements = []

    # Header
    elements.append(Paragraph(f"{property_name}", styles['EHCSubtitle']))
    elements.append(Paragraph("Record 11 — Staff Food Safety Declaration", styles['EHCTitle']))
    elements.append(Paragraph(f"EHC Audit Cycle {cycle_year}", styles['EHCSubtitle']))
    elements.append(Spacer(1, 0.25*inch))

    # Summary text
    total = len(responses)
    expected_text = f" of {expected_count} expected" if expected_count else ""
    elements.append(Paragraph(
        f"The following {total} staff members{expected_text} have read and acknowledged "
        f"the Food Safety Declaration for the {cycle_year} EHC audit cycle.",
        styles['EHCBody']
    ))
    elements.append(Spacer(1, 0.25*inch))

    # Build table data
    table_data = [['Name', 'Date', 'Signature']]

    for resp in responses:
        name = resp.get('respondent_name', '')
        date = format_date(resp.get('submitted_at', ''))

        # Get signature image
        sig_data = resp.get('signature_data', '')
        sig_img = decode_signature_image(sig_data)

        table_data.append([
            Paragraph(name, styles['EHCBody']),
            Paragraph(date, styles['EHCSmall']),
            sig_img if sig_img else ''
        ])

    # Create table
    col_widths = [2.5*inch, 1.5*inch, 2.5*inch]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),

        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Alternating row colors
        *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafafa'))
          for i in range(2, len(table_data), 2)]
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))

    # Footer
    generated_at = datetime.now().strftime('%B %d, %Y at %H:%M')
    elements.append(Paragraph(
        f"Generated: {generated_at} | Total Responses: {total} | "
        f"Document: Record 11 v3.0",
        styles['EHCFooter']
    ))

    doc.build(elements)
    return buffer.getvalue()


# ============================================
# Record 35: Food Safety Team Record
# ============================================

def generate_record_35_pdf(
    title: str,
    property_name: str,
    cycle_year: int,
    team_members: List[Dict[str, Any]],
    responses: List[Dict[str, Any]]
) -> bytes:
    """
    Generate PDF for Record 35 (Food Safety Team Record).

    Format matches original template:
    Date Approved | Name | Position | Department | Signature
    """
    buffer = BytesIO()
    styles = get_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    elements = []

    # Header
    elements.append(Paragraph(f"{property_name}", styles['EHCSubtitle']))
    elements.append(Paragraph("Record 35 — Food Safety Team Record", styles['EHCTitle']))
    elements.append(Paragraph(f"EHC Audit Cycle {cycle_year}", styles['EHCSubtitle']))
    elements.append(Spacer(1, 0.25*inch))

    # Intro text
    elements.append(Paragraph(
        "The individuals named below are designated members of the Food Safety Team "
        "for this property and have been trained in HACCP principles and food safety management.",
        styles['EHCBody']
    ))
    elements.append(Spacer(1, 0.25*inch))

    # Build response lookup by name (case-insensitive)
    response_lookup = {}
    for resp in responses:
        name_key = resp.get('respondent_name', '').strip().lower()
        response_lookup[name_key] = resp

    # Build table data
    table_data = [['Date Approved', 'Name', 'Position', 'Department', 'Signature']]

    for member in team_members:
        name = member.get('name', '')
        position = member.get('position', '')
        department = member.get('department', '')
        date_approved = member.get('date_approved', '')

        # Look up signature from responses
        name_key = name.strip().lower()
        resp = response_lookup.get(name_key, {})
        sig_data = resp.get('signature_data', '')
        sig_img = decode_signature_image(sig_data, max_width=1.2*inch, max_height=0.4*inch)

        table_data.append([
            Paragraph(format_date_short(date_approved), styles['EHCSmall']),
            Paragraph(name, styles['EHCBody']),
            Paragraph(position, styles['EHCSmall']),
            Paragraph(department, styles['EHCSmall']),
            sig_img if sig_img else Paragraph('—', styles['EHCSmall'])
        ])

    # Create table
    col_widths = [1.0*inch, 1.8*inch, 1.5*inch, 1.3*inch, 1.4*inch]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),

        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Alternating row colors
        *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafafa'))
          for i in range(2, len(table_data), 2)]
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))

    # Footer
    signed_count = sum(1 for m in team_members
                      if m.get('name', '').strip().lower() in response_lookup)
    total_count = len(team_members)
    generated_at = datetime.now().strftime('%B %d, %Y at %H:%M')

    elements.append(Paragraph(
        f"Generated: {generated_at} | Team Members: {signed_count}/{total_count} signed | "
        f"Document: Record 35 v3.0",
        styles['EHCFooter']
    ))

    doc.build(elements)
    return buffer.getvalue()


# ============================================
# Generic Table Sign-off PDF
# ============================================

def generate_table_signoff_pdf(
    title: str,
    property_name: str,
    cycle_year: int,
    columns: List[Dict[str, Any]],
    rows: List[Dict[str, Any]],
    responses: List[Dict[str, Any]],
    intro_text: Optional[str] = None
) -> bytes:
    """
    Generate PDF for generic table sign-off forms.

    Uses dynamic columns from config to build the table.
    Matches responses to rows by name column.
    """
    buffer = BytesIO()
    styles = get_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    elements = []

    # Header
    elements.append(Paragraph(f"{property_name}", styles['EHCSubtitle']))
    elements.append(Paragraph(title, styles['EHCTitle']))
    elements.append(Paragraph(f"EHC Audit Cycle {cycle_year}", styles['EHCSubtitle']))
    elements.append(Spacer(1, 0.25*inch))

    # Intro text if provided
    if intro_text:
        elements.append(Paragraph(intro_text, styles['EHCBody']))
        elements.append(Spacer(1, 0.25*inch))

    # Build response lookup by name (case-insensitive)
    response_lookup = {}
    for resp in responses:
        name_key = resp.get('respondent_name', '').strip().lower()
        response_lookup[name_key] = resp

    # Build table headers from columns
    non_sig_columns = [c for c in columns if c.get('type') != 'signature']
    header_row = [c.get('label', c.get('key', '')) for c in non_sig_columns]
    header_row.append('Signature')  # Always add signature column at end

    table_data = [header_row]

    # Determine if we have pre-filled rows or use responses directly
    if rows and len(rows) > 0:
        # Pre-filled rows mode: show all rows, match signatures
        for row in rows:
            row_data = []
            name_value = ''

            for col in non_sig_columns:
                key = col.get('key', '')
                value = row.get(key, '')
                row_data.append(Paragraph(str(value), styles['EHCBody']))

                # Track name for signature lookup
                if col.get('type') == 'text' and key in ['name', 'col_0']:
                    name_value = value

            # Look up signature
            name_key = name_value.strip().lower() if name_value else ''
            resp = response_lookup.get(name_key, {})
            sig_data = resp.get('signature_data', '')
            sig_img = decode_signature_image(sig_data, max_width=1.2*inch, max_height=0.4*inch)

            row_data.append(sig_img if sig_img else Paragraph('—', styles['EHCSmall']))
            table_data.append(row_data)
    else:
        # No pre-filled rows: show responses directly
        for resp in responses:
            row_data = []
            resp_data = resp.get('response_data', {}) or {}
            if isinstance(resp_data, str):
                import json
                resp_data = json.loads(resp_data)
            row_values = resp_data.get('row_data', {})

            for col in non_sig_columns:
                key = col.get('key', '')
                # Try row_data first, then respondent_name for name column
                value = row_values.get(key, '')
                if not value and key in ['name', 'col_0']:
                    value = resp.get('respondent_name', '')
                row_data.append(Paragraph(str(value), styles['EHCBody']))

            # Add signature
            sig_data = resp.get('signature_data', '')
            sig_img = decode_signature_image(sig_data, max_width=1.2*inch, max_height=0.4*inch)
            row_data.append(sig_img if sig_img else Paragraph('—', styles['EHCSmall']))

            table_data.append(row_data)

    # Calculate column widths dynamically
    num_cols = len(header_row)
    available_width = 7 * inch  # Letter width minus margins
    sig_col_width = 1.5 * inch
    remaining_width = available_width - sig_col_width
    other_col_width = remaining_width / (num_cols - 1) if num_cols > 1 else remaining_width

    col_widths = [other_col_width] * (num_cols - 1) + [sig_col_width]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),

        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Alternating row colors
        *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafafa'))
          for i in range(2, len(table_data), 2)]
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))

    # Footer
    signed_count = len(responses)
    total_rows = len(rows) if rows else signed_count
    generated_at = datetime.now().strftime('%B %d, %Y at %H:%M')

    elements.append(Paragraph(
        f"Generated: {generated_at} | Signatures: {signed_count}/{total_rows} | "
        f"Document: Table Sign-off",
        styles['EHCFooter']
    ))

    doc.build(elements)
    return buffer.getvalue()


# ============================================
# Flyer PDF with QR Code
# ============================================

def generate_flyer_pdf(
    title: str,
    property_name: str,
    cycle_year: int,
    qr_code_base64: str,
    form_type: str = 'staff_declaration',
    instructions: Optional[str] = None
) -> bytes:
    """
    Generate printable flyer with QR code for posting.

    Large QR code, clear instructions, property branding.
    """
    buffer = BytesIO()
    styles = get_styles()

    # Custom styles for flyer
    styles.add(ParagraphStyle(
        name='FlyerTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a1a1a')
    ))

    styles.add(ParagraphStyle(
        name='FlyerSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#666666')
    ))

    styles.add(ParagraphStyle(
        name='FlyerInstructions',
        parent=styles['Normal'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=20,
        alignment=TA_CENTER,
        leading=22
    ))

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1*inch,
        leftMargin=1*inch,
        topMargin=1*inch,
        bottomMargin=1*inch
    )

    elements = []

    # Header
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(property_name, styles['FlyerSubtitle']))
    elements.append(Paragraph(title, styles['FlyerTitle']))
    elements.append(Paragraph(f"EHC {cycle_year}", styles['FlyerSubtitle']))
    elements.append(Spacer(1, 0.5*inch))

    # QR Code (centered, large)
    if qr_code_base64:
        try:
            qr_bytes = base64.b64decode(qr_code_base64)
            qr_buffer = BytesIO(qr_bytes)
            qr_img = Image(qr_buffer, width=3*inch, height=3*inch)

            # Center the QR code using a table
            qr_table = Table([[qr_img]], colWidths=[6.5*inch])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(qr_table)
        except Exception as e:
            print(f"Error adding QR code to flyer: {e}")

    elements.append(Spacer(1, 0.5*inch))

    # Instructions
    default_instructions = "Scan with your phone camera to complete this form"
    elements.append(Paragraph(
        instructions or default_instructions,
        styles['FlyerInstructions']
    ))

    # Form type specific additional text
    if form_type == 'staff_declaration':
        elements.append(Paragraph(
            "Please read the full declaration and provide your signature to confirm acknowledgment.",
            styles['EHCBody']
        ))
    elif form_type == 'team_roster':
        elements.append(Paragraph(
            "Food Safety Team members: Find your name and sign to confirm your role.",
            styles['EHCBody']
        ))

    elements.append(Spacer(1, 1*inch))

    # Footer
    elements.append(Paragraph(
        f"Environmental Health Compliance | {cycle_year} Audit Cycle",
        styles['EHCFooter']
    ))

    doc.build(elements)
    return buffer.getvalue()
