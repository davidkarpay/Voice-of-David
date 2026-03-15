import { useState, useEffect } from 'react';
import { Mic, Flame, Target, Trophy, BarChart3, RefreshCw } from 'lucide-react';
import type { Dashboard as DashboardType, Achievement, RecordingCategory } from '../types';
import { getDashboard, getAchievements } from '../services/api';
import { PhonemeMap } from './PhonemeMap';
import { AchievementGrid } from './AchievementGrid';

interface Props {
  onStartSession: (category: RecordingCategory) => void;
}

const categories: { key: RecordingCategory; label: string; desc: string }[] = [
  { key: 'phonetic', label: 'Phonetically Balanced', desc: 'Cover all English sounds' },
  { key: 'conversational', label: 'Conversational', desc: 'Natural casual speech' },
  { key: 'emotional', label: 'Emotional Range', desc: 'Varied emotional delivery' },
  { key: 'domain', label: 'Legal Domain', desc: 'Criminal defense terminology' },
  { key: 'narrative', label: 'Narrative', desc: 'Storytelling and description' },
];

export function DashboardView({ onStartSession }: Props) {
  const [dashboard, setDashboard] = useState<DashboardType | null>(null);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'phonemes' | 'achievements'>('overview');

  const loadData = async () => {
    setLoading(true);
    try {
      const [dash, achs] = await Promise.all([getDashboard(), getAchievements()]);
      setDashboard(dash);
      setAchievements(achs);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  if (loading || !dashboard) {
    return (
      <div style={{ textAlign: 'center', padding: '60px', color: '#94a3b8' }}>
        Loading dashboard...
      </div>
    );
  }

  const progressPct = Math.min(100, (dashboard.total_recordings / dashboard.target_recordings) * 100);
  const unlockedCount = achievements.filter((a) => a.is_unlocked).length;

  return (
    <div>
      {/* Header stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        marginBottom: '24px',
      }}>
        {/* Progress card */}
        <StatCard
          icon={<Mic size={22} />}
          label="Recordings"
          value={`${dashboard.total_recordings} / ${dashboard.target_recordings}`}
          accent="#4ade80"
        >
          <div style={{
            height: '6px',
            background: '#334155',
            borderRadius: '3px',
            marginTop: '8px',
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${progressPct}%`,
              background: 'linear-gradient(90deg, #4ade80, #22d3ee)',
              borderRadius: '3px',
              transition: 'width 0.5s ease',
            }} />
          </div>
        </StatCard>

        {/* Streak card */}
        <StatCard
          icon={<Flame size={22} />}
          label="Streak"
          value={`${dashboard.streak_info.current_streak} days`}
          accent="#f97316"
        >
          <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
            {dashboard.streak_info.recorded_today ? 'Recorded today' : 'No recording today yet'}
            {' | '}Best: {dashboard.streak_info.longest_streak} days
          </div>
        </StatCard>

        {/* Phoneme coverage card */}
        <StatCard
          icon={<Target size={22} />}
          label="Phoneme Coverage"
          value={`${dashboard.phoneme_coverage.coverage_percentage}%`}
          accent="#a78bfa"
        >
          <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
            {dashboard.phoneme_coverage.covered_phonemes} / {dashboard.phoneme_coverage.total_phonemes} sounds
          </div>
        </StatCard>

        {/* Achievements card */}
        <StatCard
          icon={<Trophy size={22} />}
          label="Achievements"
          value={`${unlockedCount} / ${achievements.length}`}
          accent="#fbbf24"
        />
      </div>

      {/* Tab navigation */}
      <div style={{
        display: 'flex',
        gap: '4px',
        marginBottom: '20px',
        background: '#0f172a',
        borderRadius: '8px',
        padding: '4px',
      }}>
        {(['overview', 'phonemes', 'achievements'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              flex: 1,
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === tab ? '#1e293b' : 'transparent',
              color: activeTab === tab ? '#e2e8f0' : '#64748b',
              fontSize: '14px',
              fontWeight: activeTab === tab ? '600' : '400',
              cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div>
          {/* Quality distribution */}
          <div style={{
            background: '#1e293b',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '20px',
          }}>
            <h3 style={{ color: '#e2e8f0', fontSize: '16px', margin: '0 0 12px 0' }}>
              Quality Distribution
            </h3>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', height: '80px' }}>
              {['A', 'B', 'C', 'D'].map((grade) => {
                const count = dashboard.quality_distribution[grade] || 0;
                const max = Math.max(...Object.values(dashboard.quality_distribution), 1);
                const height = (count / max) * 100;
                const colors: Record<string, string> = { A: '#4ade80', B: '#60a5fa', C: '#fbbf24', D: '#f87171' };
                return (
                  <div key={grade} style={{ flex: 1, textAlign: 'center' }}>
                    <div style={{
                      height: `${Math.max(height, 4)}%`,
                      background: colors[grade],
                      borderRadius: '4px 4px 0 0',
                      transition: 'height 0.3s ease',
                      minHeight: '4px',
                    }} />
                    <div style={{ marginTop: '4px', fontSize: '13px', color: colors[grade], fontWeight: '600' }}>
                      {grade}
                    </div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>{count}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Start session */}
          <div style={{
            background: '#1e293b',
            borderRadius: '12px',
            padding: '20px',
          }}>
            <h3 style={{ color: '#e2e8f0', fontSize: '16px', margin: '0 0 16px 0' }}>
              Start Recording Session
            </h3>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
              gap: '10px',
            }}>
              {categories.map((cat) => (
                <button
                  key={cat.key}
                  onClick={() => onStartSession(cat.key)}
                  style={{
                    padding: '14px',
                    borderRadius: '10px',
                    border: '1px solid #334155',
                    background: '#0f172a',
                    color: '#e2e8f0',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'border-color 0.2s',
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.borderColor = '#4ade80')}
                  onMouseOut={(e) => (e.currentTarget.style.borderColor = '#334155')}
                >
                  <div style={{ fontWeight: '600', fontSize: '14px', marginBottom: '4px' }}>
                    {cat.label}
                  </div>
                  <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                    {cat.desc}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'phonemes' && (
        <PhonemeMap coverage={dashboard.phoneme_coverage} />
      )}

      {activeTab === 'achievements' && (
        <AchievementGrid achievements={achievements} />
      )}
    </div>
  );
}

function StatCard({ icon, label, value, accent, children }: {
  icon: React.ReactNode;
  label: string;
  value: string;
  accent: string;
  children?: React.ReactNode;
}) {
  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '16px',
      border: `1px solid ${accent}22`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ color: accent }}>{icon}</span>
        <span style={{ fontSize: '13px', color: '#94a3b8' }}>{label}</span>
      </div>
      <div style={{ fontSize: '22px', fontWeight: '700', color: '#e2e8f0' }}>
        {value}
      </div>
      {children}
    </div>
  );
}
