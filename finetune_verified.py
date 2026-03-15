#!/usr/bin/env python3
"""
Fine-tune XTTS v2 GPT encoder on your 40 audio samples.
Based DIRECTLY on official recipe: recipes/ljspeech/xtts_v2/train_gpt_xtts.py

Key insight: GPTTrainer is the MODEL, Trainer handles the training loop.
"""
import os
import sys
import json
import shutil
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: IMPORTS (EXACTLY MATCHING OFFICIAL RECIPE)
# ═══════════════════════════════════════════════════════════════════════════

try:
    from trainer import Trainer, TrainerArgs
    
    from TTS.config.shared_configs import BaseDatasetConfig
    from TTS.tts.datasets import load_tts_samples
    from TTS.tts.layers.xtts.trainer.gpt_trainer import GPTArgs, GPTTrainer, GPTTrainerConfig, XttsAudioConfig
    from TTS.utils.manage import ModelManager
    
    print("✅ All imports successful!")
    
except ImportError as e:
    print("❌ Import failed!")
    print(f"   Error: {e}")
    print("\n📦 Make sure you're in the virtual environment:")
    print("   source TTS_venv/bin/activate")
    print("   pip install -e .")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: PATH CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

BASE_PATH = Path(__file__).parent
DATASET_DIR = BASE_PATH / "dataset_40_items"
OUT_PATH = str(BASE_PATH / "xtts_finetuned_verified")
CHECKPOINTS_OUT_PATH = os.path.join(OUT_PATH, "XTTS_v2.0_original_model_files")

# Create directories
os.makedirs(OUT_PATH, exist_ok=True)
os.makedirs(CHECKPOINTS_OUT_PATH, exist_ok=True)

print(f"📁 Base path: {BASE_PATH}")
print(f"📁 Dataset: {DATASET_DIR}")
print(f"📁 Output: {OUT_PATH}")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: DOWNLOAD MODEL FILES (FROM OFFICIAL RECIPE)
# ═══════════════════════════════════════════════════════════════════════════

# DVAE files
DVAE_CHECKPOINT_LINK = "https://coqui.gateway.scarf.sh/hf-coqui/XTTS-v2/main/dvae.pth"
MEL_NORM_LINK = "https://coqui.gateway.scarf.sh/hf-coqui/XTTS-v2/main/mel_stats.pth"

# XTTS files
TOKENIZER_FILE_LINK = "https://coqui.gateway.scarf.sh/hf-coqui/XTTS-v2/main/vocab.json"
XTTS_CHECKPOINT_LINK = "https://coqui.gateway.scarf.sh/hf-coqui/XTTS-v2/main/model.pth"

# Set paths
DVAE_CHECKPOINT = os.path.join(CHECKPOINTS_OUT_PATH, "dvae.pth")
MEL_NORM_FILE = os.path.join(CHECKPOINTS_OUT_PATH, "mel_stats.pth")
TOKENIZER_FILE = os.path.join(CHECKPOINTS_OUT_PATH, "vocab.json")
XTTS_CHECKPOINT = os.path.join(CHECKPOINTS_OUT_PATH, "model.pth")

print("\n📦 Checking model files...")

# Download DVAE files if needed
if not os.path.isfile(DVAE_CHECKPOINT) or not os.path.isfile(MEL_NORM_FILE):
    print(" > Downloading DVAE files...")
    ModelManager._download_model_files([MEL_NORM_LINK, DVAE_CHECKPOINT_LINK], CHECKPOINTS_OUT_PATH, progress_bar=True)
else:
    print(f"   ✅ DVAE files present")

# Download XTTS v2.0 files if needed
if not os.path.isfile(TOKENIZER_FILE) or not os.path.isfile(XTTS_CHECKPOINT):
    print(" > Downloading XTTS v2.0 files...")
    ModelManager._download_model_files([TOKENIZER_FILE_LINK, XTTS_CHECKPOINT_LINK], CHECKPOINTS_OUT_PATH, progress_bar=True)
else:
    print(f"   ✅ XTTS model files present")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: DATASET PREPARATION (Convert to LJSpeech format)
# ═══════════════════════════════════════════════════════════════════════════

