#!/usr/bin/env python3
"""Pre-flight check - verify training setup without actually training"""
import os
from pathlib import Path

print("=" * 80)
print("TTS TRAINING PRE-FLIGHT CHECK")
print("=" * 80)

# Check 1: Directory structure
print("\n[1/6] Checking directory structure...")
base_path = Path.cwd()
dataset_dir = base_path / "dataset_40_items"
assert dataset_dir.exists(), "❌ Dataset directory not found!"
print(f"✓ Base path: {base_path}")
print(f"✓ Dataset: {dataset_dir}")

# Check 2: Audio files
print("\n[2/6] Checking audio files...")
wav_files = list(dataset_dir.glob("*.wav"))
print(f"✓ Found {len(wav_files)} audio files")
assert len(wav_files) >= 30, f"❌ Only {len(wav_files)} files (need 30+)"

# Check 3: Metadata
print("\n[3/6] Checking metadata...")
metadata_json = dataset_dir / "metadata.json"
metadata_txt = dataset_dir / "metadata.txt"
has_metadata = metadata_json.exists() or metadata_txt.exists()
assert has_metadata, "❌ No metadata file found!"
print(f"✓ Metadata: {metadata_json.name if metadata_json.exists() else metadata_txt.name}")

# Check 4: Python packages
print("\n[4/6] Checking Python packages...")
try:
    import torch
    print(f"✓ PyTorch {torch.__version__}")
    print(f"✓ MPS available: {torch.backends.mps.is_available()}")
except ImportError as e:
    print(f"❌ PyTorch: {e}")

try:
    from TTS.tts.layers.xtts.trainer.gpt_trainer import GPTTrainer
    print("✓ TTS library installed")
except ImportError as e:
    print(f"❌ TTS library: {e}")

# Check 5: Disk space
print("\n[5/6] Checking disk space...")
import shutil
stat = shutil.disk_usage(base_path)
free_gb = stat.free / (1024**3)
print(f"✓ Free disk space: {free_gb:.1f} GB")
assert free_gb > 10, f"❌ Only {free_gb:.1f} GB free (need 10+ GB)"

# Check 6: File access
print("\n[6/6] Checking file accessibility...")
test_file = wav_files[0]
try:
    import wave
    with wave.open(str(test_file), 'r') as w:
        frames = w.readframes(100)
    print(f"✓ Files are local and readable (not iCloud placeholders)")
except Exception as e:
    print(f"❌ Cannot read audio files: {e}")

print("\n" + "=" * 80)
print("✅ PRE-FLIGHT CHECK COMPLETE - READY FOR TRAINING!")
print("=" * 80)
print("\nNext step: python finetune_verified.py")
