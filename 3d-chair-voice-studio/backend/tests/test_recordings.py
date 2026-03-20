"""
test_recordings.py

Tests for the recordings API, focusing on deletion side-effect reversal.
Verifies that deleting a recording correctly restores session counts,
phoneme coverage, and prompt availability.

Uses an in-memory SQLite database and temporary directories to avoid
touching the real voice studio data.
"""

import io
import struct
import pytest
import pytest_asyncio
import aiosqlite
from pathlib import Path
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient


def _make_wav_bytes(duration_seconds: float = 1.0, sample_rate: int = 44100) -> bytes:
    """Generate a minimal valid WAV file (silence) for testing."""
    num_samples = int(sample_rate * duration_seconds)
    data_size = num_samples * 2  # 16-bit mono
    buf = io.BytesIO()
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # chunk size
    buf.write(struct.pack("<H", 1))   # PCM
    buf.write(struct.pack("<H", 1))   # mono
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * 2))  # byte rate
    buf.write(struct.pack("<H", 2))   # block align
    buf.write(struct.pack("<H", 16))  # bits per sample
    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(b"\x00" * data_size)
    return buf.getvalue()


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create temporary data and recordings directories."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    recordings_dir = data_dir / "recordings"
    recordings_dir.mkdir()
    return data_dir, recordings_dir


@pytest.fixture
def app(tmp_data_dir):
    """Create a FastAPI test app with patched config pointing to temp dirs."""
    data_dir, recordings_dir = tmp_data_dir
    db_path = data_dir / "test.db"

    with patch("config.DATA_DIR", data_dir), \
         patch("config.DB_PATH", db_path), \
         patch("config.RECORDINGS_DIR", recordings_dir), \
         patch("database.DATA_DIR", data_dir), \
         patch("database.DB_PATH", db_path), \
         patch("routers.recordings.RECORDINGS_DIR", recordings_dir):

        from main import app as fastapi_app
        yield fastapi_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def db(tmp_data_dir):
    """Create and initialize a test database."""
    data_dir, _ = tmp_data_dir
    db_path = data_dir / "test.db"

    with patch("database.DATA_DIR", data_dir), \
         patch("database.DB_PATH", db_path), \
         patch("config.DATA_DIR", data_dir), \
         patch("config.DB_PATH", db_path):

        from database import init_db, get_db
        await init_db()
        conn = await get_db()
        yield conn
        await conn.close()


