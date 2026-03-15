import type { PhonemeCoverage } from '../types';

interface Props {
  coverage: PhonemeCoverage;
}

const categoryLabels: Record<string, string> = {
  plosive: 'Plosives',
  affricate: 'Affricates',
  fricative: 'Fricatives',
  nasal: 'Nasals',
  liquid: 'Liquids',
  semivowel: 'Semivowels',
  vowel: 'Vowels',
};

export function PhonemeMap({ coverage }: Props) {
  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '20px',
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
      }}>
        <h3 style={{ margin: 0, color: '#e2e8f0', fontSize: '16px' }}>
          Phoneme Coverage
        </h3>
        <span style={{
          fontSize: '24px',
          fontWeight: 'bold',
          color: coverage.coverage_percentage >= 90 ? '#4ade80' :
                 coverage.coverage_percentage >= 70 ? '#60a5fa' :
                 coverage.coverage_percentage >= 50 ? '#fbbf24' : '#f87171',
        }}>
          {coverage.coverage_percentage}%
        </span>
      </div>

      {/* Overall progress bar */}
      <div style={{
        height: '8px',
        background: '#334155',
        borderRadius: '4px',
        marginBottom: '20px',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${coverage.coverage_percentage}%`,
          background: 'linear-gradient(90deg, #4ade80, #22d3ee)',
          borderRadius: '4px',
          transition: 'width 0.5s ease',
        }} />
      </div>

      {/* Category breakdown */}
      {Object.entries(coverage.categories).map(([key, cat]) => (
        <div key={key} style={{ marginBottom: '12px' }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: '6px',
            fontSize: '13px',
          }}>
            <span style={{ color: '#94a3b8' }}>{categoryLabels[key] || key}</span>
            <span style={{ color: '#e2e8f0' }}>{cat.covered}/{cat.total}</span>
          </div>
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {Object.entries(cat.phonemes).map(([phoneme, status]) => {
              const isCovered = typeof status === 'boolean' ? status : status.covered;
              return (
                <span
                  key={phoneme}
                  title={`${phoneme} - ${isCovered ? 'covered' : 'missing'}`}
                  style={{
                    display: 'inline-block',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontFamily: 'monospace',
                    fontWeight: '600',
                    background: isCovered ? '#4ade8033' : '#33415566',
                    color: isCovered ? '#4ade80' : '#64748b',
                    border: `1px solid ${isCovered ? '#4ade8044' : '#334155'}`,
                  }}
                >
                  {phoneme}
                </span>
              );
            })}
          </div>
        </div>
      ))}

      {coverage.missing_phonemes.length > 0 && (
        <div style={{
          marginTop: '12px',
          padding: '8px 12px',
          background: '#0f172a',
          borderRadius: '6px',
          fontSize: '12px',
          color: '#94a3b8',
        }}>
          Missing: {coverage.missing_phonemes.join(', ')}
        </div>
      )}
    </div>
  );
}
