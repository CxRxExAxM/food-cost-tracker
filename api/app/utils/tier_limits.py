"""
Tier-based usage limits for AI recipe parsing.

Credit Protection Policy:
- Only 'success' and 'partial' parses count toward monthly limits
- Failed parses don't consume credits (fair to users)
- Rate limiting prevents abuse (10 uploads/hour regardless of status)
"""

from typing import Optional


def get_monthly_parse_limit(tier: str) -> Optional[int]:
    """
    Get monthly AI parse limit for subscription tier.

    Args:
        tier: Subscription tier ('free', 'basic', 'pro', 'enterprise')

    Returns:
        Monthly limit or None for unlimited
    """
    limits = {
        'free': 10,
        'basic': 100,
        'pro': 100,
        'enterprise': None  # Unlimited
    }
    return limits.get(tier, 10)  # Default to free tier


def check_parse_limit(organization_id: int, conn) -> tuple[bool, dict]:
    """
    Check if organization can parse another recipe this month.

    Only counts 'success' and 'partial' status parses toward limit.
    Failed parses don't consume credits.

    Args:
        organization_id: Organization ID
        conn: Database connection

    Returns:
        (can_parse, usage_stats)
        - can_parse: True if within limit
        - usage_stats: Dict with tier, used, limit, remaining
    """

    # Get organization tier
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subscription_tier
        FROM organizations
        WHERE id = %s
    """, (organization_id,))

    org = cursor.fetchone()
    if not org:
        raise ValueError(f"Organization {organization_id} not found")

    tier = org['subscription_tier']
    limit = get_monthly_parse_limit(tier)

    # Count this month's usage (only successful/partial parses)
    cursor.execute("""
        SELECT COUNT(*) as used
        FROM ai_parse_usage
        WHERE organization_id = %s
        AND created_at >= date_trunc('month', CURRENT_DATE)
        AND parse_status IN ('success', 'partial')
    """, (organization_id,))

    usage = cursor.fetchone()['used']

    # Check if can parse
    can_parse = (limit is None) or (usage < limit)

    return can_parse, {
        'tier': tier,
        'used': usage,
        'limit': limit if limit is not None else 'unlimited',
        'remaining': (limit - usage) if limit is not None else 'unlimited'
    }


def check_rate_limit(organization_id: int, conn) -> tuple[bool, int]:
    """
    Check if organization has exceeded hourly upload rate limit.

    Counts ALL attempts (success, partial, failed) to prevent abuse.
    Limit: 10 attempts per hour.

    Args:
        organization_id: Organization ID
        conn: Database connection

    Returns:
        (within_limit, attempts_count)
        - within_limit: True if under 10 attempts/hour
        - attempts_count: Number of attempts in last hour
    """

    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as attempts
        FROM ai_parse_usage
        WHERE organization_id = %s
        AND created_at > NOW() - INTERVAL '1 hour'
    """, (organization_id,))

    attempts = cursor.fetchone()['attempts']
    return attempts < 10, attempts


def log_parse_attempt(
    organization_id: int,
    user_id: int,
    outlet_id: int,
    filename: str,
    file_type: str,
    parse_status: str,
    conn,
    recipe_id: Optional[int] = None,
    ingredients_count: Optional[int] = None,
    matched_count: Optional[int] = None,
    error_message: Optional[str] = None,
    parse_time_ms: Optional[int] = None
) -> int:
    """
    Log AI parse attempt to database.

    Args:
        organization_id: Organization ID
        user_id: User who initiated parse
        outlet_id: Outlet context
        filename: Original filename
        file_type: File extension ('docx', 'pdf', 'xlsx')
        parse_status: 'success', 'partial', or 'failed'
        conn: Database connection
        recipe_id: ID of created recipe (if successful)
        ingredients_count: Number of ingredients parsed
        matched_count: Number of auto-matched ingredients
        error_message: Error details if failed
        parse_time_ms: Processing time in milliseconds

    Returns:
        Parse usage record ID
    """

    if parse_status not in ('success', 'partial', 'failed'):
        raise ValueError(f"Invalid parse_status: {parse_status}")

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ai_parse_usage (
            organization_id, user_id, outlet_id, filename, file_type,
            parse_status, recipe_id, ingredients_count, matched_count,
            error_message, parse_time_ms
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        organization_id, user_id, outlet_id, filename, file_type,
        parse_status, recipe_id, ingredients_count, matched_count,
        error_message, parse_time_ms
    ))

    parse_id = cursor.fetchone()['id']
    conn.commit()

    return parse_id


def get_usage_stats(organization_id: int, conn) -> dict:
    """
    Get AI parse usage statistics for organization.

    Args:
        organization_id: Organization ID
        conn: Database connection

    Returns:
        Dict with usage stats and recent history
    """

    # Get current month usage
    can_parse, usage = check_parse_limit(organization_id, conn)

    # Get recent history (last 10 attempts)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            filename,
            parse_status,
            ingredients_count,
            created_at,
            error_message
        FROM ai_parse_usage
        WHERE organization_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (organization_id,))

    history = cursor.fetchall()

    return {
        'organization_id': organization_id,
        'tier': usage['tier'],
        'current_month': usage,
        'can_parse': can_parse,
        'recent_history': [
            {
                'filename': h['filename'],
                'status': h['parse_status'],
                'ingredients_count': h['ingredients_count'],
                'created_at': h['created_at'].isoformat() if h['created_at'] else None,
                'error': h['error_message']
            }
            for h in history
        ]
    }