class TestDeleteSideEffects:
    """Test that deleting recordings properly reverses all side effects."""

    @pytest.mark.asyncio
    async def test_session_count_decremented_on_delete(self, db, tmp_data_dir):
        """Deleting a recording should decrement its session's completed_count."""
        _, recordings_dir = tmp_data_dir

        # Create a session
        await db.execute(
            "INSERT INTO sessions (title, category, target_count, completed_count) VALUES (?, ?, ?, ?)",
            ("Test Session", "phonetic", 10, 0),
        )
        await db.commit()
        cursor = await db.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
        session_id = (await cursor.fetchone())[0]

        # Simulate recording upload: insert recording + increment session count
        wav_bytes = _make_wav_bytes()
        filename = "item_041.wav"
        (recordings_dir / filename).write_bytes(wav_bytes)

        await db.execute(
            """INSERT INTO recordings (item_number, filename, text, session_id, category, recorded_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (41, filename, "The quick brown fox", session_id, "phonetic"),
        )
        await db.execute(
            "UPDATE sessions SET completed_count = completed_count + 1 WHERE id = ?",
            (session_id,),
        )
        await db.commit()

        # Verify session count is 1
        cursor = await db.execute("SELECT completed_count FROM sessions WHERE id = ?", (session_id,))
        assert (await cursor.fetchone())[0] == 1

        # Delete the recording via _undo_recording_side_effects
        cursor = await db.execute("SELECT * FROM recordings WHERE item_number = 41")
        row = await cursor.fetchone()

        from routers.recordings import _undo_recording_side_effects
        await _undo_recording_side_effects(db, row)
        await db.execute("DELETE FROM recordings WHERE id = ?", (row["id"],))
        await db.commit()

        # Verify session count is back to 0
        cursor = await db.execute("SELECT completed_count FROM sessions WHERE id = ?", (session_id,))
        assert (await cursor.fetchone())[0] == 0

    @pytest.mark.asyncio
    async def test_session_count_does_not_go_negative(self, db, tmp_data_dir):
        """Deleting when completed_count is already 0 should stay at 0."""
        _, recordings_dir = tmp_data_dir

        # Create session with count=0
        await db.execute(
            "INSERT INTO sessions (title, category, target_count, completed_count) VALUES (?, ?, ?, ?)",
            ("Empty Session", "phonetic", 10, 0),
        )
        await db.commit()
        cursor = await db.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
        session_id = (await cursor.fetchone())[0]

        # Insert recording pointing to this session (simulating a bug where count wasn't incremented)
        filename = "item_041.wav"
        (recordings_dir / filename).write_bytes(_make_wav_bytes())
        await db.execute(
            """INSERT INTO recordings (item_number, filename, text, session_id, category, recorded_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (41, filename, "Hello world", session_id, "phonetic"),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM recordings WHERE item_number = 41")
        row = await cursor.fetchone()

        from routers.recordings import _undo_recording_side_effects
        await _undo_recording_side_effects(db, row)
        await db.commit()

        cursor = await db.execute("SELECT completed_count FROM sessions WHERE id = ?", (session_id,))
        assert (await cursor.fetchone())[0] == 0

    @pytest.mark.asyncio
    async def test_phoneme_coverage_decremented_on_delete(self, db, tmp_data_dir):
        """Deleting a recording should decrement phoneme occurrence counts."""
        _, recordings_dir = tmp_data_dir

        from services.phoneme_tracker import text_to_phonemes

        text = "The quick brown fox"
        phonemes = text_to_phonemes(text)

        # Simulate phoneme coverage from upload
        for phoneme in phonemes:
            await db.execute(
                """INSERT INTO phoneme_coverage (phoneme, category, occurrence_count, recording_ids)
                   VALUES (?, ?, 1, '[]')
                   ON CONFLICT(phoneme) DO UPDATE SET occurrence_count = occurrence_count + 1""",
                (phoneme, ""),
            )
        await db.commit()

        # Get baseline counts
        baseline = {}
        for phoneme in phonemes:
            cursor = await db.execute(
                "SELECT occurrence_count FROM phoneme_coverage WHERE phoneme = ?", (phoneme,)
            )
            row = await cursor.fetchone()
            baseline[phoneme] = row[0] if row else 0

        # Insert and delete recording
        filename = "item_041.wav"
        (recordings_dir / filename).write_bytes(_make_wav_bytes())
        await db.execute(
            """INSERT INTO recordings (item_number, filename, text, category, recorded_at)
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (41, filename, text, "phonetic"),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM recordings WHERE item_number = 41")
        row = await cursor.fetchone()

        from routers.recordings import _undo_recording_side_effects
        await _undo_recording_side_effects(db, row)
        await db.commit()

        # Verify counts decremented
        for phoneme in phonemes:
            cursor = await db.execute(
                "SELECT occurrence_count FROM phoneme_coverage WHERE phoneme = ?", (phoneme,)
            )
            result = await cursor.fetchone()
            assert result[0] == baseline[phoneme] - 1

    @pytest.mark.asyncio
    async def test_prompt_requeued_on_delete(self, db, tmp_data_dir):
        """Deleting a recording should return its text to the prompt cache as unused."""
        _, recordings_dir = tmp_data_dir

        text = "The ancient Stoics believed in virtue"

        filename = "item_041.wav"
        (recordings_dir / filename).write_bytes(_make_wav_bytes())
        await db.execute(
            """INSERT INTO recordings (item_number, filename, text, category, recorded_at)
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (41, filename, text, "phonetic"),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM recordings WHERE item_number = 41")
        row = await cursor.fetchone()

        from routers.recordings import _undo_recording_side_effects
        await _undo_recording_side_effects(db, row)
        await db.commit()

        # Verify text is in prompt_cache with used=0
        cursor = await db.execute(
            "SELECT text, category, used FROM prompt_cache WHERE text = ?", (text,)
        )
        cached = await cursor.fetchone()
        assert cached is not None, "Prompt text should be re-added to prompt_cache"
        assert cached["used"] == 0, "Re-added prompt should be marked as unused"
        assert cached["category"] == "phonetic"

    @pytest.mark.asyncio
    async def test_no_session_recording_delete(self, db, tmp_data_dir):
        """Deleting a recording with no session_id should work without error."""
        _, recordings_dir = tmp_data_dir

        filename = "item_041.wav"
        (recordings_dir / filename).write_bytes(_make_wav_bytes())
        await db.execute(
            """INSERT INTO recordings (item_number, filename, text, category, recorded_at)
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (41, filename, "No session text", "conversational"),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM recordings WHERE item_number = 41")
        row = await cursor.fetchone()
        assert row["session_id"] is None

        from routers.recordings import _undo_recording_side_effects
        await _undo_recording_side_effects(db, row)
        await db.commit()

        # Should complete without error, prompt should be cached
        cursor = await db.execute(
            "SELECT text FROM prompt_cache WHERE text = ?", ("No session text",)
        )
        assert await cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_batch_delete_reverses_all(self, db, tmp_data_dir):
        """Batch delete should reverse side effects for every recording in the batch."""
        _, recordings_dir = tmp_data_dir

        # Create session
        await db.execute(
            "INSERT INTO sessions (title, category, target_count, completed_count) VALUES (?, ?, ?, ?)",
            ("Batch Session", "phonetic", 10, 0),
        )
        await db.commit()
        cursor = await db.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
        session_id = (await cursor.fetchone())[0]

        # Insert 3 recordings
        texts = [
            "The first recording text",
            "The second recording text",
            "The third recording text",
        ]
        recording_ids = []
        for i, text in enumerate(texts):
            item_num = 41 + i
            filename = f"item_{item_num:03d}.wav"
            (recordings_dir / filename).write_bytes(_make_wav_bytes())
            await db.execute(
                """INSERT INTO recordings (item_number, filename, text, session_id, category, recorded_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (item_num, filename, text, session_id, "phonetic"),
            )
            await db.execute(
                "UPDATE sessions SET completed_count = completed_count + 1 WHERE id = ?",
                (session_id,),
            )

        await db.commit()

        # Verify session count is 3
        cursor = await db.execute("SELECT completed_count FROM sessions WHERE id = ?", (session_id,))
        assert (await cursor.fetchone())[0] == 3

        # Get recording IDs
        cursor = await db.execute("SELECT id FROM recordings ORDER BY id")
        rows = await cursor.fetchall()
        recording_ids = [r["id"] for r in rows]
        assert len(recording_ids) == 3

        # Delete all via _undo_recording_side_effects
        from routers.recordings import _undo_recording_side_effects
        for rid in recording_ids:
            cursor = await db.execute("SELECT * FROM recordings WHERE id = ?", (rid,))
            row = await cursor.fetchone()
            await _undo_recording_side_effects(db, row)

        placeholders = ",".join(["?"] * len(recording_ids))
        await db.execute(f"DELETE FROM recordings WHERE id IN ({placeholders})", recording_ids)
        await db.commit()

        # Session count should be 0
        cursor = await db.execute("SELECT completed_count FROM sessions WHERE id = ?", (session_id,))
        assert (await cursor.fetchone())[0] == 0

        # All 3 texts should be in prompt_cache
        cursor = await db.execute("SELECT COUNT(*) FROM prompt_cache WHERE used = 0")
        count = (await cursor.fetchone())[0]
        assert count == 3

        # All WAV files should still exist (we didn't call the endpoint, just the helper)
        # The endpoint handles file deletion; the helper handles DB side effects


class TestDeleteEndpoints:
    """Test the actual HTTP delete endpoints via TestClient.

    These tests patch config.DB_PATH and config.DATA_DIR at the module level
    so get_db() connects to the test database.
    """

    def _make_client(self, tmp_data_dir):
        """Create a test client with patched config pointing to temp dirs."""
        import asyncio
        data_dir, recordings_dir = tmp_data_dir
        db_path = data_dir / "test_endpoint.db"

        # Patch at the config module level so get_db() picks it up
        import config
        import database
        orig_db = config.DB_PATH
        orig_data = config.DATA_DIR
        orig_rec = config.RECORDINGS_DIR
        orig_db_db = database.DB_PATH
        orig_data_db = database.DATA_DIR

        config.DB_PATH = db_path
        config.DATA_DIR = data_dir
        config.RECORDINGS_DIR = recordings_dir
        database.DB_PATH = db_path
        database.DATA_DIR = data_dir

        # Import fresh to pick up patched config
        from database import init_db

        # Initialize the test database
        asyncio.get_event_loop().run_until_complete(init_db())

        # Patch RECORDINGS_DIR in the recordings router
        import routers.recordings as rec_mod
        orig_rec_dir = rec_mod.RECORDINGS_DIR
        rec_mod.RECORDINGS_DIR = recordings_dir

        from main import app
        client = TestClient(app, raise_server_exceptions=False)

        return client, {
            "config": config,
            "database": database,
            "rec_mod": rec_mod,
            "orig_db": orig_db,
            "orig_data": orig_data,
            "orig_rec": orig_rec,
            "orig_db_db": orig_db_db,
            "orig_data_db": orig_data_db,
            "orig_rec_dir": orig_rec_dir,
        }

    def _restore(self, refs):
        """Restore original config values."""
        refs["config"].DB_PATH = refs["orig_db"]
        refs["config"].DATA_DIR = refs["orig_data"]
        refs["config"].RECORDINGS_DIR = refs["orig_rec"]
        refs["database"].DB_PATH = refs["orig_db_db"]
        refs["database"].DATA_DIR = refs["orig_data_db"]
        refs["rec_mod"].RECORDINGS_DIR = refs["orig_rec_dir"]

    def test_delete_nonexistent_returns_404(self, tmp_data_dir):
        """DELETE /api/recordings/99999 should return 404."""
        client, refs = self._make_client(tmp_data_dir)
        try:
            resp = client.delete("/api/recordings/99999")
            assert resp.status_code == 404
        finally:
            self._restore(refs)

    def test_batch_delete_empty_returns_400(self, tmp_data_dir):
        """POST /api/recordings/batch-delete with empty list should return 400."""
        client, refs = self._make_client(tmp_data_dir)
        try:
            resp = client.post("/api/recordings/batch-delete", json={"recording_ids": []})
            assert resp.status_code == 400
        finally:
            self._restore(refs)
