import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Play, Pause, Star, Trash2, RotateCcw, Check, Search,
  ChevronDown, ChevronUp, MessageSquare, Filter, X,
} from 'lucide-react';
import {
  getRecordings, getAudioUrl, reviewRecording,
  batchReviewRecordings, batchDeleteRecordings,
} from '../services/api';
import type { Recording } from '../types';

const GRADES = ['A', 'B', 'C', 'D'] as const;
const GRADE_COLORS: Record<string, string> = {
  A: '#4ade80', B: '#60a5fa', C: '#fbbf24', D: '#f87171',
};
const FLAG_ICONS: Record<string, { icon: string; color: string }> = {
  favorite: { icon: '★', color: '#fbbf24' },
  delete: { icon: '🗑', color: '#f87171' },
  needs_redo: { icon: '↻', color: '#c084fc' },
};

export function ReviewRecordings() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [searchText, setSearchText] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterQuality, setFilterQuality] = useState('');
  const [filterFlag, setFilterFlag] = useState('');
  const [sortBy, setSortBy] = useState('newest');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const searchTimer = useRef<number | null>(null);
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const loadRecordings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getRecordings({
        category: filterCategory || undefined,
        quality: filterQuality || undefined,
        flag: filterFlag || undefined,
        search: debouncedSearch || undefined,
        sort: sortBy,
        limit: 200,
      });
      setRecordings(data);
    } catch (err) {
      console.error('Failed to load recordings', err);
    }
    setLoading(false);
  }, [filterCategory, filterQuality, filterFlag, debouncedSearch, sortBy]);

  useEffect(() => { loadRecordings(); }, [loadRecordings]);

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = window.setTimeout(() => setDebouncedSearch(searchText), 300);
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current); };
  }, [searchText]);

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === recordings.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(recordings.map(r => r.id)));
    }
  };

  const playAudio = (rec: Recording) => {
    if (audioRef.current) { audioRef.current.pause(); }
    if (playingId === rec.id) { setPlayingId(null); return; }
    const audio = new Audio(getAudioUrl(rec.filename));
    audio.onended = () => setPlayingId(null);
    audio.play();
    audioRef.current = audio;
    setPlayingId(rec.id);
  };

  const handleReview = async (id: number, data: {
    flag?: string | null;
    manual_quality_override?: string | null;
    review_note?: string | null;
  }) => {
    const updated = await reviewRecording(id, data);
    setRecordings(prev => prev.map(r => r.id === id ? updated : r));
  };

  const handleBatchFlag = async (flag: string | null) => {
    const ids = Array.from(selectedIds);
    await batchReviewRecordings(ids, { flag });
    await loadRecordings();
    setSelectedIds(new Set());
  };

  const handleBatchDelete = async () => {
    const ids = Array.from(selectedIds);
    await batchDeleteRecordings(ids);
    setConfirmDelete(false);
    setSelectedIds(new Set());
    await loadRecordings();
  };

  const flaggedForDelete = recordings.filter(r => r.flag === 'delete').length;
  const favorites = recordings.filter(r => r.flag === 'favorite').length;
  const reviewed = recordings.filter(r => r.reviewed_at).length;

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      {/* Summary stats */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
        {[
          { label: 'Total', value: recordings.length, color: '#e2e8f0' },
          { label: 'Reviewed', value: reviewed, color: '#4ade80' },
          { label: 'Favorites', value: favorites, color: '#fbbf24' },
          { label: 'Flagged Delete', value: flaggedForDelete, color: '#f87171' },
        ].map(s => (
          <div key={s.label} style={{
            background: '#1e293b', borderRadius: '8px', padding: '10px 16px',
            fontSize: '13px', color: '#94a3b8',
          }}>
            {s.label}: <strong style={{ color: s.color }}>{s.value}</strong>
          </div>
        ))}
      </div>

      {/* Search & Filter bar */}
      <div style={{
        background: '#1e293b', borderRadius: '10px', padding: '12px 16px',
        marginBottom: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap',
        alignItems: 'center',
      }}>
        <div style={{ position: 'relative', flex: '1 1 200px' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: '#64748b' }} />
          <input
            type="text"
            placeholder="Search prompt text..."
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{
              width: '100%', padding: '8px 8px 8px 30px', background: '#0f172a',
              border: '1px solid #334155', borderRadius: '6px', color: '#e2e8f0',
              fontSize: '13px', outline: 'none',
            }}
          />
        </div>
        <SelectFilter label="Category" value={filterCategory} onChange={setFilterCategory}
          options={[
            { value: '', label: 'All' }, { value: 'phonetic', label: 'Phonetic' },
            { value: 'conversational', label: 'Conversational' }, { value: 'emotional', label: 'Emotional' },
            { value: 'domain', label: 'Domain' }, { value: 'narrative', label: 'Narrative' },
          ]}
        />
        <SelectFilter label="Quality" value={filterQuality} onChange={setFilterQuality}
          options={[{ value: '', label: 'All' }, ...GRADES.map(g => ({ value: g, label: g }))]}
        />
        <SelectFilter label="Flag" value={filterFlag} onChange={setFilterFlag}
          options={[
            { value: '', label: 'All' }, { value: 'none', label: 'Unflagged' },
            { value: 'favorite', label: '★ Favorites' }, { value: 'delete', label: '🗑 Delete' },
            { value: 'needs_redo', label: '↻ Redo' },
          ]}
        />
        <SelectFilter label="Sort" value={sortBy} onChange={setSortBy}
          options={[
            { value: 'newest', label: 'Newest' }, { value: 'oldest', label: 'Oldest' },
            { value: 'quality_asc', label: 'Quality ↑' }, { value: 'quality_desc', label: 'Quality ↓' },
            { value: 'item_number', label: 'Item #' },
          ]}
        />
      </div>

      {/* Batch actions bar */}
      {selectedIds.size > 0 && (
        <div style={{
          background: '#1e293b', borderRadius: '10px', padding: '10px 16px',
          marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center',
          border: '1px solid #4ade8044',
        }}>
          <span style={{ fontSize: '13px', color: '#e2e8f0', marginRight: '8px' }}>
            {selectedIds.size} selected
          </span>
          <BatchButton label="★ Favorite" color="#fbbf24" onClick={() => handleBatchFlag('favorite')} />
          <BatchButton label="↻ Needs Redo" color="#c084fc" onClick={() => handleBatchFlag('needs_redo')} />
          <BatchButton label="🗑 Flag Delete" color="#f87171" onClick={() => handleBatchFlag('delete')} />
          <BatchButton label="Clear Flags" color="#94a3b8" onClick={() => handleBatchFlag(null)} />
          <div style={{ flex: 1 }} />
          {!confirmDelete ? (
            <BatchButton label="Delete Files" color="#dc2626" onClick={() => setConfirmDelete(true)} />
          ) : (
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: '#f87171' }}>Are you sure?</span>
              <BatchButton label="Yes, delete" color="#dc2626" onClick={handleBatchDelete} />
              <BatchButton label="Cancel" color="#64748b" onClick={() => setConfirmDelete(false)} />
            </div>
          )}
        </div>
      )}

      {/* Select all */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', padding: '0 4px',
      }}>
        <input
          type="checkbox"
          checked={selectedIds.size === recordings.length && recordings.length > 0}
          onChange={selectAll}
          style={{ accentColor: '#4ade80' }}
        />
        <span style={{ fontSize: '12px', color: '#64748b' }}>Select all</span>
      </div>

      {/* Recording list */}
      {loading ? (
        <div style={{ textAlign: 'center', color: '#64748b', padding: '40px' }}>Loading...</div>
      ) : recordings.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#64748b', padding: '40px' }}>
          No recordings match your filters.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {recordings.map(rec => (
            <RecordingCard
              key={rec.id}
              recording={rec}
              isSelected={selectedIds.has(rec.id)}
              isExpanded={expandedId === rec.id}
              isPlaying={playingId === rec.id}
              onToggleSelect={() => toggleSelect(rec.id)}
              onToggleExpand={() => setExpandedId(expandedId === rec.id ? null : rec.id)}
              onPlay={() => playAudio(rec)}
              onReview={(data) => handleReview(rec.id, data)}
            />
          ))}
        </div>
      )}
    </div>
  );
}


