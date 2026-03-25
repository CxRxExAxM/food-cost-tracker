"""
Chat agent service for natural language reporting.

Uses Claude Haiku to classify questions and extract parameters,
then executes queries against potentials data.
"""

import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import anthropic

# Import shared potentials functions
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from routers.potentials import build_daily_summary


# Tool definitions for Claude
TOOLS = [
    {
        "name": "get_forecast_summary",
        "description": "Get forecast metrics summary for a date range. Returns occupancy, ADR, rooms, and other hotel metrics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                }
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "get_upcoming_events",
        "description": "Get upcoming events/BEOs with optional filtering by date range, category, or minimum covers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category: breakfast, lunch, dinner, reception, meeting, other",
                    "enum": ["breakfast", "lunch", "dinner", "reception", "meeting", "other"]
                },
                "min_covers": {
                    "type": "integer",
                    "description": "Minimum number of attendees/covers"
                }
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "get_event_detail",
        "description": "Get detailed information about a specific event by ID or name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_identifier": {
                    "type": "string",
                    "description": "Event ID number or event name to search for"
                }
            },
            "required": ["event_identifier"]
        }
    },
    {
        "name": "get_daily_summary",
        "description": "Get combined forecast and events summary by day for a date range. Returns occupancy, rooms, IHG (adults_children), kids, leisure_guests, catered covers by meal period (breakfast/lunch/dinner/reception), ALOO, and event counts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                }
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "compare_periods",
        "description": "Compare metrics between two time periods (e.g., this month vs last month).",
        "input_schema": {
            "type": "object",
            "properties": {
                "period1_start": {
                    "type": "string",
                    "description": "Period 1 start date in YYYY-MM-DD format"
                },
                "period1_end": {
                    "type": "string",
                    "description": "Period 1 end date in YYYY-MM-DD format"
                },
                "period2_start": {
                    "type": "string",
                    "description": "Period 2 start date in YYYY-MM-DD format"
                },
                "period2_end": {
                    "type": "string",
                    "description": "Period 2 end date in YYYY-MM-DD format"
                }
            },
            "required": ["period1_start", "period1_end", "period2_start", "period2_end"]
        }
    },
    {
        "name": "get_groups_summary",
        "description": "Get summary of groups and their room blocks for a date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                }
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "get_high_aloo_periods",
        "description": "Identify when large groups have high ALOO (At Leisure On Own) and might flood outlets. Shows which groups are not scheduled for catered meals and will likely eat at outlets instead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "min_group_aloo": {
                    "type": "integer",
                    "description": "Minimum group ALOO count to flag (default 30)"
                },
                "min_rooms": {
                    "type": "integer",
                    "description": "Minimum rooms for a group to be considered (default 20)"
                }
            },
            "required": ["start_date", "end_date"]
        }
    }
]


def build_system_prompt(org_id: int) -> str:
    """Build system prompt with current context."""
    today = date.today().isoformat()

    return f"""You are a food & beverage reporting assistant for a luxury hotel property.
You have tools to query forecast data, events/BEOs, and potentials.

When a user asks a question:
1. Pick the right tool(s) and fill parameters
2. Use today's date ({today}) for relative references like "this week", "yesterday", "next month"
3. For date ranges:
   - "this week" = current Monday to Sunday
   - "this month" = first to last day of current month
   - "next week/month" = following week/month
4. For holiday questions, use common knowledge of US holidays
5. Return data in the most useful format

FORMATTING RULES:
- Use bullet points (•) instead of paragraphs
- Keep responses concise and scannable
- Use outline format with clear hierarchy
- Only use tables when the render_type is "table"
- Avoid verbose explanations

Be direct and focus on answering the specific question asked.
"""


