const API_BASE = '/api';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Dashboard
export const getDashboard = () => fetchJson<any>('/progress/dashboard');
export const getAchievements = () => fetchJson<any[]>('/progress/achievements');
export const getStreak = () => fetchJson<any>('/progress/streak');
export const getPhonemes = () => fetchJson<any>('/progress/phonemes');

// Recordings
export const getRecordings = (params?: {
  category?: string; quality?: string; flag?: string;
  reviewed?: boolean; search?: string; sort?: string;
  limit?: number; offset?: number;
}) => {
  const query = new URLSearchParams();
  if (params?.category) query.set('category', params.category);
  if (params?.quality) query.set('quality', params.quality);
  if (params?.flag) query.set('flag', params.flag);
  if (params?.reviewed !== undefined) query.set('reviewed', String(params.reviewed));
  if (params?.search) query.set('search', params.search);
  if (params?.sort) query.set('sort', params.sort);
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));
  return fetchJson<any[]>(`/recordings?${query}`);
};

export const uploadRecording = async (
  audioBlob: Blob,
  text: string,
  category: string,
  sessionId?: number,
) => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.wav');
  formData.append('text', text);
  formData.append('category', category);
  if (sessionId) formData.append('session_id', String(sessionId));

  const res = await fetch(`${API_BASE}/recordings/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
};

export const deleteRecording = (id: number) =>
  fetchJson(`/recordings/${id}`, { method: 'DELETE' });

// Prompts
export const generatePrompts = (category: string, count: number = 10) =>
  fetchJson<any>('/prompts/generate', {
    method: 'POST',
    body: JSON.stringify({ category, count }),
  });

export const getPromptSuggestions = () => fetchJson<any>('/prompts/suggestions');

// Sessions
export const createSession = (title: string, category: string, targetCount: number = 10) =>
  fetchJson<any>('/sessions', {
    method: 'POST',
    body: JSON.stringify({ title, category, target_count: targetCount }),
  });

export const completeSession = (id: number) =>
  fetchJson<any>(`/sessions/${id}/complete`, { method: 'PUT' });

export const getSessions = () => fetchJson<any[]>('/sessions');

// Review
export const reviewRecording = (id: number, data: {
  flag?: string | null;
  manual_quality_override?: string | null;
  review_note?: string | null;
}) => fetchJson<any>(`/recordings/${id}/review`, {
  method: 'PATCH',
  body: JSON.stringify(data),
});

export const batchReviewRecordings = (ids: number[], data: {
  flag?: string | null;
}) => fetchJson<any>('/recordings/batch-review', {
  method: 'POST',
  body: JSON.stringify({ recording_ids: ids, ...data }),
});

export const batchDeleteRecordings = (ids: number[]) =>
  fetchJson<any>('/recordings/batch-delete', {
    method: 'POST',
    body: JSON.stringify({ recording_ids: ids }),
  });

// Audio playback URL
export const getAudioUrl = (filename: string) =>
  `/audio/${filename}`;
