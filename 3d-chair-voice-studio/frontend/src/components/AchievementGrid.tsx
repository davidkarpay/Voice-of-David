import type { Achievement } from '../types';
import {
  Mic, TrendingUp, Award, Star, Target, CheckCircle,
  Activity, ShieldCheck, Flame, Volume2, Wind, Music,
  Crown, Scale, BookOpen, MessageCircle, Timer, Zap, Lock,
} from 'lucide-react';

interface Props {
  achievements: Achievement[];
}

const iconMap: Record<string, typeof Mic> = {
  mic: Mic,
  'trending-up': TrendingUp,
  award: Award,
  star: Star,
  target: Target,
  'check-circle': CheckCircle,
  activity: Activity,
  'shield-check': ShieldCheck,
  flame: Flame,
  'volume-2': Volume2,
  wind: Wind,
  music: Music,
  crown: Crown,
  scale: Scale,
  'book-open': BookOpen,
  'message-circle': MessageCircle,
  timer: Timer,
  zap: Zap,
};

const categoryColors: Record<string, string> = {
  milestone: '#4ade80',
  quality: '#60a5fa',
  streak: '#f97316',
  phoneme: '#a78bfa',
  domain: '#f472b6',
  session: '#22d3ee',
};

export function AchievementGrid({ achievements }: Props) {
  const grouped: Record<string, Achievement[]> = {};
  for (const ach of achievements) {
    const cat = ach.category || 'other';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(ach);
  }

  const categoryLabels: Record<string, string> = {
    milestone: 'Milestones',
    quality: 'Quality',
    streak: 'Streaks',
    phoneme: 'Phoneme Coverage',
    domain: 'Domain Expertise',
    session: 'Sessions',
  };

  return (
    <div>
      {Object.entries(grouped).map(([category, achs]) => (
        <div key={category} style={{ marginBottom: '24px' }}>
          <h3 style={{
            color: categoryColors[category] || '#94a3b8',
            fontSize: '14px',
            fontWeight: '600',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '12px',
          }}>
            {categoryLabels[category] || category}
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '10px',
          }}>
            {achs.map((ach) => {
              const Icon = iconMap[ach.icon || ''] || Star;
              const color = categoryColors[ach.category || ''] || '#94a3b8';
              const unlocked = ach.is_unlocked;

              return (
                <div
                  key={ach.key}
                  style={{
                    padding: '14px',
                    borderRadius: '10px',
                    background: unlocked ? `${color}11` : '#0f172a',
                    border: `1px solid ${unlocked ? `${color}44` : '#1e293b'}`,
                    opacity: unlocked ? 1 : 0.5,
                    transition: 'all 0.3s ease',
                  }}
                >
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '6px',
                  }}>
                    {unlocked ? (
                      <Icon size={20} color={color} />
                    ) : (
                      <Lock size={20} color="#475569" />
                    )}
                    <span style={{
                      fontSize: '14px',
                      fontWeight: '600',
                      color: unlocked ? '#e2e8f0' : '#64748b',
                    }}>
                      {ach.title}
                    </span>
                  </div>
                  <div style={{
                    fontSize: '12px',
                    color: unlocked ? '#94a3b8' : '#475569',
                    lineHeight: 1.4,
                  }}>
                    {ach.description}
                  </div>
                  {unlocked && ach.unlocked_at && (
                    <div style={{
                      fontSize: '11px',
                      color: '#64748b',
                      marginTop: '6px',
                    }}>
                      Unlocked {new Date(ach.unlocked_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
