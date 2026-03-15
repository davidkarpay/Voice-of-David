#!/usr/bin/env python3
"""MEMORY-OPTIMIZED for 16GB Mac"""
import os, sys, json, shutil
from pathlib import Path

try:
    from trainer import Trainer, TrainerArgs
    from TTS.config.shared_configs import BaseDatasetConfig
    from TTS.tts.datasets import load_tts_samples
    from TTS.tts.layers.xtts.trainer.gpt_trainer import GPTArgs, GPTTrainer, GPTTrainerConfig, XttsAudioConfig
    from TTS.utils.manage import ModelManager
    print("✅ Imports OK")
except ImportError as e:
    print(f"❌ {e}"); sys.exit(1)

BASE_PATH = Path(__file__).parent
DATASET_DIR = BASE_PATH / "dataset_40_items"
OUT_PATH = str(BASE_PATH / "xtts_finetuned_verified")
CHECKPOINTS_OUT_PATH = os.path.join(OUT_PATH, "XTTS_v2.0_original_model_files")
os.makedirs(OUT_PATH, exist_ok=True)
os.makedirs(CHECKPOINTS_OUT_PATH, exist_ok=True)

DVAE_CHECKPOINT = os.path.join(CHECKPOINTS_OUT_PATH, "dvae.pth")
MEL_NORM_FILE = os.path.join(CHECKPOINTS_OUT_PATH, "mel_stats.pth")
TOKENIZER_FILE = os.path.join(CHECKPOINTS_OUT_PATH, "vocab.json")
XTTS_CHECKPOINT = os.path.join(CHECKPOINTS_OUT_PATH, "model.pth")

def prep_dataset():
    ljspeech_dir = Path(OUT_PATH) / "ljspeech_dataset"
    wavs_dir = ljspeech_dir / "wavs"
    metadata_csv = ljspeech_dir / "metadata.csv"
    if metadata_csv.exists() and len(list(wavs_dir.glob("*.wav"))) >= 40:
        return str(ljspeech_dir), str(metadata_csv)
    ljspeech_dir.mkdir(exist_ok=True)
    wavs_dir.mkdir(exist_ok=True)
    with open(DATASET_DIR / "metadata.json") as f:
        data = json.load(f)
    transcripts = {item['audio_file'].replace('.wav',''): item['text'] for item in data}
    lines = []
    for af in sorted(DATASET_DIR.glob("item_*.wav")):
        t = transcripts.get(af.stem, '')
        if not t: continue
        dest = wavs_dir / af.name
        if not dest.exists(): shutil.copy2(af, dest)
        # Normalize text: lowercase, remove punctuation, normalize spaces
        normalized_text = t.lower()
        for char in '.,!?;:"-()\'':
            normalized_text = normalized_text.replace(char, '')
        normalized_text = ' '.join(normalized_text.split())
        lines.append(f"{af.stem}|{normalized_text}|{t}")
    with open(metadata_csv, 'w') as f:
        f.write('\n'.join(lines))
    return str(ljspeech_dir), str(metadata_csv)

def main():
    print("\n🚀 MEMORY-OPTIMIZED: batch=1, workers=0, 50 epochs\n")
    lj_path, meta_path = prep_dataset()
    wavs = Path(lj_path) / "wavs"
    SPEAKER_REF = [str(list(wavs.glob("*.wav"))[0])]
    
    model_args = GPTArgs(
        max_conditioning_length=132300, min_conditioning_length=66150,
        max_wav_length=255995, max_text_length=200,
        mel_norm_file=MEL_NORM_FILE, dvae_checkpoint=DVAE_CHECKPOINT,
        xtts_checkpoint=XTTS_CHECKPOINT, tokenizer_file=TOKENIZER_FILE,
        gpt_num_audio_tokens=1026, gpt_start_audio_token=1024, gpt_stop_audio_token=1025,
        gpt_use_masking_gt_prompt_approach=True, gpt_use_perceiver_resampler=True,
    )
    
    config = GPTTrainerConfig(
        epochs=50, output_path=OUT_PATH, model_args=model_args,
        run_name="XTTS_opt", dashboard_logger="tensorboard",
        audio=XttsAudioConfig(sample_rate=22050, dvae_sample_rate=22050, output_sample_rate=24000),
        batch_size=1, batch_group_size=48, eval_batch_size=1,
        num_loader_workers=0, eval_split_size=0.1, eval_split_max_size=256,
        print_step=10, plot_step=500, save_step=5000, save_n_checkpoints=1,
        optimizer="AdamW", optimizer_params={"betas": [0.9, 0.96], "eps": 1e-8, "weight_decay": 1e-2},
        lr=5e-06, lr_scheduler="MultiStepLR",
        lr_scheduler_params={"milestones": [50000, 150000, 300000], "gamma": 0.5},
        test_sentences=[{"text": "Test of my fine-tuned voice.", "speaker_wav": SPEAKER_REF, "language": "en"}],
    )
    
    model = GPTTrainer.init_from_config(config)
    train_s, eval_s = load_tts_samples([BaseDatasetConfig(
        formatter="ljspeech", dataset_name="dv", path=lj_path,
        meta_file_train=meta_path, language="en")],
        eval_split=True, eval_split_max_size=256, eval_split_size=0.1)
    
    trainer = Trainer(TrainerArgs(grad_accum_steps=252, start_with_eval=False),
        config, output_path=OUT_PATH, model=model, train_samples=train_s, eval_samples=eval_s)
    
    print(f"📊 Training: {len(train_s)}, Eval: {len(eval_s)}")
    print(f"⏱️  Estimated: ~75 min for 50 epochs\n")
    trainer.fit()
    print("\n✅ DONE!")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n⚠️ Stopped")
    except Exception as e: print(f"\n❌ {e}"); import traceback; traceback.print_exc()
