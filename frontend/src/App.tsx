import React, { useState, useEffect } from 'react';
import { TopBar, MatchweekTable, DeepDivePanel, BottomNav } from './components';
import { api } from './api/client';
import type { AnalysisResponse } from './types';

function App() {
  const [isDark, setIsDark] = useState(true);
  const [matches, setMatches] = useState<AnalysisResponse[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<AnalysisResponse | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'kickoff' | 'discrepancy'>('kickoff');
  const [filterBiggest, setFilterBiggest] = useState(false);
  const [activeTab, setActiveTab] = useState('report');

  useEffect(() => {
    loadMatches();
  }, []);

  const loadMatches = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.analyzeAll();
      setMatches(data);
      setLastUpdated(new Date().toISOString());
      if (data.length > 0) {
        setSelectedMatch(data[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load matches');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`${isDark ? 'dark' : ''}`}>
      <div className="min-h-screen bg-pl-dark text-pl-text flex flex-col">
        <TopBar
          lastUpdated={lastUpdated}
          isLive={!loading && matches.length > 0}
          isDark={isDark}
          onToggleTheme={() => setIsDark(!isDark)}
        />

        <main className="flex-1 flex overflow-hidden">
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-pl-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-pl-text-dim">Analyzing matches...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <p className="text-red-400 mb-4">{error}</p>
                <button
                  onClick={loadMatches}
                  className="px-4 py-2 bg-pl-accent text-white rounded hover:bg-pl-accent/80 transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Left Panel - Matchweek Overview */}
              <div className="w-1/2 border-r border-pl-border bg-pl-card">
                <MatchweekTable
                  matches={matches}
                  selectedMatch={selectedMatch}
                  onSelectMatch={setSelectedMatch}
                  sortBy={sortBy}
                  onSortChange={setSortBy}
                  filterBiggest={filterBiggest}
                  onFilterChange={setFilterBiggest}
                />
              </div>

              {/* Right Panel - Match Deep Dive */}
              <div className="w-1/2 bg-pl-card">
                <DeepDivePanel
                  match={selectedMatch}
                  onClose={() => setSelectedMatch(null)}
                />
              </div>
            </>
          )}
        </main>

        <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
      </div>
    </div>
  );
}

export default App;
