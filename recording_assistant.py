#!/usr/bin/env python3
"""
Voice Recording Assistant with Audacity Integration
===================================================
Guides you through recording sessions with automatic labeling and metadata tracking.
"""

import json
import time
import os
from pathlib import Path
from datetime import datetime

# Configuration
BASE_DIR = Path.home() / "Desktop" / "TTS"
SENTENCES_FILE = BASE_DIR / "recording_sentences.json"
DATASET_DIR = BASE_DIR / "dataset_expanded"
METADATA_FILE = DATASET_DIR / "metadata.json"
PROGRESS_FILE = BASE_DIR / "recording_progress.json"

# Create directories
DATASET_DIR.mkdir(exist_ok=True)

class AudacityController:
    """Controls Audacity via named pipe scripting interface"""
    
    def __init__(self):
        self.to_pipe = None
        self.from_pipe = None
        
    def connect(self):
        """Connect to Audacity's scripting pipes"""
        print("\n🔌 Connecting to Audacity...")
        print("   Make sure Audacity is running with mod-script-pipe enabled")
        print("   (Audacity → Preferences → Modules → mod-script-pipe: Enabled)")
        
        # Find the actual pipe file (Audacity creates it with its PID)
        tmp_dir = Path("/tmp")
        to_pipes = list(tmp_dir.glob("audacity_script_pipe.to.*"))
        from_pipes = list(tmp_dir.glob("audacity_script_pipe.from.*"))
        
        if not to_pipes or not from_pipes:
            print("\n❌ ERROR: Cannot find Audacity script pipes")
            print("   1. Make sure Audacity is running")
            print("   2. Enable mod-script-pipe in Preferences → Modules")
            print("   3. Restart Audacity after enabling")
            return False
        
        try:
            self.to_pipe = open(to_pipes[0], 'w')
            self.from_pipe = open(from_pipes[0], 'r')
            print(f"   ✅ Connected to Audacity")
            return True
        except Exception as e:
            print(f"   ❌ Failed to connect: {e}")
            return False
    
    def send_command(self, command):
        """Send a command to Audacity and get response"""
        if not self.to_pipe:
            return None
        
        try:
            self.to_pipe.write(command + '\n')
            self.to_pipe.flush()
            response = self.from_pipe.readline()
            return response.strip()
        except Exception as e:
            print(f"   ❌ Command failed: {e}")
            return None
    
    def start_recording(self):
        """Start recording"""
        return self.send_command("Record2ndChoice:")
    
    def stop_recording(self):
        """Stop recording"""
        return self.send_command("Stop:")
    
    def add_label(self, text):
        """Add a label at the current selection with the given text"""
        escaped_text = text.replace('"', '\\"')
        return self.send_command(f'AddLabel: Text="{escaped_text}"')
    
    def select_all(self):
        """Select all audio"""
        return self.send_command("SelectAll:")
    
    def export_selection(self, filepath):
        """Export selected audio to WAV file"""
        return self.send_command(f'Export2: Filename="{filepath}" NumChannels=1')
    
    def delete_selection(self):
        """Delete selected audio"""
        return self.send_command("Delete:")
    
    def close(self):
        """Close pipe connections"""
        if self.to_pipe:
            self.to_pipe.close()
        if self.from_pipe:
            self.from_pipe.close()

