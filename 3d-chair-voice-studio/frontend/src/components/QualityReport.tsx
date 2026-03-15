import type { AudioAnalysis, Achievement } from '../types';
import {
  CheckCircle, AlertTriangle, XCircle, Info,
  Clock, Volume2, Waves, AlertOctagon, Trophy,
} from 'lucide-react';

interface Props {
  analysis: AudioAnalysis;
  newAchievements: Achievement[];
}

const gradeColors: Record<string, string> = {
  A: '#4ade80',
  B: '#60a5fa',
  C: '#fbbf24',
  D: '#f87171',
};

const gradeIcons: Record<string, typeof CheckCircle> = {
  A: CheckCircle,
  B: Info,
  C: AlertTriangle,
  D: XCircle,
};

export function QualityReport({ analysis, newAchievements }: Props) {
  const GradeIcon = gradeIcons[analysis.quality_score] || Info;
  const gradeColor = gradeColors[analysis.quality_score] || '#94a3b8';

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '20px',
      border: `2px solid ${gradeColor}33`,
    }}>
      {/* Grade header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: `${gradeColor}22`,
          border: `3px solid ${gradeColor}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '28px',
          fontWeight: 'bold',
          color: gradeColor,
        }}>
          {analysis.quality_score}
        </div>
        <div>
          <div style={{ fontSize: '18px', fontWeight: '600', color: '#e2e8f0' }}>
            Quality Score
          </div>
          <div style={{ fontSize: '14px', color: '#94a3b8' }}>
            {analysis.quality_score === 'A' ? 'Excellent recording' :
             analysis.quality_score === 'B' ? 'Good recording' :
             analysis.quality_score === 'C' ? 'Acceptable, could improve' :
             'Needs improvement'}
          </div>
        </div>
      </div>

      {/* Metrics grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: '12px',
        marginBottom: '16px',
      }}>
        <MetricCard
          icon={<Clock size={16} />}
          label="Duration"
          value={`${analysis.duration_seconds.toFixed(1)}s`}
          color={analysis.duration_seconds >= 3 && analysis.duration_seconds <= 30 ? '#4ade80' : '#fbbf24'}
        />
        <MetricCard
          icon={<Volume2 size={16} />}
          label="SNR"
          value={`${analysis.snr_db.toFixed(1)} dB`}
          color={analysis.snr_db >= 30 ? '#4ade80' : analysis.snr_db >= 20 ? '#60a5fa' : '#fbbf24'}
        />
        <MetricCard
          icon={<Waves size={16} />}
          label="RMS Level"
          value={`${analysis.rms_db.toFixed(1)} dB`}
          color={analysis.rms_db > -30 && analysis.rms_db < -6 ? '#4ade80' : '#fbbf24'}
        />
        <MetricCard
          icon={<AlertOctagon size={16} />}
          label="Clipping"
          value={analysis.has_clipping ? 'Detected' : 'Clean'}
          color={analysis.has_clipping ? '#f87171' : '#4ade80'}
        />
      </div>

      {/* Issues */}
      {analysis.issues.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          {analysis.issues.map((issue, i) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              padding: '8px',
              background: '#f8717122',
              borderRadius: '6px',
              marginBottom: '4px',
              fontSize: '13px',
              color: '#fca5a5',
            }}>
              <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
              {issue}
            </div>
          ))}
        </div>
      )}

      {/* Suggestions */}
      {analysis.suggestions.length > 0 && (
        <div>
          {analysis.suggestions.map((suggestion, i) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              padding: '8px',
              background: '#4ade8022',
              borderRadius: '6px',
              marginBottom: '4px',
              fontSize: '13px',
              color: '#86efac',
            }}>
              <GradeIcon size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
              {suggestion}
            </div>
          ))}
        </div>
      )}

      {/* New achievements */}
      {newAchievements.length > 0 && (
        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: '#fbbf2422',
          borderRadius: '8px',
          border: '1px solid #fbbf2444',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '8px',
            color: '#fbbf24',
            fontWeight: '600',
          }}>
            <Trophy size={18} />
            Achievement Unlocked!
          </div>
          {newAchievements.map((ach) => (
            <div key={ach.key} style={{ color: '#fde68a', fontSize: '14px' }}>
              {ach.title} - {ach.description}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricCard({ icon, label, value, color }: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div style={{
      padding: '10px 12px',
      background: '#0f172a',
      borderRadius: '8px',
      border: '1px solid #334155',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>
        {icon} {label}
      </div>
      <div style={{ fontSize: '16px', fontWeight: '600', color }}>
        {value}
      </div>
    </div>
  );
}