def prepare_ljspeech_dataset():
    """Convert your dataset to LJSpeech format."""
    print("\n📊 Preparing dataset...")
    
    ljspeech_dir = Path(OUT_PATH) / "ljspeech_dataset"
    wavs_dir = ljspeech_dir / "wavs"
    metadata_csv = ljspeech_dir / "metadata.csv"
    
    # Check if already prepared
    if metadata_csv.exists():
        existing_wavs = list(wavs_dir.glob("*.wav"))
        if len(existing_wavs) >= 40:
            print(f"   ✅ Dataset already prepared ({len(existing_wavs)} files)")
            return str(ljspeech_dir), str(metadata_csv)
    
    # Create directories
    ljspeech_dir.mkdir(exist_ok=True)
    wavs_dir.mkdir(exist_ok=True)
    
    # Load transcripts from metadata.json
    metadata_json = DATASET_DIR / "metadata.json"
    
    if not metadata_json.exists():
        print("❌ metadata.json not found!")
        sys.exit(1)
    
    print("   Loading metadata.json...")
    with open(metadata_json, 'r') as f:
        data = json.load(f)
    
    transcripts = {}
    for item in data:
        key = item['audio_file'].replace('.wav', '')
        transcripts[key] = item['text']
    
    print(f"   Found {len(transcripts)} transcripts")
    
    # Find audio files
    audio_files = sorted(DATASET_DIR.glob("item_*.wav"))
    print(f"   Found {len(audio_files)} audio files")
    
    # Create LJSpeech format
    metadata_lines = []
    copied = 0
    
    for audio_file in audio_files:
        filename_base = audio_file.stem
        transcript = transcripts.get(filename_base, '')
        
        if not transcript:
            print(f"   ⚠️  No transcript for {filename_base}")
            continue
        
        # Copy audio file
        dest_file = wavs_dir / audio_file.name
        if not dest_file.exists():
            shutil.copy2(audio_file, dest_file)
        
        # Create metadata line (LJSpeech format: filename|normalized|original)
        normalized = transcript.lower()
        for char in '.,!?;:"-()\'':
            normalized = normalized.replace(char, '')
        normalized = ' '.join(normalized.split())
        
        metadata_lines.append(f"{filename_base}|{normalized}|{transcript}")
        copied += 1
    
    # Write metadata.csv
    with open(metadata_csv, 'w') as f:
        f.write('\n'.join(metadata_lines))
    
    print(f"   ✅ Prepared {copied} samples in LJSpeech format")
    return str(ljspeech_dir), str(metadata_csv)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: MAIN TRAINING FUNCTION (FOLLOWING OFFICIAL RECIPE EXACTLY)
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 70)
    print("  XTTS v2 FINE-TUNING (OFFICIAL RECIPE)")
    print("=" * 70)
    
    # Prepare dataset
    ljspeech_path, metadata_path = prepare_ljspeech_dataset()
    
    # Get speaker reference (first audio file)
    wavs_dir = Path(ljspeech_path) / "wavs"
    SPEAKER_REFERENCE = [str(list(wavs_dir.glob("*.wav"))[0])]
    LANGUAGE = "en"
    
    print(f"\n🎤 Speaker reference: {Path(SPEAKER_REFERENCE[0]).name}")
    
    # Training parameters (adjusted for Mac with 40 samples)
    BATCH_SIZE = 2  # Small for Mac memory
    GRAD_ACUMM_STEPS = 126  # Effective batch: 2 * 126 = 252
    
    # Dataset config
    config_dataset = BaseDatasetConfig(
        formatter="ljspeech",
        dataset_name="david_voice",
        path=ljspeech_path,
        meta_file_train=metadata_path,
        language="en",
    )
    
    print("\n⚙️  Configuring training...")
    
    # Model args (from official recipe)
    model_args = GPTArgs(
        max_conditioning_length=132300,  # 6 secs
        min_conditioning_length=66150,   # 3 secs
        debug_loading_failures=False,
        max_wav_length=255995,           # ~11.6 seconds
        max_text_length=200,
        mel_norm_file=MEL_NORM_FILE,
        dvae_checkpoint=DVAE_CHECKPOINT,
        xtts_checkpoint=XTTS_CHECKPOINT,
        tokenizer_file=TOKENIZER_FILE,
        gpt_num_audio_tokens=1026,
        gpt_start_audio_token=1024,
        gpt_stop_audio_token=1025,
        gpt_use_masking_gt_prompt_approach=True,
        gpt_use_perceiver_resampler=True,
    )
    
    # Audio config
    audio_config = XttsAudioConfig(
        sample_rate=22050,
        dvae_sample_rate=22050,
        output_sample_rate=24000
    )
    
    # Training config
    config = GPTTrainerConfig(
        output_path=OUT_PATH,
        model_args=model_args,
        run_name="XTTS_david_voice_FT",
        project_name="XTTS_finetuning",
        run_description="Fine-tuning XTTS v2 on David's voice (40 samples)",
        dashboard_logger="tensorboard",
        audio=audio_config,
        batch_size=BATCH_SIZE,
        batch_group_size=48,
        eval_batch_size=BATCH_SIZE,
        num_loader_workers=2,  # Reduced for Mac
        eval_split_size=0.1,  # 10% for evaluation = 4 samples
        eval_split_max_size=256,
        print_step=25,
        plot_step=100,
        log_model_step=500,
        save_step=500,          # Save more frequently for small dataset
        save_n_checkpoints=3,
        save_checkpoints=True,
        print_eval=True,
        # Optimizer (from official recipe)
        optimizer="AdamW",
        optimizer_wd_only_on_weights=False,  # False for single GPU
        optimizer_params={"betas": [0.9, 0.96], "eps": 1e-8, "weight_decay": 1e-2},
        lr=5e-06,
        lr_scheduler="MultiStepLR",
        lr_scheduler_params={"milestones": [50000, 150000, 300000], "gamma": 0.5, "last_epoch": -1},
        test_sentences=[
            {
                "text": "This is a test of my fine-tuned voice cloning model.",
                "speaker_wav": SPEAKER_REFERENCE,
                "language": LANGUAGE,
            },
            {
                "text": "The quick brown fox jumps over the lazy dog.",
                "speaker_wav": SPEAKER_REFERENCE,
                "language": LANGUAGE,
            },
        ],
    )
    
    print("   ✅ Configuration complete")
    print(f"   - Batch size: {BATCH_SIZE} (effective: {BATCH_SIZE * GRAD_ACUMM_STEPS})")
    print(f"   - Learning rate: {config.lr}")
    
    # Initialize model
    print("\n🚀 Initializing model from config...")
    model = GPTTrainer.init_from_config(config)
    print("   ✅ Model initialized")
    
    # Load training samples
    print("\n📂 Loading training samples...")
    train_samples, eval_samples = load_tts_samples(
        [config_dataset],
        eval_split=True,
        eval_split_max_size=config.eval_split_max_size,
        eval_split_size=config.eval_split_size,
    )
    print(f"   Training samples: {len(train_samples)}")
    print(f"   Evaluation samples: {len(eval_samples)}")
    
    # Initialize trainer (THIS IS THE KEY - use Trainer class!)
    print("\n🏋️ Initializing trainer...")
    trainer = Trainer(
        TrainerArgs(
            restore_path=None,
            skip_train_epoch=False,
            start_with_eval=True,
            grad_accum_steps=GRAD_ACUMM_STEPS,
        ),
        config,
        output_path=OUT_PATH,
        model=model,
        train_samples=train_samples,
        eval_samples=eval_samples,
    )
    print("   ✅ Trainer ready")
    
    # START TRAINING!
    print("\n" + "=" * 70)
    print("  🚀 STARTING TRAINING")
    print("  Estimated time: 30-90 minutes")
    print("  Press Ctrl+C to stop (progress will be saved)")
    print("=" * 70 + "\n")
    
    trainer.fit()
    
    print("\n" + "=" * 70)
    print("  ✅ TRAINING COMPLETE!")
    print("=" * 70)
    print(f"\n📁 Model saved to: {OUT_PATH}")

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("XTTS v2 Fine-tuning Script")
        print("\nUsage: python finetune_verified.py")
        print("\nFine-tunes XTTS v2 on your 40-item dataset.")
        print("Based directly on official recipe: recipes/ljspeech/xtts_v2/train_gpt_xtts.py")
        sys.exit(0)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
        print("Progress has been saved to checkpoints.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