def run_agent(messages: List[Dict], org_id: int, conn) -> Dict:
    """
    Run the chat agent loop.

    Args:
        messages: Conversation history
        org_id: Organization ID for data queries
        conn: Database connection

    Returns:
        Dict with text, render_type, render_data, and tool_calls
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = build_system_prompt(org_id)

    # Convert messages to Claude format
    claude_messages = []
    for msg in messages:
        claude_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Call Claude with tools
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        temperature=0,
        system=system_prompt,
        messages=claude_messages,
        tools=TOOLS
    )

    # Handle tool use
    tool_calls_made = []

    if response.stop_reason == "tool_use":
        # Execute tools
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id

                # Execute tool
                tool_result = execute_tool(tool_name, tool_input, org_id, conn)
                tool_calls_made.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": tool_result
                })

                # Continue conversation with tool result
                claude_messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                claude_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(tool_result)
                    }]
                })

        # Get final response after tool execution
        final_response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            temperature=0,
            system=system_prompt,
            messages=claude_messages
        )

        # Extract text response
        text_content = ""
        for block in final_response.content:
            if hasattr(block, "text"):
                text_content += block.text

        # Determine render type and data from tool results
        render_type, render_data = format_response(tool_calls_made)

        return {
            "text": text_content,
            "render_type": render_type,
            "render_data": render_data,
            "tool_calls": tool_calls_made
        }
    else:
        # No tool use - just return text
        text_content = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_content += block.text

        return {
            "text": text_content,
            "render_type": "text",
            "render_data": {},
            "tool_calls": []
        }


def execute_tool(tool_name: str, tool_input: Dict, org_id: int, conn) -> Dict:
    """Execute a tool and return results."""
    if tool_name == "get_forecast_summary":
        return get_forecast_summary(conn, org_id, tool_input["start_date"], tool_input["end_date"])
    elif tool_name == "get_upcoming_events":
        return get_upcoming_events(
            conn, org_id,
            tool_input["start_date"],
            tool_input["end_date"],
            tool_input.get("category"),
            tool_input.get("min_covers")
        )
    elif tool_name == "get_event_detail":
        return get_event_detail(conn, org_id, tool_input["event_identifier"])
    elif tool_name == "get_daily_summary":
        return get_daily_summary(conn, org_id, tool_input["start_date"], tool_input["end_date"])
    elif tool_name == "compare_periods":
        return compare_periods(
            conn, org_id,
            tool_input["period1_start"], tool_input["period1_end"],
            tool_input["period2_start"], tool_input["period2_end"]
        )
    elif tool_name == "get_groups_summary":
        return get_groups_summary(conn, org_id, tool_input["start_date"], tool_input["end_date"])
    elif tool_name == "get_high_aloo_periods":
        return get_high_aloo_periods(
            conn, org_id,
            tool_input["start_date"],
            tool_input["end_date"],
            tool_input.get("min_group_aloo", 30),
            tool_input.get("min_rooms", 20)
        )
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def format_response(tool_calls: List[Dict]) -> tuple[str, Dict]:
    """
    Determine render type and format data based on tool calls.

    Returns (render_type, render_data)
    """
    if not tool_calls:
        return "text", {}

    # For now, default to table for data results
    # TODO: Add logic to determine chart vs table based on data shape
    first_result = tool_calls[0]["result"]

    if "events" in first_result:
        # Event list - use table
        events = first_result["events"]
        if events:
            return "table", {
                "columns": ["Date", "Event", "Category", "Attendees", "Venue"],
                "rows": [[
                    e.get("date", ""),
                    e.get("event_name", ""),
                    e.get("category", ""),
                    e.get("attendees", ""),
                    e.get("venue", "")
                ] for e in events]
            }

    if "daily_data" in first_result:
        # Daily summary - could be chart or table
        daily_data = first_result["daily_data"]
        if daily_data:
            return "table", {
                "columns": ["Date", "Occupancy %", "Rooms", "Catered Covers"],
                "rows": [[
                    d.get("date", ""),
                    f"{d.get('occupancy_pct', 0):.1f}%",
                    d.get("occupied_rooms", 0),
                    d.get("total_catered_covers", 0)
                ] for d in daily_data]
            }

    # Default to text
    return "text", {}


# Tool implementation functions

def get_forecast_summary(conn, org_id: int, start_date: str, end_date: str) -> Dict:
    """Get forecast metrics summary."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            metric_name,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value
        FROM potentials_forecast_metrics
        WHERE organization_id = %s
            AND date >= %s AND date <= %s
        GROUP BY metric_name
    """, (org_id, start_date, end_date))

    metrics = {}
    for row in cursor.fetchall():
        metrics[row["metric_name"]] = {
            "avg": float(row["avg_value"]) if row["avg_value"] else 0,
            "min": float(row["min_value"]) if row["min_value"] else 0,
            "max": float(row["max_value"]) if row["max_value"] else 0
        }

    return {"metrics": metrics, "start_date": start_date, "end_date": end_date}


def get_upcoming_events(conn, org_id: int, start_date: str, end_date: str,
                       category: Optional[str] = None, min_covers: Optional[int] = None) -> Dict:
    """Get upcoming events with optional filtering."""
    cursor = conn.cursor()

    query = """
        SELECT event_id, date, booking_name, event_name, category,
               venue, time, attendees, gtd, notes
        FROM potentials_events
        WHERE organization_id = %s
            AND date >= %s AND date <= %s
    """
    params = [org_id, start_date, end_date]

    if category:
        query += " AND category = %s"
        params.append(category)

    if min_covers:
        query += " AND attendees >= %s"
        params.append(min_covers)

    query += " ORDER BY date, time"

    cursor.execute(query, params)

    events = []
    for row in cursor.fetchall():
        events.append({
            "event_id": row["event_id"],
            "date": row["date"].isoformat() if row["date"] else None,
            "booking_name": row["booking_name"],
            "event_name": row["event_name"],
            "category": row["category"],
            "venue": row["venue"],
            "time": row["time"],
            "attendees": row["attendees"],
            "gtd": row["gtd"],
            "notes": row["notes"]
        })

    return {"events": events, "count": len(events)}


def get_event_detail(conn, org_id: int, event_identifier: str) -> Dict:
    """Get detailed info about a specific event."""
    cursor = conn.cursor()

    # Try as event_id first (integer)
    try:
        event_id = int(event_identifier)
        cursor.execute("""
            SELECT event_id, date, booking_name, event_name, category,
                   venue, time, attendees, gtd, notes, event_type
            FROM potentials_events
            WHERE organization_id = %s AND event_id = %s
        """, (org_id, event_id))
    except ValueError:
        # Search by name
        cursor.execute("""
            SELECT event_id, date, booking_name, event_name, category,
                   venue, time, attendees, gtd, notes, event_type
            FROM potentials_events
            WHERE organization_id = %s
                AND (event_name ILIKE %s OR booking_name ILIKE %s)
            LIMIT 1
        """, (org_id, f"%{event_identifier}%", f"%{event_identifier}%"))

    row = cursor.fetchone()
    if not row:
        return {"error": "Event not found"}

    return {
        "event_id": row["event_id"],
        "date": row["date"].isoformat() if row["date"] else None,
        "booking_name": row["booking_name"],
        "event_name": row["event_name"],
        "category": row["category"],
        "venue": row["venue"],
        "time": row["time"],
        "attendees": row["attendees"],
        "gtd": row["gtd"],
        "notes": row["notes"],
        "event_type": row["event_type"]
    }


def get_daily_summary(conn, org_id: int, start_date: str, end_date: str) -> Dict:
    """Get daily summary combining forecast and events.

    Uses shared build_daily_summary function to ensure consistency
    with REST API and includes all fields: occupancy, IHG, kids,
    leisure_guests, catered meals by period, ALOO, etc.
    """
    cursor = conn.cursor()
    daily_data = build_daily_summary(cursor, org_id, start_date, end_date)
    return {"daily_data": daily_data}


def compare_periods(conn, org_id: int, p1_start: str, p1_end: str,
                   p2_start: str, p2_end: str) -> Dict:
    """Compare metrics between two periods."""
    period1 = get_forecast_summary(conn, org_id, p1_start, p1_end)
    period2 = get_forecast_summary(conn, org_id, p2_start, p2_end)

    # Get event counts
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as event_count, SUM(attendees) as total_attendees
        FROM potentials_events
        WHERE organization_id = %s AND date >= %s AND date <= %s
    """, (org_id, p1_start, p1_end))
    p1_events = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) as event_count, SUM(attendees) as total_attendees
        FROM potentials_events
        WHERE organization_id = %s AND date >= %s AND date <= %s
    """, (org_id, p2_start, p2_end))
    p2_events = cursor.fetchone()

    return {
        "period1": {
            "start": p1_start,
            "end": p1_end,
            "metrics": period1["metrics"],
            "event_count": p1_events["event_count"],
            "total_covers": p1_events["total_attendees"] or 0
        },
        "period2": {
            "start": p2_start,
            "end": p2_end,
            "metrics": period2["metrics"],
            "event_count": p2_events["event_count"],
            "total_covers": p2_events["total_attendees"] or 0
        }
    }


def get_groups_summary(conn, org_id: int, start_date: str, end_date: str) -> Dict:
    """Get summary of group room blocks."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            block_name,
            SUM(rooms) as total_rooms,
            SUM(arrivals) as total_arrivals,
            SUM(departures) as total_departures,
            MIN(date) as first_date,
            MAX(date) as last_date
        FROM potentials_group_rooms
        WHERE organization_id = %s
            AND date >= %s AND date <= %s
        GROUP BY block_name
        ORDER BY total_rooms DESC
    """, (org_id, start_date, end_date))

    groups = []
    for row in cursor.fetchall():
        groups.append({
            "block_name": row["block_name"],
            "total_rooms": row["total_rooms"] or 0,
            "total_arrivals": row["total_arrivals"] or 0,
            "total_departures": row["total_departures"] or 0,
            "first_date": row["first_date"].isoformat() if row["first_date"] else None,
            "last_date": row["last_date"].isoformat() if row["last_date"] else None
        })

    return {"groups": groups, "count": len(groups)}


def get_high_aloo_periods(conn, org_id: int, start_date: str, end_date: str,
                         min_group_aloo: int = 30, min_rooms: int = 20) -> Dict:
    """
    Identify when large groups have high ALOO and might overwhelm outlets.

    Calculates group-specific ALOO (guests not scheduled for catered events)
    for each meal period and flags potential outlet capacity issues.
    """
    cursor = conn.cursor()

    # Get group room data by date
    cursor.execute("""
        SELECT date, block_name, rooms
        FROM potentials_group_rooms
        WHERE organization_id = %s
            AND date >= %s AND date <= %s
            AND rooms >= %s
        ORDER BY date, block_name
    """, (org_id, start_date, end_date, min_rooms))

    group_rooms_data = {}
    for row in cursor.fetchall():
        date_key = row["date"].isoformat()
        if date_key not in group_rooms_data:
            group_rooms_data[date_key] = {}
        group_rooms_data[date_key][row["block_name"]] = row["rooms"]

    # Get scheduled events by group and meal category
    cursor.execute("""
        SELECT date, booking_name, category, SUM(attendees) as total_covers
        FROM potentials_events
        WHERE organization_id = %s
            AND date >= %s AND date <= %s
            AND category IN ('breakfast', 'lunch', 'dinner', 'reception')
        GROUP BY date, booking_name, category
    """, (org_id, start_date, end_date))

    scheduled_covers = {}
    for row in cursor.fetchall():
        date_key = row["date"].isoformat()
        group_key = (date_key, row["booking_name"], row["category"])
        scheduled_covers[group_key] = row["total_covers"] or 0

    # Calculate ALOO for each group/date/meal combination
    high_aloo_periods = []

    for date_str, groups in group_rooms_data.items():
        for group_name, rooms in groups.items():
            # Estimate group size: rooms × 2.5 average guests per room
            estimated_group_size = int(rooms * 2.5)

            # Check each meal period
            for meal in ['breakfast', 'lunch', 'dinner', 'reception']:
                group_key = (date_str, group_name, meal)
                scheduled = scheduled_covers.get(group_key, 0)
                aloo = estimated_group_size - scheduled

                # Flag if ALOO exceeds threshold
                if aloo >= min_group_aloo:
                    high_aloo_periods.append({
                        "date": date_str,
                        "group": group_name,
                        "meal_period": meal,
                        "rooms": rooms,
                        "estimated_group_size": estimated_group_size,
                        "scheduled_covers": scheduled,
                        "aloo": aloo,
                        "pct_aloo": round((aloo / estimated_group_size) * 100, 1) if estimated_group_size > 0 else 0
                    })

    # Sort by ALOO count descending
    high_aloo_periods.sort(key=lambda x: x["aloo"], reverse=True)

    return {
        "high_aloo_periods": high_aloo_periods,
        "count": len(high_aloo_periods),
        "thresholds": {
            "min_group_aloo": min_group_aloo,
            "min_rooms": min_rooms
        }
    }


# Session and message management

def get_or_create_session(conn, session_id: Optional[int], org_id: int, user_id: int) -> Dict:
    """Get existing session or create new one."""
    cursor = conn.cursor()

    if session_id:
        cursor.execute("""
            SELECT id, title, created_at, updated_at
            FROM chat_sessions
            WHERE id = %s AND organization_id = %s AND user_id = %s
        """, (session_id, org_id, user_id))
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    # Create new session
    cursor.execute("""
        INSERT INTO chat_sessions (organization_id, user_id, title)
        VALUES (%s, %s, %s)
        RETURNING id, title, created_at, updated_at
    """, (org_id, user_id, "New Chat"))

    row = cursor.fetchone()
    conn.commit()

    return {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }


def save_message(conn, session_id: int, role: str, content: str,
                tool_calls: Optional[List] = None, result_type: Optional[str] = None,
                result_data: Optional[Dict] = None):
    """Save a message to the database."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages
        (session_id, role, content, tool_calls, result_type, result_data)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        session_id, role, content,
        json.dumps(tool_calls) if tool_calls else None,
        result_type,
        json.dumps(result_data) if result_data else None
    ))

    # Update session timestamp
    cursor.execute("""
        UPDATE chat_sessions
        SET updated_at = NOW()
        WHERE id = %s
    """, (session_id,))

    conn.commit()


def get_recent_messages(conn, session_id: int, limit: int = 10) -> List[Dict]:
    """Get recent messages for a session."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content, created_at
        FROM chat_messages
        WHERE session_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (session_id, limit))

    messages = []
    for row in reversed(cursor.fetchall()):
        messages.append({
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None
        })

    return messages
