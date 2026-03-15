"""Recording management API endpoints."""

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import aiosqlite

from config import RECORDINGS_DIR, AUDIO_SAMPLE_RATE
from database import get_db
from services.audio_analyzer import analyze_audio
from services.phoneme_tracker import text_to_phonemes
from services.achievement_engine import check_achievements, update_daily_activity
from models.schemas import (
    RecordingResponse, RecordingUploadResponse,
    RecordingReviewUpdate, BatchReviewUpdate, BatchDelete,
)

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

VALID_FLAGS = {"delete", "favorite", "needs_redo"}
VALID_GRADES = {"A", "B", "C", "D"}


def _row_to_response(r) -> RecordingResponse:
    """Convert a database row to a RecordingResponse."""
    return RecordingResponse(
        id=r["id"],
        item_number=r["item_number"],
        filename=r["filename"],
        text=r["text"],
        session_id=r["session_id"],
        category=r["category"],
        duration_seconds=r["duration_seconds"],
        quality_score=r["quality_score"],
        snr_db=r["snr_db"],
        has_clipping=bool(r["has_clipping"]),
        silence_ratio=r["silence_ratio"],
        rms_db=r["rms_db"],
        recorded_at=r["recorded_at"],
        flag=r["flag"],
        manual_quality_override=r["manual_quality_override"],
        review_note=r["review_note"],
        reviewed_at=r["reviewed_at"],
    )


def _convert_to_wav(audio_bytes: bytes) -> bytes:
    """Convert any audio format to 16-bit 44.1kHz mono WAV using ffmpeg.

    If the input is already a valid WAV, returns it unchanged.
    """
    if audio_bytes[:4] == b"RIFF":
        return audio_bytes

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        tmp_in_path = tmp_in.name

    tmp_out_path = tmp_in_path.replace(".webm", ".wav")
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", tmp_in_path,
                "-ar", str(AUDIO_SAMPLE_RATE),
                "-ac", "1",
                "-sample_fmt", "s16",
                tmp_out_path,
            ],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            raise ValueError(f"ffmpeg conversion failed: {result.stderr.decode()[-200:]}")

        with open(tmp_out_path, "rb") as f:
            return f.read()
    finally:
        Path(tmp_in_path).unlink(missing_ok=True)
        Path(tmp_out_path).unlink(missing_ok=True)


async def _get_next_item_number(db: aiosqlite.Connection) -> int:
    """Get the next available item number."""
    cursor = await db.execute("SELECT MAX(item_number) FROM recordings")
    row = await cursor.fetchone()
    max_num = row[0] if row and row[0] else 0
    return max(max_num + 1, 41)  # Start from 41 (40 existing samples)


