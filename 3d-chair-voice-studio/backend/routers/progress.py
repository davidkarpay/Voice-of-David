"""Progress, achievements, and stats API endpoints."""

from fastapi import APIRouter
import aiosqlite

from database import get_db
from routers.recordings import _row_to_response
from services.achievement_engine import get_streak_info
from services.phoneme_tracker import ALL_PHONEMES, get_coverage_stats, PHONEME_CATEGORIES
from models.schemas import DashboardResponse, AchievementResponse
from config import TARGET_RECORDINGS

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    """Get aggregate dashboard data: totals, quality distribution,
    recent recordings, streak info, and phoneme coverage."""
    db = await get_db()
    try:
        # Total recordings
        cursor = await db.execute("SELECT COUNT(*) as total FROM recordings")
        total = (await cursor.fetchone())["total"]

        # Quality distribution
        cursor = await db.execute(
            "SELECT quality_score, COUNT(*) as count FROM recordings GROUP BY quality_score"
        )
        quality_dist = {r["quality_score"]: r["count"] for r in await cursor.fetchall()}

        # Recent recordings
        cursor = await db.execute(
            "SELECT * FROM recordings ORDER BY id DESC LIMIT 5"
        )
        recent = [_row_to_response(r) for r in await cursor.fetchall()]

        # Streak info
        streak = await get_streak_info(db)

        # Phoneme coverage
        cursor = await db.execute("SELECT phoneme FROM phoneme_coverage WHERE occurrence_count > 0")
        covered = {r["phoneme"] for r in await cursor.fetchall()}
        coverage = get_coverage_stats(covered)

        return DashboardResponse(
            total_recordings=total,
            target_recordings=TARGET_RECORDINGS,
            quality_distribution=quality_dist,
            recent_recordings=recent,
            streak_info=streak,
            phoneme_coverage=coverage,
        )

    finally:
        await db.close()


@router.get("/achievements", response_model=list[AchievementResponse])
async def get_achievements():
    """Get all achievements with their unlock status."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM achievements ORDER BY category, threshold"
        )
        rows = await cursor.fetchall()

        return [
            AchievementResponse(
                key=r["key"],
                title=r["title"],
                description=r["description"],
                icon=r["icon"],
                category=r["category"],
                threshold=r["threshold"],
                unlocked_at=r["unlocked_at"],
                is_unlocked=r["unlocked_at"] is not None,
            )
            for r in rows
        ]

    finally:
        await db.close()


@router.get("/streak")
async def get_streak():
    """Get current streak information."""
    db = await get_db()
    try:
        return await get_streak_info(db)
    finally:
        await db.close()


@router.get("/phonemes")
async def get_phoneme_details():
    """Get detailed phoneme coverage data."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM phoneme_coverage")
        rows = await cursor.fetchall()
        covered = {r["phoneme"] for r in rows if r["occurrence_count"] > 0}

        stats = get_coverage_stats(covered)

        # Add occurrence counts
        occurrence_map = {r["phoneme"]: r["occurrence_count"] for r in rows}
        for cat_data in stats["categories"].values():
            for phoneme in cat_data["phonemes"]:
                cat_data["phonemes"][phoneme] = {
                    "covered": cat_data["phonemes"][phoneme],
                    "count": occurrence_map.get(phoneme, 0),
                }

        return stats

    finally:
        await db.close()
