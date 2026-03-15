export interface Recording {
  id: number;
  item_number: number;
  filename: string;
  text: string;
  session_id: number | null;
  category: string | null;
  duration_seconds: number | null;
  quality_score: string | null;
  snr_db: number | null;
  has_clipping: boolean;
  silence_ratio: number | null;
  rms_db: number | null;
  recorded_at: string | null;
  flag: string | null;
  manual_quality_override: string | null;
  review_note: string | null;
  reviewed_at: string | null;
}

export interface AudioAnalysis {
  duration_seconds: number;
  sample_rate: number;
  channels: number;
  bit_depth: number;
  snr_db: number;
  rms_db: number;
  peak_amplitude: number;
  has_clipping: boolean;
  clipping_count: number;
  silence_ratio: number;
  quality_score: string;
  issues: string[];
  suggestions: string[];
}

export interface RecordingUploadResponse {
  recording: Recording;
  analysis: AudioAnalysis;
  new_achievements: Achievement[];
}

export interface Session {
  id: number;
  title: string;
  category: string | null;
  started_at: string | null;
  completed_at: string | null;
  target_count: number;
  completed_count: number;
}

export interface Achievement {
  key: string;
  title: string;
  description: string | null;
  icon: string | null;
  category: string | null;
  threshold: number | null;
  unlocked_at: string | null;
  is_unlocked: boolean;
}

export interface StreakInfo {
  current_streak: number;
  longest_streak: number;
  recorded_today: boolean;
}

export interface PhonemeCategory {
  total: number;
  covered: number;
  percentage: number;
  phonemes: Record<string, boolean | { covered: boolean; count: number }>;
}

export interface PhonemeCoverage {
  total_phonemes: number;
  covered_phonemes: number;
  coverage_percentage: number;
  missing_phonemes: string[];
  categories: Record<string, PhonemeCategory>;
}

export interface Dashboard {
  total_recordings: number;
  target_recordings: number;
  quality_distribution: Record<string, number>;
  recent_recordings: Recording[];
  streak_info: StreakInfo;
  phoneme_coverage: PhonemeCoverage;
}

export interface PromptSuggestions {
  cached_prompts: { id: number; text: string; category: string }[];
  recommended_category: string;
  category_distribution: Record<string, number>;
  total_recordings: number;
  phoneme_coverage_percentage: number;
}

export type RecordingCategory = 'phonetic' | 'conversational' | 'emotional' | 'domain' | 'narrative';
