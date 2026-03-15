"""Achievement engine for David's Voice.

Checks recording activity against achievement criteria and unlocks
achievements when thresholds are met.
"""

import json
from datetime import datetime, date, timedelta
from typing import Optional

import aiosqlite


async def check_achievements(db: aiosqlite.Connection) -> list[dict]:
    """Check all achievement conditions and unlock any newly earned ones.

    Returns a list of newly unlocked achievement dictionaries.
    """
    newly_unlocked = []

    # Get current stats
    row = await db.execute_fetchall("SELECT COUNT(*) as count FROM recordings")
    total_recordings = row[0][0] if row else 0

    # Check milestone achievements
    milestones = {
        "milestone_10": 10, "milestone_25": 25, "milestone_50": 50,
        "milestone_100": 100, "milestone_150": 150, "milestone_200": 200,
    }
    for key, threshold in milestones.items():
        if total_recordings >= threshold:
            unlocked = await _try_unlock(db, key)
            if unlocked:
                newly_unlocked.append(unlocked)

    # Check streak achievements
    streak = await _calculate_streak(db)
    streak_thresholds = {"streak_3": 3, "streak_7": 7, "streak_14": 14, "streak_30": 30}
    for key, threshold in streak_thresholds.items():
        if streak >= threshold:
            unlocked = await _try_unlock(db, key)
            if unlocked:
                newly_unlocked.append(unlocked)

    # Check quality achievements
    await _check_quality_achievements(db, newly_unlocked)

    # Check domain achievements
    await _check_domain_achievements(db, newly_unlocked)

    return newly_unlocked


async def _try_unlock(db: aiosqlite.Connection, key: str) -> Optional[dict]:
    """Try to unlock an achievement. Returns the achievement dict if newly unlocked, None otherwise."""
    cursor = await db.execute(
        "SELECT id, title, description, icon, category, unlocked_at FROM achievements WHERE key = ?",
        (key,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    if row["unlocked_at"] is not None:
        return None  # Already unlocked

    now = datetime.utcnow().isoformat()
    await db.execute(
        "UPDATE achievements SET unlocked_at = ? WHERE key = ?",
        (now, key)
    )
    await db.commit()

    return {
        "key": key,
        "title": row["title"],
        "description": row["description"],
        "icon": row["icon"],
        "category": row["category"],
        "unlocked_at": now,
    }


async def _calculate_streak(db: aiosqlite.Connection) -> int:
    """Calculate the current consecutive-day recording streak."""
    cursor = await db.execute(
        "SELECT date FROM daily_activity WHERE recordings_count > 0 ORDER BY date DESC"
    )
    rows = await cursor.fetchall()

    if not rows:
        return 0

    streak = 0
    expected_date = date.today()

    for row in rows:
        activity_date = date.fromisoformat(row["date"])
        if activity_date == expected_date:
            streak += 1
            expected_date -= timedelta(days=1)
        elif activity_date < expected_date:
            break

    return streak


async def get_streak_info(db: aiosqlite.Connection) -> dict:
    """Get current streak information."""
    streak = await _calculate_streak(db)

    # Check if today has activity
    today_str = date.today().isoformat()
    cursor = await db.execute(
        "SELECT recordings_count FROM daily_activity WHERE date = ?",
        (today_str,)
    )
    row = await cursor.fetchone()
    recorded_today = row["recordings_count"] > 0 if row else False

    # Longest streak ever
    cursor = await db.execute(
        "SELECT date FROM daily_activity WHERE recordings_count > 0 ORDER BY date ASC"
    )
    rows = await cursor.fetchall()
    longest = 0
    current = 0
    prev = None
    for row in rows:
        d = date.fromisoformat(row["date"])
        if prev is not None and (d - prev).days == 1:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
        prev = d

    return {
        "current_streak": streak,
        "longest_streak": longest,
        "recorded_today": recorded_today,
    }


async def _check_quality_achievements(db: aiosqlite.Connection, newly_unlocked: list):
    """Check quality-based achievements."""
    # Golden Mic: 10 consecutive A-rated recordings
    cursor = await db.execute(
        "SELECT quality_score FROM recordings ORDER BY id DESC LIMIT 10"
    )
    rows = await cursor.fetchall()
    if len(rows) >= 10 and all(r["quality_score"] == "A" for r in rows):
        unlocked = await _try_unlock(db, "quality_golden_mic")
        if unlocked:
            newly_unlocked.append(unlocked)

    # Consistent: 20 recordings within 3dB of each other
    cursor = await db.execute(
        "SELECT rms_db FROM recordings WHERE rms_db IS NOT NULL ORDER BY id DESC LIMIT 20"
    )
    rows = await cursor.fetchall()
    if len(rows) >= 20:
        rms_values = [r["rms_db"] for r in rows]
        if max(rms_values) - min(rms_values) <= 3.0:
            unlocked = await _try_unlock(db, "quality_consistent")
            if unlocked:
                newly_unlocked.append(unlocked)


async def _check_domain_achievements(db: aiosqlite.Connection, newly_unlocked: list):
    """Check domain-based achievements."""
    domains = {
        "domain_legal": ("domain", 20),
        "domain_narrative": ("narrative", 20),
        "domain_conversational": ("conversational", 20),
    }
    for key, (category, threshold) in domains.items():
        cursor = await db.execute(
            "SELECT COUNT(*) as count FROM recordings WHERE category = ?",
            (category,)
        )
        row = await cursor.fetchone()
        if row and row["count"] >= threshold:
            unlocked = await _try_unlock(db, key)
            if unlocked:
                newly_unlocked.append(unlocked)


async def update_daily_activity(db: aiosqlite.Connection, quality_score: str):
    """Record activity for streak tracking."""
    today_str = date.today().isoformat()

    # Map quality to numeric for averaging
    score_map = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0}
    numeric_score = score_map.get(quality_score, 1.0)

    cursor = await db.execute(
        "SELECT recordings_count, avg_quality_score FROM daily_activity WHERE date = ?",
        (today_str,)
    )
    row = await cursor.fetchone()

    if row:
        new_count = row["recordings_count"] + 1
        prev_avg = row["avg_quality_score"] or 0
        new_avg = (prev_avg * row["recordings_count"] + numeric_score) / new_count
        await db.execute(
            "UPDATE daily_activity SET recordings_count = ?, avg_quality_score = ? WHERE date = ?",
            (new_count, new_avg, today_str)
        )
    else:
        await db.execute(
            "INSERT INTO daily_activity (date, recordings_count, avg_quality_score) VALUES (?, 1, ?)",
            (today_str, numeric_score)
        )

    await db.commit()
