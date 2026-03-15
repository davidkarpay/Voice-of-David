"""Prompt generation API endpoints."""

import json
from typing import Optional

from fastapi import APIRouter, HTTPException
import aiosqlite

from database import get_db
from services.anthropic_service import generate_prompts, generate_prompts_fallback
from services.phoneme_tracker import (
    text_to_phonemes, get_coverage_stats, get_missing_phonemes,
    get_phoneme_suggestions_for_prompt, ALL_PHONEMES,
)
from models.schemas import PromptGenerateRequest, PromptResponse
from config import ANTHROPIC_API_KEY

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.post("/generate", response_model=PromptResponse)
async def generate_recording_prompts(request: PromptGenerateRequest):
    """Generate recording prompts using Claude, targeted at phoneme gaps.

    Falls back to built-in templates if the Anthropic API key is not configured.
    """
    db = await get_db()
    try:
        # Get current phoneme coverage
        cursor = await db.execute("SELECT phoneme FROM phoneme_coverage WHERE occurrence_count > 0")
        rows = await cursor.fetchall()
        covered = {r["phoneme"] for r in rows}
        missing = get_missing_phonemes(covered)
        guidance = get_phoneme_suggestions_for_prompt(missing)

        # Get existing texts to avoid repetition
        cursor = await db.execute("SELECT text FROM recordings ORDER BY id DESC LIMIT 30")
        rows = await cursor.fetchall()
        existing_texts = [r["text"] for r in rows]

        # Generate prompts
        if ANTHROPIC_API_KEY:
            try:
                prompts = await generate_prompts(
                    category=request.category,
                    count=request.count,
                    phoneme_guidance=guidance if request.category == "phonetic" else None,
                    existing_texts=existing_texts,
                )
            except Exception as e:
                # Fall back to templates on API error
                prompts = await generate_prompts_fallback(request.category, request.count)
        else:
            prompts = await generate_prompts_fallback(request.category, request.count)

        # Cache generated prompts
        for prompt in prompts:
            await db.execute(
                "INSERT INTO prompt_cache (text, category, target_phonemes) VALUES (?, ?, ?)",
                (prompt, request.category, json.dumps(missing[:5]))
            )
        await db.commit()

        return PromptResponse(
            prompts=prompts,
            category=request.category,
            phoneme_guidance=guidance if missing else None,
        )

    finally:
        await db.close()


@router.get("/suggestions")
async def get_prompt_suggestions():
    """Get smart prompt suggestions based on what's needed most.

    Returns unused cached prompts or generates recommendations for
    which category to record next.
    """
    db = await get_db()
    try:
        # Check for unused cached prompts
        cursor = await db.execute(
            "SELECT id, text, category FROM prompt_cache WHERE used = 0 ORDER BY generated_at DESC LIMIT 5"
        )
        cached = await cursor.fetchall()

        # Get category distribution
        cursor = await db.execute(
            "SELECT category, COUNT(*) as count FROM recordings GROUP BY category"
        )
        distribution = {r["category"]: r["count"] for r in await cursor.fetchall()}

        # Get total
        cursor = await db.execute("SELECT COUNT(*) as total FROM recordings")
        total = (await cursor.fetchone())["total"]

        # Recommend the least-covered category
        categories = ["phonetic", "conversational", "emotional", "domain", "narrative"]
        min_category = min(categories, key=lambda c: distribution.get(c, 0))

        # Get phoneme coverage
        cursor = await db.execute("SELECT phoneme FROM phoneme_coverage WHERE occurrence_count > 0")
        covered = {r["phoneme"] for r in await cursor.fetchall()}
        coverage_pct = len(covered) / len(ALL_PHONEMES) * 100 if ALL_PHONEMES else 0

        return {
            "cached_prompts": [{"id": r["id"], "text": r["text"], "category": r["category"]} for r in cached],
            "recommended_category": min_category,
            "category_distribution": distribution,
            "total_recordings": total,
            "phoneme_coverage_percentage": round(coverage_pct, 1),
        }

    finally:
        await db.close()
