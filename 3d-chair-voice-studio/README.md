# David's Voice - 3D Chair Voice Studio

Gamified voice recording platform for building a personal TTS voice clone dataset. Generates phoneme-targeted prompts via Claude API, analyzes audio quality in real-time, and tracks progress through achievements and streaks.

## Quick Start

```bash
# Terminal 1: Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."  # optional, falls back to built-in prompts
python main.py
# Runs on http://localhost:8001

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173 (or next available port)
```

Open the frontend URL in Chrome. The app will auto-import any existing recordings from `~/Desktop/TTS/dataset_40_items/` on first run.

## Architecture

- **Backend**: FastAPI + aiosqlite + anthropic SDK
- **Frontend**: React 19 + TypeScript + Vite (inline styles, lucide-react icons)
- **Audio**: Browser MediaRecorder (webm/opus) -> ffmpeg conversion to 16-bit 44.1kHz mono WAV
- **Database**: SQLite at `data/voice_studio.db`
- **Recordings**: Stored as WAV files in `data/recordings/`

## Features

### Dashboard
- Recording count, streak tracking, phoneme coverage (39/40 sounds), achievement progress
- Quality distribution chart (A/B/C/D grades)
- Session launcher with 5 categories: Phonetic, Conversational, Emotional, Domain, Narrative

### Recording Studio
- Claude-generated prompts targeted at phoneme gaps (10 per batch)
- 3-second countdown, live waveform visualization
- Real-time quality analysis: duration, SNR, RMS, clipping detection, silence ratio
- Automatic quality grading (A/B/C/D) based on composite scoring

### Review Page
- Browse all recordings with search, filter (category/quality/flag), and sort
- Inline audio playback
- Expandable detail view with full quality metrics
- Manual quality override (A/B/C/D)
- Flag system: Favorite, Needs Redo, Delete
- Notes field for each recording
- Batch operations: flag, unflag, or delete multiple recordings at once

### Gamification
- 22 achievements across 6 categories (milestones, quality, streaks, phoneme, domain, sessions)
- Daily streak tracking with longest-streak record
- Phoneme coverage map showing covered/missing sounds by category

## Dependencies

- **Python 3.12+** with packages in `backend/requirements.txt`
- **Node.js 20+** for the frontend
- **ffmpeg** (Homebrew: `brew install ffmpeg`) for webm-to-WAV conversion
- **Anthropic API key** (optional, for AI-generated prompts)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/progress/dashboard` | Dashboard stats |
| GET | `/api/progress/achievements` | All achievements |
| GET | `/api/progress/streak` | Streak info |
| GET | `/api/progress/phonemes` | Phoneme coverage details |
| POST | `/api/prompts/generate` | Generate recording prompts |
| GET | `/api/recordings` | List recordings (filterable) |
| POST | `/api/recordings/upload` | Upload a recording |
| PATCH | `/api/recordings/{id}/review` | Update review metadata |
| POST | `/api/recordings/batch-review` | Batch flag/review |
| POST | `/api/recordings/batch-delete` | Batch delete |
| DELETE | `/api/recordings/{id}` | Delete single recording |

## Configuration

All config is in `backend/config.py`:
- `PORT`: Server port (default 8001)
- `TARGET_RECORDINGS`: Goal count (200)
- `AUDIO_SAMPLE_RATE`: 44100 Hz
- `MIN_DURATION_SECONDS` / `MAX_DURATION_SECONDS`: 3-30s
- `SNR_THRESHOLD_A/B/C`: Quality grade cutoffs (30/20/15 dB)

Last updated: 2026-03-15
