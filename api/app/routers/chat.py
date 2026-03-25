"""
Natural language chat endpoint for RestauranTek reporting.

Provides conversational interface to query forecasts, events, and potentials data.
"""

import os
import traceback
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import get_current_user
from ..database import get_db
from ..services.chat_agent import run_agent, get_or_create_session, save_message, get_recent_messages


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None


class ChatResponse(BaseModel):
    message: str
    render_type: str
    render_data: dict
    session_id: int


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a message to the NL reporting agent.

    The agent can answer questions about:
    - Forecasts and occupancy
    - Upcoming events and BEOs
    - Potentials and revenue projections
    - Period comparisons

    Returns structured data for rendering (text, charts, tables).
    """
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI chat service is not configured. Please set ANTHROPIC_API_KEY environment variable."
        )

    # Get organization ID from current user
    org_id = current_user["organization_id"]

    try:
        with get_db() as conn:
            # Get or create chat session
            session = get_or_create_session(
                conn=conn,
                session_id=request.session_id,
                org_id=org_id,
                user_id=current_user["id"]
            )

            # Save user message
            save_message(
                conn=conn,
                session_id=session["id"],
                role="user",
                content=request.message
            )

            # Get conversation history
            history = get_recent_messages(conn=conn, session_id=session["id"], limit=10)

            # Run agent
            result = run_agent(
                messages=history,
                org_id=org_id,
                conn=conn
            )

            # Save assistant response
            save_message(
                conn=conn,
                session_id=session["id"],
                role="assistant",
                content=result["text"],
                tool_calls=result.get("tool_calls"),
                result_type=result["render_type"],
                result_data=result.get("render_data")
            )

            return ChatResponse(
                message=result["text"],
                render_type=result["render_type"],
                render_data=result.get("render_data", {}),
                session_id=session["id"]
            )
    except Exception as e:
        print(f"Chat error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Chat error: {str(e)}"
        )


@router.get("/sessions")
async def list_sessions(
    current_user: dict = Depends(get_current_user),
):
    """List all chat sessions for the current user."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, created_at, updated_at
            FROM chat_sessions
            WHERE organization_id = %s AND user_id = %s
            ORDER BY updated_at DESC
            LIMIT 50
        """, (org_id, current_user["id"]))

        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "id": row[0],
                "title": row[1],
                "created_at": row[2].isoformat() if row[2] else None,
                "updated_at": row[3].isoformat() if row[3] else None
            })

        return {"sessions": sessions}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get all messages for a specific chat session."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        # Verify session belongs to user
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM chat_sessions
            WHERE id = %s AND organization_id = %s AND user_id = %s
        """, (session_id, org_id, current_user["id"]))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Session not found")

        messages = get_recent_messages(conn=conn, session_id=session_id, limit=100)
        return {"messages": messages}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete a chat session and all its messages."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify session belongs to user
        cursor.execute("""
            SELECT id FROM chat_sessions
            WHERE id = %s AND organization_id = %s AND user_id = %s
        """, (session_id, org_id, current_user["id"]))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Session not found")

        # Delete session (messages will cascade)
        cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
        conn.commit()

        return {"status": "deleted"}


@router.get("/health")
async def chat_health():
    """Check if chat service is available."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    return {
        "status": "configured" if api_key else "not_configured",
        "api_key_set": bool(api_key)
    }
