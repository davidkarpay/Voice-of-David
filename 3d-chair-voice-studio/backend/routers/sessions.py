"""Recording session management API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
import aiosqlite

from database import get_db
from models.schemas import SessionCreate, SessionResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
async def create_session(session: SessionCreate):
    """Start a new recording session."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO sessions (title, category, target_count) VALUES (?, ?, ?)",
            (session.title, session.category, session.target_count)
        )
        await db.commit()

        session_id = cursor.lastrowid
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()

        return SessionResponse(
            id=row["id"],
            title=row["title"],
            category=row["category"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            target_count=row["target_count"],
            completed_count=row["completed_count"],
        )
    finally:
        await db.close()


@router.put("/{session_id}/complete", response_model=SessionResponse)
async def complete_session(session_id: int):
    """Mark a recording session as complete."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")

        now = datetime.utcnow().isoformat()
        await db.execute(
            "UPDATE sessions SET completed_at = ? WHERE id = ?",
            (now, session_id)
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()

        return SessionResponse(
            id=row["id"],
            title=row["title"],
            category=row["category"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            target_count=row["target_count"],
            completed_count=row["completed_count"],
        )
    finally:
        await db.close()


@router.get("", response_model=list[SessionResponse])
async def list_sessions(limit: int = 20):
    """List recording sessions, most recent first."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()

        return [
            SessionResponse(
                id=r["id"],
                title=r["title"],
                category=r["category"],
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                target_count=r["target_count"],
                completed_count=r["completed_count"],
            )
            for r in rows
        ]
    finally:
        await db.close()


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int):
    """Get a single session by ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionResponse(
            id=row["id"],
            title=row["title"],
            category=row["category"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            target_count=row["target_count"],
            completed_count=row["completed_count"],
        )
    finally:
        await db.close()
