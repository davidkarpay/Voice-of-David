#!/usr/bin/env python3
"""
Compare Pre-trained vs Fine-tuned XTTS Models
==============================================
Generates audio from both models using the same text and reference audio.
"""

import os
from pathlib import Path
import torch
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

# Paths
BASE_DIR = Path("/Users/davidluciankarpay/Desktop/TTS/xtts_finetuned_verified")
ORIGINAL_MODEL_DIR = BASE_DIR / "XTTS_v2.0_original_model_files"
FINETUNED_MODEL_DIR = BASE_DIR / "XTTS_opt-November-28-2025_11+35AM-0000000"
DATASET_DIR = BASE_DIR / "ljspeech_dataset" / "wavs"

# Output paths
OUTPUT_DIR = Path("/Users/davidluciankarpay/Desktop/TTS")
BASE_OUTPUT = OUTPUT_DIR / "1_pretrained_base_model.wav"
FINETUNED_OUTPUT = OUTPUT_DIR / "2_finetuned_50epochs.wav"

# Test configuration
TEST_TEXT = "The quick brown fox jumps over the lazy dog. This is a test of voice quality and naturalness."
# Use one of your recorded samples as reference
REFERENCE_AUDIO = list(DATASET_DIR.glob("item_001.wav"))[0]

print("=" * 80)
print("XTTS MODEL COMPARISON")
print("=" * 80)
print(f"\n📝 Test Text: '{TEST_TEXT}'")
print(f"🎤 Reference Audio: {REFERENCE_AUDIO.name}")
print(f"\n🔍 Models to compare:")
print(f"   1. Pre-trained base model (before any training)")
print(f"   2. Your 50-epoch fine-tuned model")
print("\n" + "=" * 80)

# Load configuration from the training output directory
config = XttsConfig()
config.load_json(str(FINETUNED_MODEL_DIR / "config.json"))

def generate_audio(model_path, output_path, model_name):
    """Generate audio using specified model checkpoint"""
    print(f"\n🔄 Loading {model_name}...")
    print(f"   Model: {model_path.name}")
    
    # Initialize model
    model = Xtts.init_from_config(config)
    model.load_checkpoint(
        config,
        checkpoint_dir=str(model_path.parent),
        checkpoint_path=str(model_path),
        vocab_path=str(ORIGINAL_MODEL_DIR / "vocab.json"),
        eval=True,
        use_deepspeed=False
    )
    
    # Move to appropriate device
    if torch.cuda.is_available():
        model.cuda()
    elif torch.backends.mps.is_available():
        model = model.to("mps")
    
    print(f"✅ Model loaded successfully")
    print(f"🎙️  Generating speech...")
    
    # Generate speech
    outputs = model.synthesize(
        TEST_TEXT,
        config,
        speaker_wav=str(REFERENCE_AUDIO),
        language="en",
        temperature=0.7,
        length_penalty=1.0,
        repetition_penalty=5.0,
        top_k=50,
        top_p=0.85,
    )
    
    # Save audio
    import torchaudio
    torchaudio.save(
        str(output_path),
        torch.tensor(outputs["wav"]).unsqueeze(0),
        24000
    )
    
    print(f"💾 Saved: {output_path.name}")
    
    # Cleanup
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif torch.backends.mps.is_available():
        torch.mps.empty_cache()
    
    return output_path

try:
    # Generate with pre-trained base model
    print("\n" + "=" * 80)
    print("STEP 1: Pre-trained Base Model (before your training)")
    print("=" * 80)
    generate_audio(
        ORIGINAL_MODEL_DIR / "model.pth",
        BASE_OUTPUT,
        "Pre-trained Base Model"
    )
    
    # Generate with fine-tuned model
    print("\n" + "=" * 80)
    print("STEP 2: Your Fine-tuned Model (after 50 epochs)")
    print("=" * 80)
    
    # Use the best checkpoint
    generate_audio(
        FINETUNED_MODEL_DIR / "best_model_1800.pth",
        FINETUNED_OUTPUT,
        "Fine-tuned Model (50 epochs)"
    )
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ COMPARISON COMPLETE!")
    print("=" * 80)
    print(f"\n🎧 Listen to the results:")
    print(f"\n   1️⃣  Pre-trained base:  {BASE_OUTPUT.name}")
    print(f"   2️⃣  Fine-tuned (50ep):  {FINETUNED_OUTPUT.name}")
    print(f"\n📂 Location: {OUTPUT_DIR}")
    print("\n💡 The fine-tuned model should sound more like YOUR voice!")
    print("   The base model will sound like the generic XTTS v2 voice.")
    print("\n" + "=" * 80)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
