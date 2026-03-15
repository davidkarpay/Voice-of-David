"""
server.py

FastAPI backend for the Kokoro TTS web interface. Loads the Kokoro 82M model
once at startup, accepts text + voice via an SSE endpoint, generates audio
chunk-by-chunk with real-time progress reporting, and serves the resulting WAV.

Part of: Kokoro TTS Web UI
See: index.html for the frontend

Dependencies:
    - fastapi/uvicorn: HTTP server and ASGI
    - kokoro: TTS model pipeline (82M params, Apache 2.0)
    - soundfile: WAV file writing
    - numpy: audio array concatenation

Author: David Karpay
Created: 2026-03-13
Last Modified: 2026-03-15
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from starlette.responses import StreamingResponse

SAMPLE_RATE = 24000
GENERATED_DIR = Path(__file__).parent / "generated"
INDEX_HTML = Path(__file__).parent / "index.html"

VOICES = {
    "af_heart": "Heart (American female)",
    "af_nova": "Nova (American female)",
    "bm_george": "George (British male)",
}

pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Kokoro pipeline once at startup."""
    global pipeline
    import kokoro

    print("Loading Kokoro pipeline...")
    pipeline = kokoro.KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")

    # Pre-load voices so first request isn't slow
    for voice_id in VOICES:
        try:
            pipeline.load_voice(voice_id)
            print(f"  Loaded voice: {voice_id}")
        except Exception:
            pass

    GENERATED_DIR.mkdir(exist_ok=True)

    # Clean up old generated files (>1 hour)
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


def generate_sync(text: str, voice: str, speed: float, queue: asyncio.Queue, loop):
    """
    Run Kokoro TTS generation synchronously in a thread.

    Sends progress events to the async queue for SSE streaming.

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

        # Second pass: generate audio and track chunk timing
        audio_chunks = []
        chunk_timing = []  # [{text, start, end}, ...]
        cumulative_samples = 0

        for i, (gs, ps, audio) in enumerate(pipeline(text, voice=voice, speed=speed)):
            audio_chunks.append(audio)
            chunk_start = cumulative_samples / SAMPLE_RATE
            cumulative_samples += len(audio)
            chunk_end = cumulative_samples / SAMPLE_RATE

            chunk_timing.append({
                "text": gs,
                "start": round(chunk_start, 3),
                "end": round(chunk_end, 3),
            })

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
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "event": "complete",
                "data": {
                    "url": f"/generated/{filename}",
                    "duration": round(duration, 1),
                    "chunks": chunk_timing,
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

    Streams progress events as each chunk is generated, then a
    complete event with the URL to the generated WAV file.

    Args:
        text: Text to synthesize
        voice: Voice ID from /api/voices
        speed: Speed multiplier (0.5 to 2.0)

    Returns:
        Server-Sent Events stream with progress and completion data
    """
    if voice not in VOICES:
        voice = "af_heart"

    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    # Run generation in a thread to avoid blocking
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