@router.post("/upload", response_model=RecordingUploadResponse)
async def upload_recording(
    audio: UploadFile = File(...),
    text: str = Form(...),
    category: str = Form("phonetic"),
    session_id: Optional[int] = Form(None),
):
    """Upload a WAV recording with its transcript text."""
    audio_bytes = await audio.read()

    if len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio file is too small or empty.")

    try:
        audio_bytes = _convert_to_wav(audio_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis = analyze_audio(audio_bytes)

    db = await get_db()
    try:
        item_number = await _get_next_item_number(db)
        filename = f"item_{item_number:03d}.wav"

        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = RECORDINGS_DIR / filename
        with open(file_path, "wb") as f:
            f.write(audio_bytes)

        await db.execute(
            """INSERT INTO recordings
               (item_number, filename, text, session_id, category,
                duration_seconds, quality_score, snr_db, has_clipping,
                silence_ratio, rms_db, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item_number, filename, text, session_id, category,
                analysis.duration_seconds, analysis.quality_score,
                analysis.snr_db, analysis.has_clipping,
                analysis.silence_ratio, analysis.rms_db,
                datetime.utcnow().isoformat(),
            )
        )

        if session_id:
            await db.execute(
                "UPDATE sessions SET completed_count = completed_count + 1 WHERE id = ?",
                (session_id,)
            )

        phonemes = text_to_phonemes(text)
        for phoneme in phonemes:
            await db.execute(
                """INSERT INTO phoneme_coverage (phoneme, category, occurrence_count, recording_ids)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(phoneme) DO UPDATE SET
                   occurrence_count = occurrence_count + 1,
                   recording_ids = json_insert(recording_ids, '$[#]', ?)""",
                (phoneme, "", json.dumps([item_number]), item_number)
            )

        await update_daily_activity(db, analysis.quality_score)
        await db.commit()

        new_achievements = await check_achievements(db)

        cursor = await db.execute(
            "SELECT * FROM recordings WHERE item_number = ?", (item_number,)
        )
        row = await cursor.fetchone()

        return RecordingUploadResponse(
            recording=_row_to_response(row),
            analysis=analysis.to_dict(),
            new_achievements=new_achievements,
        )
    finally:
        await db.close()


@router.get("", response_model=list[RecordingResponse])
async def list_recordings(
    category: Optional[str] = None,
    quality: Optional[str] = None,
    flag: Optional[str] = None,
    reviewed: Optional[bool] = None,
    search: Optional[str] = None,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
):
    """List recordings with optional filters."""
    db = await get_db()
    try:
        query = "SELECT * FROM recordings WHERE 1=1"
        params: list = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if quality:
            query += " AND quality_score = ?"
            params.append(quality)
        if flag == "none":
            query += " AND flag IS NULL"
        elif flag:
            query += " AND flag = ?"
            params.append(flag)
        if reviewed is not None:
            if reviewed:
                query += " AND reviewed_at IS NOT NULL"
            else:
                query += " AND reviewed_at IS NULL"
        if search:
            query += " AND text LIKE ?"
            params.append(f"%{search}%")

        sort_map = {
            "newest": "recorded_at DESC",
            "oldest": "recorded_at ASC",
            "quality_asc": "quality_score ASC",
            "quality_desc": "quality_score DESC",
            "item_number": "item_number ASC",
        }
        query += f" ORDER BY {sort_map.get(sort, 'item_number DESC')}"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [_row_to_response(r) for r in rows]
    finally:
        await db.close()


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(recording_id: int):
    """Get a single recording by ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM recordings WHERE id = ?", (recording_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recording not found")
        return _row_to_response(row)
    finally:
        await db.close()


@router.patch("/{recording_id}/review", response_model=RecordingResponse)
async def review_recording(recording_id: int, update: RecordingReviewUpdate):
    """Update review metadata for a recording (flag, quality override, note)."""
    if update.flag is not None and update.flag not in VALID_FLAGS:
        raise HTTPException(status_code=400, detail=f"Invalid flag. Must be one of: {VALID_FLAGS}")
    if update.manual_quality_override is not None and update.manual_quality_override not in VALID_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade. Must be one of: {VALID_GRADES}")

    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM recordings WHERE id = ?", (recording_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recording not found")

        sets = []
        params: list = []
        for field in ["flag", "manual_quality_override", "review_note"]:
            val = getattr(update, field)
            if val is not None:
                sets.append(f"{field} = ?")
                params.append(val)
            elif val is None and field in update.model_fields_set:
                # Explicitly set to null to clear the field
                sets.append(f"{field} = NULL")

        sets.append("reviewed_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(recording_id)

        await db.execute(
            f"UPDATE recordings SET {', '.join(sets)} WHERE id = ?", params
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM recordings WHERE id = ?", (recording_id,))
        row = await cursor.fetchone()
        return _row_to_response(row)
    finally:
        await db.close()


@router.post("/batch-review")
async def batch_review(update: BatchReviewUpdate):
    """Apply the same review update to multiple recordings."""
    if not update.recording_ids:
        raise HTTPException(status_code=400, detail="No recording IDs provided")
    if update.flag is not None and update.flag not in VALID_FLAGS:
        raise HTTPException(status_code=400, detail=f"Invalid flag. Must be one of: {VALID_FLAGS}")
    if update.manual_quality_override is not None and update.manual_quality_override not in VALID_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade. Must be one of: {VALID_GRADES}")

    db = await get_db()
    try:
        sets = []
        params: list = []
        for field in ["flag", "manual_quality_override", "review_note"]:
            val = getattr(update, field)
            if val is not None:
                sets.append(f"{field} = ?")
                params.append(val)

        if not sets:
            raise HTTPException(status_code=400, detail="No fields to update")

        sets.append("reviewed_at = ?")
        params.append(datetime.utcnow().isoformat())

        placeholders = ",".join(["?"] * len(update.recording_ids))
        params.extend(update.recording_ids)

        await db.execute(
            f"UPDATE recordings SET {', '.join(sets)} WHERE id IN ({placeholders})",
            params,
        )
        await db.commit()
        return {"updated_count": len(update.recording_ids)}
    finally:
        await db.close()


@router.post("/batch-delete")
async def batch_delete(request: BatchDelete):
    """Delete multiple recordings and their audio files."""
    if not request.recording_ids:
        raise HTTPException(status_code=400, detail="No recording IDs provided")

    db = await get_db()
    try:
        placeholders = ",".join(["?"] * len(request.recording_ids))
        cursor = await db.execute(
            f"SELECT id, filename FROM recordings WHERE id IN ({placeholders})",
            request.recording_ids,
        )
        rows = await cursor.fetchall()

        for r in rows:
            file_path = RECORDINGS_DIR / r["filename"]
            if file_path.exists():
                file_path.unlink()

        await db.execute(
            f"DELETE FROM recordings WHERE id IN ({placeholders})",
            request.recording_ids,
        )
        await db.commit()
        return {"deleted_count": len(rows)}
    finally:
        await db.close()


@router.delete("/{recording_id}")
async def delete_recording(recording_id: int):
    """Delete a recording and its audio file."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT filename FROM recordings WHERE id = ?", (recording_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recording not found")

        file_path = RECORDINGS_DIR / row["filename"]
        if file_path.exists():
            file_path.unlink()

        await db.execute("DELETE FROM recordings WHERE id = ?", (recording_id,))
        await db.commit()
        return {"status": "deleted", "id": recording_id}
    finally:
        await db.close()
