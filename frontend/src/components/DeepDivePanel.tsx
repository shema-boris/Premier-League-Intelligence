import React from 'react';
import type { AnalysisResponse } from '../types';

interface DeepDivePanelProps {
  match: AnalysisResponse | null;
  onClose: () => void;
}

function formatTime(isoString: string): string {
  if (!isoString) return '--:--';
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

export const DeepDivePanel: React.FC<DeepDivePanelProps> = ({ match, onClose }) => {
  if (!match) {
    return (
      <div className="flex items-center justify-center h-full text-pl-text-dim">
        <p>Select a match to view details</p>
      </div>
    );
  }

  const homeDisc = match.discrepancies.find(d => d.outcome === 'home');
  const drawDisc = match.discrepancies.find(d => d.outcome === 'draw');
  const awayDisc = match.discrepancies.find(d => d.outcome === 'away');

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-pl-border">
        <h2 className="text-lg font-semibold text-white">MATCH DEEP DIVE</h2>
        <button
          onClick={onClose}
          className="text-pl-text-dim hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Match Header Card */}
        <div className="bg-pl-dark rounded-lg p-4">
          <div className="flex items-center justify-center gap-8 mb-4">
            {/* Home Team */}
            <div className="text-center">
              <div className="w-16 h-16 bg-pl-border rounded-full flex items-center justify-center mb-2 mx-auto">
                <span className="text-2xl font-bold text-white">
                  {match.home_team.slice(0, 3).toUpperCase()}
                </span>
              </div>
              <p className="text-sm text-pl-text">{match.home_team}</p>
            </div>

            <span className="text-2xl text-pl-text-dim font-light">V</span>

            {/* Away Team */}
            <div className="text-center">
              <div className="w-16 h-16 bg-pl-border rounded-full flex items-center justify-center mb-2 mx-auto">
                <span className="text-2xl font-bold text-white">
                  {match.away_team.slice(0, 3).toUpperCase()}
                </span>
              </div>
              <p className="text-sm text-pl-text">{match.away_team}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-pl-text-dim">KICKOFF: {formatTime(match.kickoff_utc)}</p>
              <p className="text-pl-text-dim">VENUE: —</p>
            </div>
            <div className="text-right">
              <p className="text-pl-text">
                MARKET: {match.market_favorite} {(match.market_favorite_prob * 100).toFixed(0)}%
              </p>
              <p className="text-pl-text">
                MODEL: {match.model_favorite} {(match.model_favorite_prob * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {/* Quick toggle buttons */}
          <div className="flex items-center justify-center gap-2 mt-4">
            <button className="px-3 py-1 bg-pl-border rounded text-xs text-pl-text-dim hover:text-white transition-colors">
              Data With
            </button>
            <button className="px-3 py-1 bg-pl-accent/20 text-pl-accent rounded text-xs font-medium">
              MODEL
            </button>
          </div>
        </div>

        {/* Team News Impact */}
        <div className="bg-pl-dark rounded-lg p-4">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            TEAM NEWS IMPACT
          </h3>

          <div className="space-y-4">
            {/* Probability bars */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-pl-text-dim">
                <span>Home</span>
                <span>Draw</span>
                <span>Away</span>
              </div>
              <div className="flex gap-1 h-8">
                <div 
                  className="bg-pl-accent rounded-l flex items-center justify-center text-xs font-medium text-white"
                  style={{ width: `${(homeDisc?.model_probability || 0.33) * 100}%` }}
                >
                  {((homeDisc?.model_probability || 0.33) * 100).toFixed(0)}%
                </div>
                <div 
                  className="bg-pl-text-dim flex items-center justify-center text-xs font-medium text-white"
                  style={{ width: `${(drawDisc?.model_probability || 0.33) * 100}%` }}
                >
                  {((drawDisc?.model_probability || 0.33) * 100).toFixed(0)}%
                </div>
                <div 
                  className="bg-pl-accent-orange rounded-r flex items-center justify-center text-xs font-medium text-white"
                  style={{ width: `${(awayDisc?.model_probability || 0.33) * 100}%` }}
                >
                  {((awayDisc?.model_probability || 0.33) * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Injury placeholders */}
            <div className="text-sm text-pl-text-dim">
              <p className="mb-2 text-white">{match.home_team.toUpperCase()}</p>
              <p className="text-xs italic">No injury data available (off-season)</p>
            </div>

            <div className="pt-2 border-t border-pl-border">
              <p className="text-sm">
                <span className="text-pl-text-dim">Net Team Swing: </span>
                <span className="text-pl-accent">+0.00 xG</span>
              </p>
              <p className="text-xs text-pl-text-dim">No significant injury impact</p>
            </div>
          </div>
        </div>

        {/* Discrepancy Narrative */}
        <div className="bg-pl-dark rounded-lg p-4">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            DISCREPANCY NARRATIVE
          </h3>
          <p className="text-sm text-pl-text leading-relaxed">
            {match.conclusion}
          </p>
        </div>
      </div>
    </div>
  );
};
