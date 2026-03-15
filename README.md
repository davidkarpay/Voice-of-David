# Voice of David - TTS Project

Text-to-speech tools for voice cloning (XTTS v2) and general-purpose speech synthesis (Kokoro).

## Components

### Kokoro TTS Web UI

A web-based text-to-speech interface powered by the [Kokoro-82M](https://github.com/hexgrad/kokoro) model (Apache 2.0, 82M parameters).

**Features:**
- Paste any text and generate natural speech at ~4.5x realtime on Apple Silicon
- Three curated voices: Heart (American female), Nova (American female), George (British male)
- Adjustable speed (0.5x - 2.0x)
- Canvas-based waveform visualization with click-to-seek
- Synchronized word-by-word transcript with click-to-navigate
- Real-time SSE progress during generation
- WAV file download

**Quick Start:**
```bash
cd ~/Desktop/TTS
source kokoro_env/bin/activate
python server.py
# Open http://localhost:8000
```

**Dependencies:**
- Python 3.12+ with venv at `kokoro_env/`
- System: `espeak-ng` (via Homebrew)
- Python: `kokoro`, `torch`, `fastapi`, `uvicorn`, `soundfile`, `numpy`

**Architecture:**
- `server.py` — FastAPI backend. Loads Kokoro pipeline once at startup, serves SSE generation endpoint with chunk-level progress and word timing data.
- `index.html` — Vanilla JS/CSS frontend. Canvas waveform, synchronized transcript with syllable-based word timing estimation, keyboard shortcuts (Space = play/pause).
- `generated/` — Temporary WAV output directory (auto-cleaned on startup, files >1hr deleted).

**Known Limitations:**
- Question intonation is flat (model-level limitation for English; rising intonation tokens exist but English G2P never generates them). Acceptable for long-form content.
- Word highlighting uses syllable-count estimation within chunks, not exact forced alignment.

### XTTS Voice Cloning (Legacy)

Fine-tuned XTTS v2 model trained on David's voice recordings.

- **Finetuned models**: Moved to NAS at `/Volumes/david/TTS_models/`
- **Training data**: `dataset_40_items/`, `dataset_expanded/`
- **Recording tools**: `recording_assistant.py` (Audacity integration), `recording_sentences.json`
- **Voice studio**: `3d-chair-voice-studio/` (React + FastAPI recording UI)
- **Comparison tools**: `compare_models.py`, `test_multireference.py`

See `RECORDING_QUICK_START.md` and `recording_plan.md` for the voice recording workflow.

## Project Structure

```
~/Desktop/TTS/
├── server.py                  # Kokoro TTS FastAPI backend
├── index.html                 # Kokoro TTS web UI
├── kokoro_env/                # Python venv (Kokoro + deps)
├── generated/                 # Temporary generated WAV files
├── 3d-chair-voice-studio/     # React voice recording studio (XTTS)
├── dataset_40_items/          # Original 40 voice samples
├── dataset_expanded/          # Expanded recording dataset
├── recording_assistant.py     # Audacity recording helper
├── recording_sentences.json   # Sentence prompts for recording
├── compare_models.py          # XTTS model comparison tool
├── finetune_verified.py       # XTTS finetuning script
├── finetune_optimized.py      # Optimized finetuning variant
└── voice_test_outputs/        # XTTS test output audio
```

## Last Updated

2026-03-15