class RecordingSession:
    """Manages recording session state and progress tracking"""
    
    def __init__(self):
        self.load_sentences()
        self.load_progress()
        self.metadata = self.load_metadata()
        self.audacity = AudacityController()
        
    def load_sentences(self):
        """Load sentences from JSON file"""
        if not SENTENCES_FILE.exists():
            print(f"❌ ERROR: Sentences file not found at {SENTENCES_FILE}")
            print("   Please create recording_sentences.json first")
            exit(1)
        
        with open(SENTENCES_FILE, 'r') as f:
            self.all_sentences = json.load(f)
    
    def load_progress(self):
        """Load progress from previous sessions"""
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, 'r') as f:
                self.progress = json.load(f)
        else:
            self.progress = {
                "current_session": "session_1",
                "current_index": 0,
                "total_recorded": 0,
                "sessions_completed": [],
                "last_item_number": 40
            }
    
    def save_progress(self):
        """Save progress to file"""
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def load_metadata(self):
        """Load existing metadata"""
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        return []
    
    def save_metadata(self):
        """Save metadata to file"""
        with open(METADATA_FILE, 'w') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
    
    def add_metadata_entry(self, item_number, text):
        """Add a new metadata entry"""
        self.metadata.append({
            "audio_file": f"item_{item_number:03d}",
            "text": text,
            "recorded_date": datetime.now().isoformat()
        })
        self.save_metadata()

    def show_session_menu(self):
        """Display session selection menu"""
        print("\n" + "=" * 80)
        print("RECORDING SESSION SELECTOR")
        print("=" * 80)
        
        for session_key, session_data in self.all_sentences.items():
            status = "✅ COMPLETED" if session_key in self.progress["sessions_completed"] else ""
            current = "← CURRENT" if session_key == self.progress["current_session"] else ""
            
            print(f"\n{session_key.upper()}: {session_data['title']} {status} {current}")
            print(f"  {session_data['description']}")
            print(f"  Sentences: {len(session_data['sentences'])}")
        
        print(f"\n📊 Progress: {self.progress['total_recorded']} sentences recorded total")
        print(f"📝 Next item number: {self.progress['last_item_number'] + 1}")
        
        print("\n" + "=" * 80)
        print("\nOptions:")
        print("  1-5: Jump to specific session")
        print("  c: Continue from where you left off")
        print("  q: Quit")
        
        choice = input("\nYour choice: ").strip().lower()
        
        if choice == 'q':
            return None
        elif choice == 'c':
            return self.progress["current_session"]
        elif choice in ['1', '2', '3', '4', '5']:
            session_key = f"session_{choice}"
            if session_key in self.all_sentences:
                return session_key
        
        print("Invalid choice, continuing from current session")
        return self.progress["current_session"]
    
    def show_statistics(self):
        """Display recording statistics"""
        print("\n" + "=" * 80)
        print("RECORDING STATISTICS")
        print("=" * 80)
        
        total_sentences = sum(len(s["sentences"]) for s in self.all_sentences.values())
        print(f"\n📊 Overall Progress: {self.progress['total_recorded']} / {total_sentences} sentences")
        print(f"   ({self.progress['total_recorded']/total_sentences*100:.1f}% complete)")
        
        print(f"\n📝 Current: {self.progress['current_session']}")
        print(f"   Starting at sentence {self.progress['current_index'] + 1}")
        
        print(f"\n✅ Completed sessions: {len(self.progress['sessions_completed'])}")
        for session in self.progress["sessions_completed"]:
            print(f"   - {session}")
        
        print(f"\n💾 Metadata entries: {len(self.metadata)}")
        print(f"📁 Audio files in: {DATASET_DIR}")
        print("\n" + "=" * 80)

    def record_session(self, session_key):
        """Record a complete session"""
        session_data = self.all_sentences[session_key]
        sentences = session_data["sentences"]
        
        # Determine starting index
        if session_key == self.progress["current_session"]:
            start_index = self.progress["current_index"]
        else:
            start_index = 0
            self.progress["current_session"] = session_key
            self.progress["current_index"] = 0
        
        print("\n" + "=" * 80)
        print(f"SESSION: {session_data['title']}")
        print("=" * 80)
        print(f"{session_data['description']}")
        print(f"\nTotal sentences: {len(sentences)}")
        print(f"Starting from: {start_index + 1}")
        print("=" * 80)
        
        # Connect to Audacity
        if not self.audacity.connect():
            print("\n❌ Cannot proceed without Audacity connection")
            return
        
        print("\n📋 INSTRUCTIONS:")
        print("   1. Each sentence will be displayed")
        print("   2. Press ENTER when ready to record")
        print("   3. Read the sentence naturally")
        print("   4. Recording stops automatically after you finish")
        print("   5. Review the recording and approve or re-record")
        print("\n   Commands: [Enter]=Record | 's'=Skip | 'q'=Quit session")
        
        input("\nPress ENTER to begin...")

        # Recording loop
        for idx in range(start_index, len(sentences)):
            sentence = sentences[idx]
            item_number = self.progress["last_item_number"] + 1
            
            print("\n" + "=" * 80)
            print(f"SENTENCE {idx + 1} of {len(sentences)} (Item {item_number:03d})")
            print("=" * 80)
            print(f"\n  \"{sentence}\"\n")
            print("=" * 80)
            
            while True:
                command = input("\nPress [ENTER] to record, 's' to skip, 'q' to quit: ").strip().lower()
                
                if command == 'q':
                    print("\n⚠️  Saving progress and quitting session...")
                    self.progress["current_index"] = idx
                    self.save_progress()
                    return
                
                if command == 's':
                    print("   Skipped")
                    break
                
                # Record the sentence
                print("\n🔴 RECORDING in 3 seconds...")
                print("   Get ready to read the sentence naturally")
                time.sleep(3)
                
                print("🔴 RECORDING NOW - speak clearly!")
                self.audacity.start_recording()
                
                input("   Press ENTER when you finish speaking...")
                
                self.audacity.stop_recording()
                print("⏹️  Recording stopped")
                
                # Add label with the sentence text
                self.audacity.add_label(sentence)
                
                print("\n🎧 Review the recording in Audacity")
                choice = input("   Keep this recording? [y/n/q]: ").strip().lower()
                
                if choice == 'q':
                    self.audacity.delete_selection()
                    self.progress["current_index"] = idx
                    self.save_progress()
                    return
                
                if choice == 'y':
                    # Export the recording
                    filename = f"item_{item_number:03d}.wav"
                    filepath = DATASET_DIR / filename
                    
                    print(f"💾 Saving as {filename}...")
                    self.audacity.select_all()
                    self.audacity.export_selection(str(filepath))
                    
                    # Save metadata
                    self.add_metadata_entry(item_number, sentence)
                    
                    # Update progress
                    self.progress["last_item_number"] = item_number
                    self.progress["total_recorded"] += 1
                    self.progress["current_index"] = idx + 1
                    self.save_progress()
                    
                    # Clear for next recording
                    self.audacity.delete_selection()
                    
                    print(f"   ✅ Saved! ({self.progress['total_recorded']} total)")
                    break
                else:
                    # Re-record
                    print("   🔄 Re-recording...")
                    self.audacity.delete_selection()

        # Session complete
        print("\n" + "=" * 80)
        print("✅ SESSION COMPLETE!")
        print("=" * 80)
        
        if session_key not in self.progress["sessions_completed"]:
            self.progress["sessions_completed"].append(session_key)
        
        # Move to next session
        session_num = int(session_key.split('_')[1])
        next_session = f"session_{session_num + 1}"
        if next_session in self.all_sentences:
            self.progress["current_session"] = next_session
            self.progress["current_index"] = 0
        
        self.save_progress()
        
        print(f"\n📊 Total recordings: {self.progress['total_recorded']}")
        print(f"📝 Metadata entries: {len(self.metadata)}")
        print(f"💾 Progress saved to {PROGRESS_FILE}")
    
    def run(self):
        """Main application loop"""
        print("=" * 80)
        print("VOICE RECORDING ASSISTANT")
        print("=" * 80)
        print("\nThis tool guides you through recording sessions with automatic")
        print("Audacity integration and metadata tracking.")
        
        while True:
            self.show_statistics()
            
            session_key = self.show_session_menu()
            
            if session_key is None:
                print("\n👋 Goodbye!")
                break
            
            self.record_session(session_key)
            
            print("\n" + "=" * 80)
            choice = input("\nContinue to another session? [y/n]: ").strip().lower()
            if choice != 'y':
                print("\n👋 Goodbye!")
                break
        
        # Cleanup
        self.audacity.close()


if __name__ == "__main__":
    try:
        session = RecordingSession()
        session.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Recording interrupted")
        print("Progress has been saved. Run again to continue.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
