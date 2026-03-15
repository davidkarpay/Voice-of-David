"""David's Voice - FastAPI backend entry point.

Gamified voice model development platform that uses the Anthropic API
to generate recording prompts and provides real-time quality feedback.
"""

import json
import shutil
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import (
    HOST, PORT, CORS_ORIGINS, RECORDINGS_DIR, DATA_DIR,
    EXISTING_DATASET_DIR, EXISTING_METADATA_JSON,
)
from database import init_db, get_db
from services.audio_analyzer import analyze_audio_file
from services.phoneme_tracker import text_to_phonemes
from services.achievement_engine import check_achievements

from routers import recordings, prompts, progress, sessions


async def import_existing_dataset():
    """Import existing 40 recordings from dataset_40_items/ into the database.

    Reads metadata.json for text transcriptions, runs quality analysis on each
    audio file, and populates the recordings and phoneme_coverage tables.
    Skips files already imported (idempotent).
    """
    if not EXISTING_DATASET_DIR.exists():
        print(f"No existing dataset found at {EXISTING_DATASET_DIR}")
        return

    if not EXISTING_METADATA_JSON.exists():
        print(f"No metadata.json found at {EXISTING_METADATA_JSON}")
        return

    db = await get_db()
    try:
        # Check if already imported
        cursor = await db.execute("SELECT COUNT(*) as count FROM recordings WHERE item_number <= 40")
        row = await cursor.fetchone()
        if row["count"] > 0:
            print(f"Existing dataset already imported ({row['count']} recordings). Skipping.")
            return

        # Load metadata
        with open(EXISTING_METADATA_JSON, "r") as f:
            metadata_list = json.load(f)

        print(f"Importing {len(metadata_list)} existing recordings...")

        imported = 0
        for entry in metadata_list:
            audio_file = entry.get("audio_file", "")
            text = entry.get("text", "")

            if not audio_file or not text:
                continue

            source_path = EXISTING_DATASET_DIR / audio_file
            if not source_path.exists():
                print(f"  Skipping {audio_file} (file not found)")
                continue

            # Extract item number from filename (e.g., "item_001.wav" -> 1)
            try:
                item_num = int(audio_file.replace("item_", "").replace(".wav", ""))
            except ValueError:
                continue

            # Copy to recordings directory
            RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
            dest_path = RECORDINGS_DIR / audio_file
            if not dest_path.exists():
                shutil.copy2(source_path, dest_path)

            # Analyze quality
            try:
                analysis = analyze_audio_file(source_path)
            except Exception as e:
                print(f"  Error analyzing {audio_file}: {e}")
                continue

            # Insert into database
            await db.execute(
                """INSERT OR IGNORE INTO recordings
                   (item_number, filename, text, category, duration_seconds,
                    quality_score, snr_db, has_clipping, silence_ratio, rms_db)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item_num, audio_file, text, "phonetic",
                    analysis.duration_seconds, analysis.quality_score,
                    analysis.snr_db, analysis.has_clipping,
                    analysis.silence_ratio, analysis.rms_db,
                )
            )

            # Update phoneme coverage
            phonemes = text_to_phonemes(text)
            for phoneme in phonemes:
                await db.execute(
                    """INSERT INTO phoneme_coverage (phoneme, category, occurrence_count, recording_ids)
                       VALUES (?, '', 1, ?)
                       ON CONFLICT(phoneme) DO UPDATE SET
                       occurrence_count = occurrence_count + 1""",
                    (phoneme, json.dumps([item_num]))
                )

            imported += 1

        await db.commit()
        print(f"Imported {imported} existing recordings successfully.")

        # Run achievement check
        new_achievements = await check_achievements(db)
        if new_achievements:
            print(f"Unlocked {len(new_achievements)} achievements from imported data:")
            for ach in new_achievements:
                print(f"  - {ach['title']}: {ach['description']}")

    finally:
        await db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    print("Initializing David's Voice...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    await init_db()
    await import_existing_dataset()

    print(f"David's Voice ready at http://{HOST}:{PORT}")
    yield
    # Shutdown
    print("Shutting down David's Voice.")


app = FastAPI(
    title="David's Voice",
    description="Gamified voice model development platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS (Cross-Origin Resource Sharing) for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(recordings.router)
app.include_router(prompts.router)
app.include_router(progress.router)
app.include_router(sessions.router)

# Serve recordings as static files for audio playback
app.mount("/audio", StaticFiles(directory=str(RECORDINGS_DIR)), name="audio")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) as count FROM recordings")
        count = (await cursor.fetchone())["count"]
        return {
            "status": "healthy",
            "recordings": count,
        }
    finally:
        await db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
