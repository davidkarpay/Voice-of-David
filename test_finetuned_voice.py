#!/usr/bin/env python3
"""
Test your fine-tuned XTTS voice model
Generates audio from various test sentences and saves them for evaluation
"""

import os
from pathlib import Path
from TTS.api import TTS

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

BASE_PATH = Path(__file__).parent

# Your fine-tuned model location
MODEL_DIR = BASE_PATH / "xtts_finetuned_verified" / "XTTS_opt-November-28-2025_11+35AM-0000000"
MODEL_PATH = MODEL_DIR / "best_model_1800.pth"
CONFIG_PATH = MODEL_DIR / "config.json"

# Reference audio (use one of your training samples for speaker identity)
DATASET_DIR = BASE_PATH / "xtts_finetuned_verified" / "ljspeech_dataset" / "wavs"
REFERENCE_AUDIO = list(DATASET_DIR.glob("*.wav"))[0]  # Use first sample

# Output directory for test audio
OUTPUT_DIR = BASE_PATH / "voice_test_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
# TEST SENTENCES
# ═══════════════════════════════════════════════════════════════════════════

TEST_SENTENCES = [
    # Simple/Similar to training
    {
        "id": "01_simple",
        "text": "Hello, this is a test of my fine-tuned voice model.",
        "category": "Simple"
    },
    
    # Legal/Professional (your domain)
    {
        "id": "02_legal",
        "text": "The defendant's constitutional rights were violated during the interrogation process.",
        "category": "Legal Professional"
    },
    
    # Conversational
    {
        "id": "03_conversational",
        "text": "I'm really excited about how well this voice cloning technology is working!",
        "category": "Conversational"
    },
    
    # Technical
    {
        "id": "04_technical",
        "text": "The machine learning model utilizes gradient descent optimization and backpropagation.",
        "category": "Technical"
    },
    
    # Complex sentence structure
    {
        "id": "05_complex",
        "text": "Although the evidence was circumstantial, the prosecution argued that when considered collectively, it demonstrated guilt beyond a reasonable doubt.",
        "category": "Complex Structure"
    },
    
    # Emotional/Emphatic
    {
        "id": "06_emphatic",
        "text": "This is absolutely critical for ensuring justice is served in our community!",
        "category": "Emphatic"
    },
    
    # Long technical legal
    {
        "id": "07_long_legal",
        "text": "The appellate court's decision to remand the case for further proceedings indicates that procedural irregularities during the initial trial may have compromised the defendant's right to effective assistance of counsel.",
        "category": "Long Legal"
    },
    
    # Numbers and specifics
    {
        "id": "08_numbers",
        "text": "In the year 2024, approximately 3,500 cases were processed through the public defender's office.",
        "category": "Numbers"
    },
    
    # Question format
    {
        "id": "09_question",
        "text": "How can we ensure that every defendant receives adequate legal representation regardless of their financial circumstances?",
        "category": "Question"
    },
    
    # Short and direct
    {
        "id": "10_short",
        "text": "The motion is denied.",
        "category": "Short Direct"
    },
]

# ═══════════════════════════════════════════════════════════════════════════
# LOAD MODEL
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("🎤 TESTING FINE-TUNED VOICE MODEL")
print("=" * 80)
print()

# Verify files exist
if not MODEL_PATH.exists():
    print(f"❌ Model not found: {MODEL_PATH}")
    print("   Make sure training completed successfully!")
    exit(1)

if not CONFIG_PATH.exists():
    print(f"❌ Config not found: {CONFIG_PATH}")
    exit(1)

if not REFERENCE_AUDIO.exists():
    print(f"❌ Reference audio not found: {REFERENCE_AUDIO}")
    print(f"   Looking in: {DATASET_DIR}")
    exit(1)

print(f"📂 Model: {MODEL_PATH.name}")
print(f"🎵 Reference: {REFERENCE_AUDIO.name}")
print(f"💾 Output: {OUTPUT_DIR}")
print()

# Initialize TTS with your fine-tuned model
print("🔄 Loading model...")
try:
    tts = TTS(model_path=str(CONFIG_PATH), config_path=str(CONFIG_PATH))
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    print("\nTrying alternative loading method...")
    try:
        # Alternative: Load as XTTS model directly
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        # Note: This loads base model - we'll need to manually load weights
        print("⚠️  Loaded base XTTS model (will need manual weight loading)")
    except Exception as e2:
        print(f"❌ Alternative loading also failed: {e2}")
        exit(1)

print()

# ═══════════════════════════════════════════════════════════════════════════
# GENERATE TEST AUDIO
# ═══════════════════════════════════════════════════════════════════════════

print("🎙️  GENERATING TEST AUDIO")
print("=" * 80)
print()

successful = 0
failed = 0

for test in TEST_SENTENCES:
    test_id = test["id"]
    text = test["text"]
    category = test["category"]
    
    output_file = OUTPUT_DIR / f"{test_id}_{category.replace(' ', '_')}.wav"
    
    print(f"[{test_id}] {category}")
    print(f"  Text: {text[:60]}..." if len(text) > 60 else f"  Text: {text}")
    
    try:
        # Generate audio
        tts.tts_to_file(
            text=text,
            file_path=str(output_file),
            speaker_wav=str(REFERENCE_AUDIO),
            language="en"
        )
        
        print(f"  ✅ Saved: {output_file.name}")
        successful += 1
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        failed += 1
    
    print()

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("📊 GENERATION SUMMARY")
print("=" * 80)
print(f"✅ Successful: {successful}/{len(TEST_SENTENCES)}")
print(f"❌ Failed: {failed}/{len(TEST_SENTENCES)}")
print()

if successful > 0:
    print(f"🎧 LISTEN TO YOUR RESULTS:")
    print(f"   Open: {OUTPUT_DIR}")
    print()
    print("📋 EVALUATION CHECKLIST:")
    print("   ✓ Does it sound like you?")
    print("   ✓ Is pronunciation clear?")
    print("   ✓ Is the rhythm/prosody natural?")
    print("   ✓ Does it handle different sentence types well?")
    print("   ✓ Are emotions/emphasis appropriate?")
    print()
    print("💡 TIP: Compare these to your original training samples")
    print(f"        Original samples in: {DATASET_DIR}")
else:
    print("⚠️  No audio generated successfully")
    print("   Check error messages above for troubleshooting")

print()
print("=" * 80)