function RecordingCard({ recording: rec, isSelected, isExpanded, isPlaying, onToggleSelect, onToggleExpand, onPlay, onReview }: {
  recording: Recording;
  isSelected: boolean;
  isExpanded: boolean;
  isPlaying: boolean;
  onToggleSelect: () => void;
  onToggleExpand: () => void;
  onPlay: () => void;
  onReview: (data: any) => void;
}) {
  const [note, setNote] = useState(rec.review_note || '');
  const [savingNote, setSavingNote] = useState(false);
  const grade = rec.manual_quality_override || rec.quality_score || 'D';
  const gradeColor = GRADE_COLORS[grade] || '#64748b';
  const flagInfo = rec.flag ? FLAG_ICONS[rec.flag] : null;

  const saveNote = async () => {
    setSavingNote(true);
    await onReview({ review_note: note });
    setSavingNote(false);
  };

  return (
    <div style={{
      background: '#1e293b', borderRadius: '10px',
      border: `1px solid ${isSelected ? '#4ade8066' : rec.flag === 'delete' ? '#f8717133' : '#334155'}`,
      overflow: 'hidden',
    }}>
      {/* Compact row */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px',
        cursor: 'pointer',
      }} onClick={onToggleExpand}>
        <input
          type="checkbox" checked={isSelected}
          onChange={e => { e.stopPropagation(); onToggleSelect(); }}
          onClick={e => e.stopPropagation()}
          style={{ accentColor: '#4ade80', flexShrink: 0 }}
        />

        {/* Item number */}
        <span style={{ fontSize: '12px', color: '#64748b', fontFamily: 'monospace', width: '36px', flexShrink: 0 }}>
          #{rec.item_number}
        </span>

        {/* Play button */}
        <button onClick={e => { e.stopPropagation(); onPlay(); }} style={{
          background: 'none', border: 'none', color: isPlaying ? '#4ade80' : '#94a3b8',
          cursor: 'pointer', padding: '2px', flexShrink: 0,
        }}>
          {isPlaying ? <Pause size={16} /> : <Play size={16} />}
        </button>

        {/* Text */}
        <span style={{
          flex: 1, fontSize: '13px', color: '#e2e8f0',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {rec.text}
        </span>

        {/* Category badge */}
        <span style={{
          fontSize: '11px', color: '#94a3b8', background: '#0f172a',
          padding: '2px 8px', borderRadius: '4px', flexShrink: 0,
        }}>
          {rec.category}
        </span>

        {/* Duration */}
        <span style={{ fontSize: '12px', color: '#64748b', width: '40px', textAlign: 'right', flexShrink: 0 }}>
          {rec.duration_seconds ? `${rec.duration_seconds.toFixed(1)}s` : '--'}
        </span>

        {/* Quality grade */}
        <span style={{
          width: '24px', height: '24px', borderRadius: '6px', display: 'flex',
          alignItems: 'center', justifyContent: 'center', fontSize: '13px',
          fontWeight: '700', background: `${gradeColor}22`, color: gradeColor,
          flexShrink: 0,
        }}>
          {grade}
        </span>

        {/* Flag indicator */}
        <span style={{ width: '20px', textAlign: 'center', fontSize: '14px', flexShrink: 0 }}>
          {flagInfo ? <span style={{ color: flagInfo.color }}>{flagInfo.icon}</span> : ''}
        </span>

        {/* Reviewed indicator */}
        {rec.reviewed_at && (
          <Check size={14} style={{ color: '#4ade80', flexShrink: 0 }} />
        )}

        {/* Expand chevron */}
        {isExpanded ? <ChevronUp size={16} style={{ color: '#64748b' }} /> : <ChevronDown size={16} style={{ color: '#64748b' }} />}
      </div>

      {/* Expanded detail */}
      {isExpanded && (
        <div style={{
          padding: '12px 14px 16px', borderTop: '1px solid #334155',
          background: '#0f172a',
        }}>
          {/* Full text */}
          <div style={{
            fontSize: '15px', color: '#e2e8f0', lineHeight: 1.6,
            marginBottom: '16px', fontStyle: 'italic',
          }}>
            "{rec.text}"
          </div>

          {/* Metrics row */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <Metric label="Duration" value={rec.duration_seconds ? `${rec.duration_seconds.toFixed(1)}s` : '--'} />
            <Metric label="SNR" value={rec.snr_db ? `${rec.snr_db.toFixed(1)} dB` : '--'} />
            <Metric label="RMS" value={rec.rms_db ? `${rec.rms_db.toFixed(1)} dB` : '--'} />
            <Metric label="Clipping" value={rec.has_clipping ? 'Yes' : 'Clean'} color={rec.has_clipping ? '#f87171' : '#4ade80'} />
            <Metric label="Silence" value={rec.silence_ratio ? `${(rec.silence_ratio * 100).toFixed(0)}%` : '--'} />
            <Metric label="Auto Grade" value={rec.quality_score || '--'} color={GRADE_COLORS[rec.quality_score || ''] || '#64748b'} />
          </div>

          {/* Manual quality override */}
          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>
              Manual Quality Override
            </label>
            <div style={{ display: 'flex', gap: '6px' }}>
              {GRADES.map(g => (
                <button key={g} onClick={() => onReview({ manual_quality_override: g })} style={{
                  width: '36px', height: '32px', borderRadius: '6px', border: 'none',
                  background: rec.manual_quality_override === g ? `${GRADE_COLORS[g]}33` : '#1e293b',
                  color: rec.manual_quality_override === g ? GRADE_COLORS[g] : '#64748b',
                  fontWeight: '700', fontSize: '14px', cursor: 'pointer',
                  outline: rec.manual_quality_override === g ? `2px solid ${GRADE_COLORS[g]}` : 'none',
                }}>
                  {g}
                </button>
              ))}
              {rec.manual_quality_override && (
                <button onClick={() => onReview({ manual_quality_override: null })} style={{
                  padding: '4px 10px', borderRadius: '6px', border: 'none',
                  background: '#1e293b', color: '#64748b', fontSize: '12px', cursor: 'pointer',
                }}>
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Flags */}
          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>
              Flags
            </label>
            <div style={{ display: 'flex', gap: '6px' }}>
              <FlagButton label="★ Favorite" active={rec.flag === 'favorite'} color="#fbbf24"
                onClick={() => onReview({ flag: rec.flag === 'favorite' ? null : 'favorite' })} />
              <FlagButton label="↻ Needs Redo" active={rec.flag === 'needs_redo'} color="#c084fc"
                onClick={() => onReview({ flag: rec.flag === 'needs_redo' ? null : 'needs_redo' })} />
              <FlagButton label="🗑 Delete" active={rec.flag === 'delete'} color="#f87171"
                onClick={() => onReview({ flag: rec.flag === 'delete' ? null : 'delete' })} />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>
              Notes
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <textarea
                value={note}
                onChange={e => setNote(e.target.value)}
                placeholder="Add a note about this recording..."
                rows={2}
                style={{
                  flex: 1, padding: '8px 10px', background: '#1e293b',
                  border: '1px solid #334155', borderRadius: '6px', color: '#e2e8f0',
                  fontSize: '13px', resize: 'vertical', outline: 'none',
                  fontFamily: 'inherit',
                }}
              />
              <button onClick={saveNote} disabled={savingNote || note === (rec.review_note || '')} style={{
                padding: '8px 14px', borderRadius: '6px', border: 'none',
                background: note !== (rec.review_note || '') ? '#4ade80' : '#334155',
                color: note !== (rec.review_note || '') ? '#0f172a' : '#64748b',
                fontSize: '13px', fontWeight: '600', cursor: 'pointer', alignSelf: 'flex-end',
              }}>
                {savingNote ? '...' : 'Save'}
              </button>
            </div>
          </div>

          {/* Review timestamp */}
          {rec.reviewed_at && (
            <div style={{ fontSize: '11px', color: '#475569', marginTop: '10px' }}>
              Last reviewed: {new Date(rec.reviewed_at).toLocaleString()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{
      background: '#1e293b', borderRadius: '6px', padding: '6px 12px',
      fontSize: '12px',
    }}>
      <div style={{ color: '#64748b', marginBottom: '2px' }}>{label}</div>
      <div style={{ color: color || '#e2e8f0', fontWeight: '600' }}>{value}</div>
    </div>
  );
}


function FlagButton({ label, active, color, onClick }: {
  label: string; active: boolean; color: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick} style={{
      padding: '6px 12px', borderRadius: '6px', fontSize: '12px',
      border: active ? `1px solid ${color}` : '1px solid #334155',
      background: active ? `${color}22` : '#1e293b',
      color: active ? color : '#64748b',
      cursor: 'pointer', fontWeight: active ? '600' : '400',
    }}>
      {label}
    </button>
  );
}


function BatchButton({ label, color, onClick }: { label: string; color: string; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{
      padding: '6px 12px', borderRadius: '6px', border: 'none',
      background: `${color}22`, color, fontSize: '12px', cursor: 'pointer',
      fontWeight: '600',
    }}>
      {label}
    </button>
  );
}


function SelectFilter({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)} style={{
      padding: '8px 10px', background: '#0f172a', border: '1px solid #334155',
      borderRadius: '6px', color: '#e2e8f0', fontSize: '12px', outline: 'none',
      cursor: 'pointer',
    }}>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}
