import React, { useState } from 'react';
import type { AnalysisResponse } from '../types';
import { TeamForm } from './TeamForm';
import { PredictedLineup } from './PredictedLineup';
import { HeadToHead } from './HeadToHead';
import { TeamBadge } from './TeamBadge';

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
  const [activeTab, setActiveTab] = useState<'overview' | 'form' | 'lineups' | 'h2h'>('overview');

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

  const tabs = [
    { id: 'overview' as const, label: 'Overview', icon: '📊' },
    { id: 'form' as const, label: 'Team Form', icon: '📈' },
    { id: 'lineups' as const, label: 'Lineups', icon: '⚽' },
    { id: 'h2h' as const, label: 'Head-to-Head', icon: '🔄' },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-pl-border">
        <div className="flex items-center justify-between px-4 py-3">
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
        
        {/* Tabs */}
        <div className="flex gap-1 px-4">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'border-pl-accent text-white'
                  : 'border-transparent text-pl-text-dim hover:text-white'
              }`}
            >
              <span className="mr-1">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Match Header - Always visible */}
        <div className="bg-pl-dark rounded-lg p-4">
          <div className="flex items-center justify-center gap-8 mb-4">
            {/* Home Team */}
            <div className="text-center">
              <div className="mb-2 flex justify-center">
                <TeamBadge teamName={match.home_team} size="large" />
              </div>
              <p className="text-sm text-pl-text font-medium">{match.home_team}</p>
            </div>

            <span className="text-2xl text-pl-text-dim font-light">VS</span>

            {/* Away Team */}
            <div className="text-center">
              <div className="mb-2 flex justify-center">
                <TeamBadge teamName={match.away_team} size="large" />
              </div>
              <p className="text-sm text-pl-text font-medium">{match.away_team}</p>
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

        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <>
            {/* Model Probabilities */}
            <div className="bg-pl-dark rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-4">Model Probabilities</h3>
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
            </div>

            {/* Analysis Narrative */}
            <div className="bg-pl-dark rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3">Intelligence Report</h3>
              <p className="text-sm text-pl-text leading-relaxed">{match.conclusion}</p>
            </div>
          </>
        )}

        {activeTab === 'form' && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-pl-dark rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3">{match.home_team}</h3>
              <TeamForm teamName={match.home_team} />
            </div>
            <div className="bg-pl-dark rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3">{match.away_team}</h3>
              <TeamForm teamName={match.away_team} />
            </div>
          </div>
        )}

        {activeTab === 'lineups' && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-pl-dark rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3">{match.home_team}</h3>
              <PredictedLineup teamName={match.home_team} />
            </div>
            <div className="bg-pl-dark rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3">{match.away_team}</h3>
              <PredictedLineup teamName={match.away_team} />
            </div>
          </div>
        )}

        {activeTab === 'h2h' && (
          <div className="bg-pl-dark rounded-lg p-4">
            <h3 className="text-sm font-semibold text-white mb-4">
              {match.home_team} vs {match.away_team}
            </h3>
            <HeadToHead team1={match.home_team} team2={match.away_team} />
          </div>
        )}
      </div>
    </div>
  );
};
