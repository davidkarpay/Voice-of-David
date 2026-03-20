# TTS Project Context

## Kokoro TTS Web UI
- Backend: `server.py` (FastAPI, port 8000)
- Frontend: `index.html` (vanilla JS, no build step)
- Venv: `kokoro_env/` (Python 3.12, includes kokoro, torch, torchaudio, fastapi, uvicorn)
- System dep: `espeak-ng` (Homebrew)
- Voices in use: `af_heart`, `af_nova`, `bm_george`
- Start: `source kokoro_env/bin/activate && python server.py`

## 3D Chair Voice Studio (David's Voice)
- Path: `3d-chair-voice-studio/`
- Backend: FastAPI on port 8001, venv at `3d-chair-voice-studio/backend/venv/`
- Frontend: React/TypeScript/Vite on port 5173+
- Database: SQLite at `3d-chair-voice-studio/data/voice_studio.db`
- Recordings: `3d-chair-voice-studio/data/recordings/`
- Requires: ffmpeg (for webm->WAV conversion), optional ANTHROPIC_API_KEY for prompt generation
- Start backend: `cd 3d-chair-voice-studio/backend && source venv/bin/activate && python main.py`
- Start frontend: `cd 3d-chair-voice-studio/frontend && npm run dev`
- Note: Kokoro TTS occupies port 8000, so voice studio uses port 8001

## XTTS Voice Cloning
- Finetuned models on NAS: `/Volumes/david/TTS_models/`
- Original venvs (TTS_venv, TTS_env) were deleted during disk cleanup 2026-03-11
- To use XTTS again, install Idiap fork: `pip install coqui-tts`

## Testing
- Voice studio backend: `cd 3d-chair-voice-studio/backend && source venv/bin/activate && python -m pytest tests/ -v`
- Tests use in-memory SQLite and temp dirs (no production data touched)
- Test deps: pytest, pytest-asyncio (installed in voice studio venv)

## Known Issues
- Kokoro question intonation is flat for English (model limitation, not fixable via config)

## Design Decisions
- Word transcript uses torchaudio wav2vec2 forced alignment for exact word timestamps
- Deleting a recording reverses all side effects (session count, phoneme coverage, prompt re-queued)
