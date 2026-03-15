"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# --- Recordings ---

class RecordingResponse(BaseModel):
    id: int
    item_number: int
    filename: str
    text: str
    session_id: Optional[int] = None
    category: Optional[str] = None
    duration_seconds: Optional[float] = None
    quality_score: Optional[str] = None
    snr_db: Optional[float] = None
    has_clipping: bool = False
    silence_ratio: Optional[float] = None
    rms_db: Optional[float] = None
    recorded_at: Optional[str] = None
    flag: Optional[str] = None
    manual_quality_override: Optional[str] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[str] = None


class RecordingReviewUpdate(BaseModel):
    flag: Optional[str] = None
    manual_quality_override: Optional[str] = None
    review_note: Optional[str] = None


class BatchReviewUpdate(BaseModel):
    recording_ids: list[int]
    flag: Optional[str] = None
    manual_quality_override: Optional[str] = None
    review_note: Optional[str] = None


class BatchDelete(BaseModel):
    recording_ids: list[int]


class RecordingUploadResponse(BaseModel):
    recording: RecordingResponse
    analysis: dict
    new_achievements: list[dict] = []


# --- Sessions ---

class SessionCreate(BaseModel):
    title: str
    category: str
    target_count: int = 10


class SessionResponse(BaseModel):
    id: int
    title: str
    category: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    target_count: int = 10
    completed_count: int = 0


# --- Prompts ---

class PromptGenerateRequest(BaseModel):
    category: str = "phonetic"
    count: int = 10


class PromptResponse(BaseModel):
    prompts: list[str]
    category: str
    phoneme_guidance: Optional[str] = None


# --- Progress ---

class DashboardResponse(BaseModel):
    total_recordings: int
    target_recordings: int
    quality_distribution: dict
    recent_recordings: list[RecordingResponse]
    streak_info: dict
    phoneme_coverage: dict


class AchievementResponse(BaseModel):
    key: str
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    threshold: Optional[int] = None
    unlocked_at: Optional[str] = None
    is_unlocked: bool = False
