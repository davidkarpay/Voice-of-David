import { useState, useEffect, useCallback } from 'react';
import { Mic, Square, RotateCcw, Check, SkipForward, Play, Pause, Loader } from 'lucide-react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { WaveformVisualizer } from './WaveformVisualizer';
import { QualityReport } from './QualityReport';
import { generatePrompts, uploadRecording, getPromptSuggestions } from '../services/api';
import type { AudioAnalysis, Achievement, RecordingCategory } from '../types';

interface Props {
  sessionId?: number;
  category: RecordingCategory;
  onRecordingComplete: () => void;
}

type StudioState = 'idle' | 'countdown' | 'recording' | 'review' | 'uploading' | 'result';

export function RecordingStudio({ sessionId, category, onRecordingComplete }: Props) {
  const recorder = useAudioRecorder();
  const [state, setState] = useState<StudioState>('idle');
  const [prompts, setPrompts] = useState<string[]>([]);
  const [currentPromptIndex, setCurrentPromptIndex] = useState(0);
  const [countdown, setCountdown] = useState(3);
  const [analysis, setAnalysis] = useState<AudioAnalysis | null>(null);
  const [newAchievements, setNewAchievements] = useState<Achievement[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingPrompts, setLoadingPrompts] = useState(false);

  // Load prompts
  const loadPrompts = useCallback(async () => {
    setLoadingPrompts(true);
    try {
      const result = await generatePrompts(category, 10);
      setPrompts(result.prompts);
      setCurrentPromptIndex(0);
    } catch (err: any) {
      setError(`Failed to load prompts: ${err.message}`);
    }
    setLoadingPrompts(false);
  }, [category]);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const currentPrompt = prompts[currentPromptIndex] || '';

  // Countdown then start recording
  const startCountdown = useCallback(() => {
    setState('countdown');
    setCountdown(3);
    setAnalysis(null);
    setNewAchievements([]);

    let count = 3;
    const interval = setInterval(() => {
      count--;
      setCountdown(count);
      if (count <= 0) {
        clearInterval(interval);
        setState('recording');
        recorder.startRecording();
      }
    }, 1000);
  }, [recorder]);

  // Stop recording, go to review
  const stopRecording = useCallback(() => {
    recorder.stopRecording();
    setState('review');
  }, [recorder]);

  // Upload recording
  const acceptRecording = useCallback(async () => {
    if (!recorder.audioBlob) return;

    setState('uploading');
    try {
      const result = await uploadRecording(
        recorder.audioBlob,
        currentPrompt,
        category,
        sessionId,
      );
      setAnalysis(result.analysis);
      setNewAchievements(result.new_achievements || []);
      setState('result');
      onRecordingComplete();
    } catch (err: any) {
      setError(`Upload failed: ${err.message}`);
      setState('review');
    }
  }, [recorder.audioBlob, currentPrompt, category, sessionId, onRecordingComplete]);

  // Redo recording
  const redoRecording = useCallback(() => {
    recorder.resetRecording();
    setState('idle');
  }, [recorder]);

  // Next prompt
  const nextPrompt = useCallback(() => {
    if (currentPromptIndex < prompts.length - 1) {
      setCurrentPromptIndex((i) => i + 1);
    } else {
      loadPrompts();
    }
    recorder.resetRecording();
    setAnalysis(null);
    setNewAchievements([]);
    setState('idle');
  }, [currentPromptIndex, prompts.length, loadPrompts, recorder]);

  // Playback
  const togglePlayback = useCallback(() => {
    if (!recorder.audioUrl) return;
    const audio = new Audio(recorder.audioUrl);
    if (isPlaying) {
      setIsPlaying(false);
    } else {
      setIsPlaying(true);
      audio.play();
      audio.onended = () => setIsPlaying(false);
    }
  }, [recorder.audioUrl, isPlaying]);

  return (
    <div style={{ maxWidth: '700px', margin: '0 auto' }}>
      {/* Prompt display */}
      <div style={{
        background: '#1e293b',
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '20px',
        textAlign: 'center',
        minHeight: '100px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        {loadingPrompts ? (
          <div style={{ color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
            Generating prompts...
          </div>
        ) : (
          <div>
            <div style={{
              fontSize: '20px',
              lineHeight: 1.6,
              color: '#e2e8f0',
              fontWeight: '400',
            }}>
              "{currentPrompt}"
            </div>
            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>
              Prompt {currentPromptIndex + 1} of {prompts.length}
            </div>
          </div>
        )}
      </div>

      {/* Waveform */}
      <div style={{ marginBottom: '20px' }}>
        <WaveformVisualizer
          analyserNode={recorder.analyserNode}
          isRecording={state === 'recording'}
        />
      </div>

      {/* Duration display */}
      {(state === 'recording' || state === 'review') && (
        <div style={{
          textAlign: 'center',
          fontSize: '32px',
          fontFamily: 'monospace',
          color: state === 'recording' ? '#f87171' : '#e2e8f0',
          marginBottom: '16px',
        }}>
          {recorder.duration.toFixed(1)}s
        </div>
      )}

      {/* Countdown */}
      {state === 'countdown' && (
        <div style={{
          textAlign: 'center',
          fontSize: '72px',
          fontWeight: 'bold',
          color: '#fbbf24',
          marginBottom: '16px',
          animation: 'pulse 1s ease-in-out',
        }}>
          {countdown}
        </div>
      )}

      {/* Controls */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: '12px',
        marginBottom: '20px',
      }}>
        {state === 'idle' && (
          <button onClick={startCountdown} style={primaryButtonStyle}>
            <Mic size={20} /> Start Recording
          </button>
        )}

        {state === 'recording' && (
          <button onClick={stopRecording} style={{ ...primaryButtonStyle, background: '#dc2626' }}>
            <Square size={20} /> Stop
          </button>
        )}

        {state === 'review' && (
          <>
            <button onClick={togglePlayback} style={secondaryButtonStyle}>
              {isPlaying ? <Pause size={18} /> : <Play size={18} />}
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            <button onClick={redoRecording} style={secondaryButtonStyle}>
              <RotateCcw size={18} /> Redo
            </button>
            <button onClick={acceptRecording} style={primaryButtonStyle}>
              <Check size={18} /> Accept
            </button>
          </>
        )}

        {state === 'uploading' && (
          <button disabled style={{ ...primaryButtonStyle, opacity: 0.6 }}>
            <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
            Analyzing...
          </button>
        )}

        {state === 'result' && (
          <button onClick={nextPrompt} style={primaryButtonStyle}>
            <SkipForward size={18} /> Next Prompt
          </button>
        )}
      </div>

      {/* Skip prompt button (always available when not recording) */}
      {(state === 'idle' || state === 'result') && prompts.length > 1 && (
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <button
            onClick={nextPrompt}
            style={{
              background: 'none',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              fontSize: '13px',
              padding: '4px 8px',
            }}
          >
            Skip this prompt
          </button>
        </div>
      )}

      {/* Quality report */}
      {state === 'result' && analysis && (
        <QualityReport analysis={analysis} newAchievements={newAchievements} />
      )}

      {/* Error display */}
      {(error || recorder.error) && (
        <div style={{
          padding: '12px 16px',
          background: '#f8717122',
          borderRadius: '8px',
          color: '#fca5a5',
          fontSize: '14px',
          marginTop: '12px',
        }}>
          {error || recorder.error}
        </div>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(1.1); }
        }
      `}</style>
    </div>
  );
}

const primaryButtonStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '12px 24px',
  borderRadius: '10px',
  border: 'none',
  background: '#4ade80',
  color: '#0f172a',
  fontSize: '15px',
  fontWeight: '600',
  cursor: 'pointer',
};

const secondaryButtonStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  padding: '10px 18px',
  borderRadius: '8px',
  border: '1px solid #334155',
  background: '#1e293b',
  color: '#e2e8f0',
  fontSize: '14px',
  cursor: 'pointer',
};
