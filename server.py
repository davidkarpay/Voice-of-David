"""
server.py

FastAPI backend for the Kokoro TTS web interface. Loads the Kokoro 82M model
once at startup, accepts text + voice via an SSE endpoint, generates audio
chunk-by-chunk with real-time progress reporting, and serves the resulting WAV.

Uses torchaudio forced alignment (wav2vec2) for exact word-level timestamps
in the synchronized transcript.

Part of: Kokoro TTS Web UI
See: index.html for the frontend

Dependencies:
    - fastapi/uvicorn: HTTP server and ASGI
    - kokoro: TTS model pipeline (82M params, Apache 2.0)
    - soundfile: WAV file writing
    - numpy: audio array concatenation
    - torchaudio: forced alignment for word timestamps

Author: David Karpay
Created: 2026-03-13
Last Modified: 2026-03-15
"""

import asyncio
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from starlette.responses import StreamingResponse

SAMPLE_RATE = 24000
ALIGN_SAMPLE_RATE = 16000
GENERATED_DIR = Path(__file__).parent / "generated"
INDEX_HTML = Path(__file__).parent / "index.html"

VOICES = {
    "af_heart": "Heart (American female)",
    "af_nova": "Nova (American female)",
    "bm_george": "George (British male)",
}

pipeline = None
align_model = None
align_labels = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Kokoro pipeline and alignment model once at startup."""
    global pipeline, align_model, align_labels
    import kokoro

    print("Loading Kokoro pipeline...")
    pipeline = kokoro.KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")

    for voice_id in VOICES:
        try:
            pipeline.load_voice(voice_id)
            print(f"  Loaded voice: {voice_id}")
        except Exception:
            pass

    print("Loading alignment model (wav2vec2)...")
    bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
    align_model = bundle.get_model()
    align_labels = bundle.get_labels()
    print("  Alignment model ready")

    GENERATED_DIR.mkdir(exist_ok=True)

    cutoff = time.time() - 3600
    for f in GENERATED_DIR.glob("*.wav"):
        if f.stat().st_mtime < cutoff:
            f.unlink()

    print("Ready at http://localhost:8000")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    """Serve the frontend."""
    return FileResponse(INDEX_HTML, media_type="text/html")


@app.get("/api/voices")
async def get_voices():
    """Return available voices."""
    return JSONResponse(
        [{"id": k, "name": v} for k, v in VOICES.items()]
    )


def align_audio_to_words(audio_np: np.ndarray, text: str):
    """
    Run forced alignment on audio to get exact word-level timestamps.

    Uses wav2vec2 CTC forced alignment: a single forward pass through the
    model produces emission probabilities, then dynamic programming aligns
    the known text to those emissions.

    Args:
        audio_np: Audio as numpy float32 array at SAMPLE_RATE (24kHz)
        text: The exact text that was spoken

    Returns:
        List of dicts with 'word', 'start', 'end' keys (times in seconds)
    """
    waveform = torch.from_numpy(audio_np).unsqueeze(0).float()

    # Resample 24kHz -> 16kHz for wav2vec2
    waveform = torchaudio.functional.resample(waveform, SAMPLE_RATE, ALIGN_SAMPLE_RATE)

    with torch.inference_mode():
        emissions, _ = align_model(waveform)

    # Normalize text: uppercase, keep only chars in the model's vocabulary
    clean_text = re.sub(r"[^\w\s']", "", text).upper()
    # Collapse multiple spaces
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # Tokenize: map characters to label indices, spaces to '|'
    tokens = []
    for c in clean_text:
        if c == " ":
            tokens.append(align_labels.index("|"))
        elif c in align_labels:
            tokens.append(align_labels.index(c))

    if not tokens:
        return []

    aligned_tokens, scores = torchaudio.functional.forced_align(
        emissions, torch.tensor([tokens]), blank=0
    )
    token_spans = torchaudio.functional.merge_tokens(aligned_tokens[0], scores[0])

    # Convert frame indices to seconds
    ratio = waveform.shape[1] / emissions.shape[1]
    frame_to_sec = ratio / ALIGN_SAMPLE_RATE

    # Group character spans into words (split on '|' token)
    words = clean_text.split()
    word_timings = []
    word_idx = 0
    current_chars = []

    for span in token_spans:
        label = align_labels[span.token]
        if label == "|":
            if current_chars and word_idx < len(words):
                word_timings.append({
                    "word": words[word_idx],
                    "start": round(current_chars[0].start * frame_to_sec, 3),
                    "end": round(current_chars[-1].end * frame_to_sec, 3),
                })
                word_idx += 1
                current_chars = []
        else:
            current_chars.append(span)

    # Last word
    if current_chars and word_idx < len(words):
        word_timings.append({
            "word": words[word_idx],
            "start": round(current_chars[0].start * frame_to_sec, 3),
            "end": round(current_chars[-1].end * frame_to_sec, 3),
        })

    return word_timings


def generate_sync(text: str, voice: str, speed: float, queue: asyncio.Queue, loop):
    """
    Run Kokoro TTS generation synchronously in a thread.

    Generates audio chunk-by-chunk, concatenates into a WAV file, then runs
    forced alignment for exact word-level timestamps.

    Args:
        text: Input text to synthesize
        voice: Voice ID (e.g. 'af_heart')
        speed: Playback speed multiplier (0.5 - 2.0)
        queue: asyncio.Queue for sending progress events to the SSE generator
        loop: The event loop to schedule queue puts on
    """
    try:
        # First pass: count chunks without generating audio
        chunks_preview = list(pipeline(text, voice=voice, speed=speed, model=False))
        total = len(chunks_preview)

        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"event": "info", "data": {"total_chunks": total}},
        )

        # Second pass: generate audio and track chunk text
        audio_chunks = []
        chunk_texts = []

        for i, (gs, ps, audio) in enumerate(pipeline(text, voice=voice, speed=speed)):
            audio_chunks.append(audio)
            chunk_texts.append(gs)

            preview = gs[:80] + "..." if len(gs) > 80 else gs
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "event": "progress",
                    "data": {
                        "chunk": i + 1,
                        "total": total,
                        "text": preview,
                    },
                },
            )

        # Concatenate and save
        full_audio = np.concatenate(audio_chunks)
        filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
        filepath = GENERATED_DIR / filename
        sf.write(str(filepath), full_audio, SAMPLE_RATE)

        duration = len(full_audio) / SAMPLE_RATE

        # Run forced alignment for exact word timestamps
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"event": "progress", "data": {
                "chunk": total, "total": total, "text": "Aligning words..."
            }},
        )

        full_text = " ".join(chunk_texts)
        word_timings = align_audio_to_words(full_audio, full_text)

        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "event": "complete",
                "data": {
                    "url": f"/generated/{filename}",
                    "duration": round(duration, 1),
                    "words": word_timings,
                },
            },
        )
    except Exception as e:
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"event": "error", "data": {"message": str(e)}},
        )


@app.get("/api/generate")
async def generate(
    text: str = Query(..., min_length=1, max_length=50000),
    voice: str = Query("af_heart"),
    speed: float = Query(1.0, ge=0.5, le=2.0),
):
    """
    SSE endpoint for TTS generation with real-time progress.

    Streams progress events as each chunk is generated, then runs forced
    alignment and sends a complete event with word-level timestamps.

    Args:
        text: Text to synthesize
        voice: Voice ID from /api/voices
        speed: Speed multiplier (0.5 to 2.0)

    Returns:
        Server-Sent Events stream with progress and completion data.
        The complete event includes a 'words' array with exact timestamps.
    """
    if voice not in VOICES:
        voice = "af_heart"

    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    asyncio.get_event_loop().run_in_executor(
        None, generate_sync, text, voice, speed, queue, loop
    )

    async def event_stream():
        import json

        while True:
            msg = await queue.get()
            event_type = msg["event"]
            data = json.dumps(msg["data"])
            yield f"event: {event_type}\ndata: {data}\n\n"
            if event_type in ("complete", "error"):
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/generated/{filename}")
async def serve_generated(filename: str):
    """Serve a generated WAV file."""
    filepath = GENERATED_DIR / filename
    if not filepath.exists() or not filepath.suffix == ".wav":
        return JSONResponse({"error": "Not found"}, status_code=404)
    return FileResponse(filepath, media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
