"""SQLite database setup and management for David's Voice."""

import aiosqlite
import json
from pathlib import Path
from config import DB_PATH, DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_number INTEGER UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    text TEXT NOT NULL,
    session_id INTEGER REFERENCES sessions(id),
    category TEXT,
    duration_seconds REAL,
    quality_score TEXT,
    snr_db REAL,
    has_clipping BOOLEAN DEFAULT 0,
    silence_ratio REAL,
    rms_db REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    flag TEXT DEFAULT NULL,
    manual_quality_override TEXT DEFAULT NULL,
    review_note TEXT DEFAULT NULL,
    reviewed_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    category TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    target_count INTEGER DEFAULT 10,
    completed_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    category TEXT,
    threshold INTEGER,
    unlocked_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS phoneme_coverage (
    phoneme TEXT PRIMARY KEY,
    category TEXT,
    occurrence_count INTEGER DEFAULT 0,
    recording_ids TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS daily_activity (
    date TEXT PRIMARY KEY,
    recordings_count INTEGER DEFAULT 0,
    avg_quality_score REAL
);

CREATE TABLE IF NOT EXISTS prompt_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    category TEXT,
    target_phonemes TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used BOOLEAN DEFAULT 0
);
"""

# Achievement definitions
ACHIEVEMENT_DEFINITIONS = [
    # Milestones
    {"key": "milestone_10", "title": "Getting Started", "description": "Record 10 voice samples", "icon": "mic", "category": "milestone", "threshold": 10},
    {"key": "milestone_25", "title": "Quarter Way", "description": "Record 25 voice samples", "icon": "trending-up", "category": "milestone", "threshold": 25},
    {"key": "milestone_50", "title": "Half Century", "description": "Record 50 voice samples", "icon": "award", "category": "milestone", "threshold": 50},
    {"key": "milestone_100", "title": "Triple Digits", "description": "Record 100 voice samples", "icon": "star", "category": "milestone", "threshold": 100},
    {"key": "milestone_150", "title": "Almost There", "description": "Record 150 voice samples", "icon": "target", "category": "milestone", "threshold": 150},
    {"key": "milestone_200", "title": "Voice Complete", "description": "Record all 200 voice samples", "icon": "check-circle", "category": "milestone", "threshold": 200},
    # Quality
    {"key": "quality_golden_mic", "title": "Golden Mic", "description": "10 consecutive A-rated recordings", "icon": "mic", "category": "quality", "threshold": 10},
    {"key": "quality_consistent", "title": "Consistent", "description": "20 recordings all within 3dB of each other", "icon": "activity", "category": "quality", "threshold": 20},
    {"key": "quality_perfect_session", "title": "Perfect Session", "description": "Complete a session with all A-rated recordings", "icon": "shield-check", "category": "quality", "threshold": 1},
    # Streaks
    {"key": "streak_3", "title": "Three-Peat", "description": "Record for 3 consecutive days", "icon": "flame", "category": "streak", "threshold": 3},
    {"key": "streak_7", "title": "Week Warrior", "description": "Record for 7 consecutive days", "icon": "flame", "category": "streak", "threshold": 7},
    {"key": "streak_14", "title": "Fortnight Force", "description": "Record for 14 consecutive days", "icon": "flame", "category": "streak", "threshold": 14},
    {"key": "streak_30", "title": "Monthly Master", "description": "Record for 30 consecutive days", "icon": "flame", "category": "streak", "threshold": 30},
    # Phoneme coverage
    {"key": "phoneme_plosives", "title": "Plosive Power", "description": "Cover all plosive sounds (P, B, T, D, K, G)", "icon": "volume-2", "category": "phoneme", "threshold": 6},
    {"key": "phoneme_fricatives", "title": "Friction Master", "description": "Cover all fricative sounds", "icon": "wind", "category": "phoneme", "threshold": 9},
    {"key": "phoneme_vowels", "title": "Vowel Virtuoso", "description": "Cover all vowel sounds", "icon": "music", "category": "phoneme", "threshold": 15},
    {"key": "phoneme_master", "title": "Phoneme Master", "description": "95%+ phoneme coverage", "icon": "crown", "category": "phoneme", "threshold": 37},
    # Domain
    {"key": "domain_legal", "title": "Legal Eagle", "description": "Record 20 legal domain prompts", "icon": "scale", "category": "domain", "threshold": 20},
    {"key": "domain_narrative", "title": "Storyteller", "description": "Record 20 narrative prompts", "icon": "book-open", "category": "domain", "threshold": 20},
    {"key": "domain_conversational", "title": "Conversationalist", "description": "Record 20 conversational prompts", "icon": "message-circle", "category": "domain", "threshold": 20},
    # Session
    {"key": "session_marathon", "title": "Marathon", "description": "Record 40 samples in one session", "icon": "timer", "category": "session", "threshold": 40},
    {"key": "session_quick_five", "title": "Quick Five", "description": "5 high-quality recordings in under 10 minutes", "icon": "zap", "category": "session", "threshold": 5},
]


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Initialize the database schema and seed achievement definitions."""
    db = await get_db()
    try:
        await db.executescript(SCHEMA)

        # Migrate existing databases: add review columns if missing
        for col in ["flag", "manual_quality_override", "review_note", "reviewed_at"]:
            try:
                await db.execute(f"ALTER TABLE recordings ADD COLUMN {col} TEXT DEFAULT NULL")
            except Exception:
                pass  # Column already exists

        # Seed achievements if not present
        for ach in ACHIEVEMENT_DEFINITIONS:
            await db.execute(
                """INSERT OR IGNORE INTO achievements (key, title, description, icon, category, threshold)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (ach["key"], ach["title"], ach["description"], ach["icon"], ach["category"], ach["threshold"])
            )

        await db.commit()
    finally:
        await db.close()
