# Quick Start Guide - Voice Recording System

## Before You Start

1. **Audacity Setup** (one-time only):
   - Audacity → Preferences → Modules
   - Set mod-script-pipe to "Enabled"
   - Restart Audacity
   
2. **Each Recording Session**:
   - Make sure Audacity is running
   - Use the same quiet environment as your first 40 recordings
   - Have water nearby (vocal health!)

## Starting a Recording Session
```bash
cd ~/Desktop/TTS
# Note: TTS_venv was removed during disk cleanup (2026-03-11).
# To use XTTS tools again, create a new venv and install coqui-tts:
#   python3 -m venv xtts_env && source xtts_env/bin/activate && pip install coqui-tts
source xtts_env/bin/activate
python recording_assistant.py
```

## How It Works

### Session Selection
- Choose a session (1-5) or continue from where you left off
- Each session has 40 sentences with a specific focus
- Progress is saved automatically

### Recording Workflow
For each sentence:
1. Sentence appears on screen
2. Press ENTER when ready
3. 3-second countdown
4. Read naturally (don't rush, don't perform)
5. Press ENTER when done speaking
6. Review in Audacity
7. Choose: Keep (y), Re-record (n), or Quit (q)

### What Happens Automatically
- ✅ Recording is labeled with the sentence text
- ✅ Audio exported as item_041.wav, item_042.wav, etc.
- ✅ Metadata saved (filename + transcript + date)
- ✅ Progress tracked (can resume anytime)
- ✅ Statistics updated

## Tips for Best Results

**Voice Quality**:
- Speak naturally, as if talking to a friend
- Maintain consistent distance from microphone
- Don't read in a "reading voice" - just talk
- It's okay to take breaks between sentences

**Session Management**:
- 40 sentences ≈ 30-45 minutes per session
- Take breaks between sessions to avoid vocal fatigue
- You don't have to complete all 5 sessions in one day

**If Something Goes Wrong**:
- Press 'q' to quit - progress is auto-saved
- Re-record anytime if you're not satisfied
- Skip problematic sentences with 's' (you can return later)

## Files Created

**Your recordings**: `~/Desktop/TTS/dataset_expanded/item_041.wav` through `item_240.wav`

**Metadata**: `~/Desktop/TTS/dataset_expanded/metadata.json`
- Contains filename, text, and recording date for each sample
- Already formatted for training - no manual work needed

**Progress**: `~/Desktop/TTS/recording_progress.json`
- Tracks which session you're on
- Remembers your position within each session
- Total count of recordings

## After Recording

When you complete all 5 sessions (200 sentences):
- You'll have ~4-6 hours of total audio (including original 40 samples)
- Combined with 7-reference inference, this should give excellent voice quality
- Ready for fine-tuning when you decide to retrain

## Troubleshooting

**"Cannot find Audacity script pipes"**
- Make sure Audacity is actually running
- Verify mod-script-pipe is Enabled in Preferences
- Restart Audacity after enabling

**Recording doesn't start**
- Check that your microphone is selected in Audacity
- Verify input levels are showing in Audacity

**Export fails**
- Make sure dataset_expanded directory exists
- Check disk space

## Session Descriptions

**Session 1** - Phonetically Balanced: Everyday observations covering all English sounds

**Session 2** - Questions & Conversation: Natural questions to capture interrogative intonation

**Session 3** - Expressive Range: Emotional variety and emphatic expressions

**Session 4** - Professional Language: Technical vocabulary with natural delivery

**Session 5** - Narrative Speech: Flowing descriptive language and storytelling rhythm
