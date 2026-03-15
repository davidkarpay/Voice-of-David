#!/usr/bin/env python3
"""
Multi-Reference Voice Cloning Test
===================================
Tests your fine-tuned model with different numbers of reference samples
to see if more references improve voice quality.
"""

from pathlib import Path
import torch
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import random

# Paths
BASE_DIR = Path("/Users/davidluciankarpay/Desktop/TTS/xtts_finetuned_verified")
FINETUNED_MODEL_DIR = BASE_DIR / "XTTS_opt-November-28-2025_11+35AM-0000000"
DATASET_DIR = BASE_DIR / "ljspeech_dataset" / "wavs"
ORIGINAL_MODEL_DIR = BASE_DIR / "XTTS_v2.0_original_model_files"
OUTPUT_DIR = Path("/Users/davidluciankarpay/Desktop/TTS")

# Test sentences - different from training data
TEST_SENTENCES = [
    "Hello, this is a test of my voice with multiple reference samples.",
    "I'm curious to see how well this fine-tuned model can capture my speaking style.",
    "The weather today is absolutely beautiful, perfect for a long walk outside.",
]

print("=" * 80)
print("MULTI-REFERENCE VOICE CLONING TEST")
print("=" * 80)
print("\n🎯 Goal: Test if using multiple reference samples improves voice quality")
print("         with your 50-epoch fine-tuned model")
print("\n" + "=" * 80)

# Get all your audio samples
all_samples = sorted(list(DATASET_DIR.glob("item_*.wav")))
print(f"\n📁 Found {len(all_samples)} audio samples in your dataset")

# Load model once
print("\n🔄 Loading your fine-tuned model...")
config = XttsConfig()
config.load_json(str(FINETUNED_MODEL_DIR / "config.json"))

model = Xtts.init_from_config(config)
model.load_checkpoint(
    config,
    checkpoint_dir=str(FINETUNED_MODEL_DIR),
    checkpoint_path=str(FINETUNED_MODEL_DIR / "best_model_1800.pth"),
    vocab_path=str(ORIGINAL_MODEL_DIR / "vocab.json"),
    eval=True,
    use_deepspeed=False
)

if torch.backends.mps.is_available():
    model = model.to("mps")
elif torch.cuda.is_available():
    model.cuda()

print("✅ Model loaded successfully\n")

def generate_with_references(text, reference_files, output_name):
    """Generate audio using multiple reference samples"""
    print(f"\n🎙️  Generating: {output_name}")
    print(f"   References: {len(reference_files)} samples")
    print(f"   Text: {text[:50]}...")
    
    # Convert paths to strings
    speaker_wavs = [str(f) for f in reference_files]
    
    outputs = model.synthesize(
        text,
        config,
        speaker_wav=speaker_wavs,  # Pass list of reference files
        language="en",
        temperature=0.7,
        length_penalty=1.0,
        repetition_penalty=5.0,
        top_k=50,
        top_p=0.85,
    )
    
    # Save audio
    import torchaudio
    output_path = OUTPUT_DIR / output_name
    torchaudio.save(
        str(output_path),
        torch.tensor(outputs["wav"]).unsqueeze(0),
        24000
    )
    
    print(f"   ✅ Saved: {output_name}")
    return output_path

# Test with different numbers of references
print("\n" + "=" * 80)
print("RUNNING TESTS")
print("=" * 80)

# Randomly select diverse reference samples
random.seed(42)  # For reproducibility
reference_pool = random.sample(all_samples, min(10, len(all_samples)))

test_configs = [
    (1, "single reference (baseline)"),
    (3, "3 references"),
    (5, "5 references"),
    (7, "7 references (if available)"),
]

results = []

for test_num, test_sentence in enumerate(TEST_SENTENCES, 1):
    print(f"\n{'=' * 80}")
    print(f"TEST SENTENCE {test_num}: \"{test_sentence}\"")
    print("=" * 80)
    
    for num_refs, description in test_configs:
        if num_refs > len(reference_pool):
            print(f"\n⚠️  Skipping {num_refs} references (only {len(reference_pool)} available)")
            continue
        
        refs = reference_pool[:num_refs]
        output_name = f"test{test_num}_{num_refs}ref.wav"
        
        try:
            generate_with_references(test_sentence, refs, output_name)
            results.append({
                'test': test_num,
                'refs': num_refs,
                'file': output_name,
                'description': description
            })
        except Exception as e:
            print(f"   ❌ Error: {e}")

# Cleanup
del model
if torch.backends.mps.is_available():
    torch.mps.empty_cache()

# Summary
print("\n" + "=" * 80)
print("✅ TESTING COMPLETE!")
print("=" * 80)
print(f"\n📊 Generated {len(results)} test audio files")
print(f"📂 Location: {OUTPUT_DIR}")
print("\n🎧 Listen to the files in order to compare:")
print("\nFor each test sentence, compare:")

for test_num in range(1, len(TEST_SENTENCES) + 1):
    print(f"\n📝 Test Sentence {test_num}:")
    test_results = [r for r in results if r['test'] == test_num]
    for r in sorted(test_results, key=lambda x: x['refs']):
        print(f"   • test{r['test']}_{r['refs']}ref.wav  ({r['description']})")

print("\n💡 WHAT TO LISTEN FOR:")
print("   • Does voice quality improve with more references?")
print("   • Is there a sweet spot (3, 5, or 7 references)?")
print("   • Does pronunciation get more accurate?")
print("   • Does prosody/rhythm sound more natural?")
print("\n" + "=" * 80)
