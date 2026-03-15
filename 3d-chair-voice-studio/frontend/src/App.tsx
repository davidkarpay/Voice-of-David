import { useState, useCallback } from 'react';
import { Mic, LayoutDashboard, ArrowLeft, ListChecks } from 'lucide-react';
import { DashboardView } from './components/Dashboard';
import { RecordingStudio } from './components/RecordingStudio';
import { ReviewRecordings } from './components/ReviewRecordings';
import type { RecordingCategory } from './types';

type View = 'dashboard' | 'studio' | 'review';

function App() {
  const [view, setView] = useState<View>('dashboard');
  const [studioCategory, setStudioCategory] = useState<RecordingCategory>('phonetic');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleStartSession = useCallback((category: RecordingCategory) => {
    setStudioCategory(category);
    setView('studio');
  }, []);

  const handleRecordingComplete = useCallback(() => {
    // Don't bump refreshKey here — it remounts RecordingStudio,
    // which reloads prompts and resets the index back to 0.
    // Dashboard will refresh when user navigates back.
  }, []);

  const handleBackToDashboard = useCallback(() => {
    setView('dashboard');
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0f172a',
      color: '#e2e8f0',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    }}>
      {/* Header */}
      <header style={{
        padding: '16px 24px',
        borderBottom: '1px solid #1e293b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {view === 'studio' && (
            <button
              onClick={handleBackToDashboard}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
              }}
            >
              <ArrowLeft size={20} />
            </button>
          )}
          <Mic size={24} color="#4ade80" />
          <h1 style={{ margin: 0, fontSize: '20px', fontWeight: '700' }}>
            David's Voice
          </h1>
        </div>
        <nav style={{ display: 'flex', gap: '8px' }}>
          <NavButton
            icon={<LayoutDashboard size={16} />}
            label="Dashboard"
            active={view === 'dashboard'}
            onClick={handleBackToDashboard}
          />
          <NavButton
            icon={<Mic size={16} />}
            label="Record"
            active={view === 'studio'}
            onClick={() => setView('studio')}
          />
          <NavButton
            icon={<ListChecks size={16} />}
            label="Review"
            active={view === 'review'}
            onClick={() => setView('review')}
          />
        </nav>
      </header>

      {/* Main content */}
      <main style={{ maxWidth: '900px', margin: '0 auto', padding: '24px' }}>
        {view === 'dashboard' && (
          <DashboardView
            key={refreshKey}
            onStartSession={handleStartSession}
          />
        )}
        {view === 'studio' && (
          <div>
            <div style={{
              marginBottom: '20px',
              padding: '12px 16px',
              background: '#1e293b',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <span style={{ fontSize: '14px', color: '#94a3b8' }}>
                Category: <strong style={{ color: '#e2e8f0' }}>{studioCategory}</strong>
              </span>
              <div style={{ display: 'flex', gap: '6px' }}>
                {(['phonetic', 'conversational', 'emotional', 'domain', 'narrative'] as RecordingCategory[]).map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setStudioCategory(cat)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '4px',
                      border: 'none',
                      background: cat === studioCategory ? '#4ade8033' : 'transparent',
                      color: cat === studioCategory ? '#4ade80' : '#64748b',
                      fontSize: '12px',
                      cursor: 'pointer',
                      textTransform: 'capitalize',
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>
            <RecordingStudio
              key={studioCategory}
              category={studioCategory}
              onRecordingComplete={handleRecordingComplete}
            />
          </div>
        )}
        {view === 'review' && <ReviewRecordings />}
      </main>
    </div>
  );
}

function NavButton({ icon, label, active, onClick }: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '8px 14px',
        borderRadius: '8px',
        border: 'none',
        background: active ? '#1e293b' : 'transparent',
        color: active ? '#e2e8f0' : '#64748b',
        fontSize: '14px',
        cursor: 'pointer',
        fontWeight: active ? '600' : '400',
      }}
    >
      {icon} {label}
    </button>
  );
}

export default App;
