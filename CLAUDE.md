# TTS Project Context

## Kokoro TTS Web UI
- Backend: `server.py` (FastAPI, port 8000)
- Frontend: `index.html` (vanilla JS, no build step)
- Venv: `kokoro_env/` (Python 3.12, includes kokoro, torch, fastapi, uvicorn)
- System dep: `espeak-ng` (Homebrew)
- Voices in use: `af_heart`, `af_nova`, `bm_george`
- Start: `source kokoro_env/bin/activate && python server.py`

## XTTS Voice Cloning
- Finetuned models on NAS: `/Volumes/david/TTS_models/`
- Original venvs (TTS_venv, TTS_env) were deleted during disk cleanup 2026-03-11
- To use XTTS again, install Idiap fork: `pip install coqui-tts`

## Known Issues
- Kokoro question intonation is flat for English (model limitation, not fixable via config)
- Word transcript highlighting uses syllable estimation, not exact alignment
