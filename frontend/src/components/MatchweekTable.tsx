import React from 'react';
import type { AnalysisResponse } from '../types';

interface MatchweekTableProps {
  matches: AnalysisResponse[];
  selectedMatch: AnalysisResponse | null;
  onSelectMatch: (match: AnalysisResponse) => void;
  sortBy: 'kickoff' | 'discrepancy';
  onSortChange: (sort: 'kickoff' | 'discrepancy') => void;
  filterBiggest: boolean;
  onFilterChange: (filter: boolean) => void;
}

function getMaxDiscrepancy(match: AnalysisResponse): number {
  if (!match.discrepancies.length) return 0;
  return Math.max(...match.discrepancies.map((d) => Math.abs(d.delta)));
}

function formatTime(isoString: string): string {
  if (!isoString) return '--:--';
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function getTeamAbbrev(team: string): string {
  const abbrevs: Record<string, string> = {
    'Arsenal': 'ARS',
    'Aston Villa': 'AVL',
    'Bournemouth': 'BOU',
    'Brentford': 'BRE',
    'Brighton and Hove Albion': 'BHA',
    'Burnley': 'BUR',
    'Chelsea': 'CHE',
    'Crystal Palace': 'CRY',
    'Everton': 'EVE',
    'Fulham': 'FUL',
    'Leeds United': 'LEE',
    'Leicester City': 'LEI',
    'Liverpool': 'LIV',
    'Manchester City': 'MCI',
    'Manchester United': 'MUN',
    'Newcastle United': 'NEW',
    'Nottingham Forest': 'NFO',
    'Sheffield United': 'SHU',
    'Sunderland': 'SUN',
    'Tottenham Hotspur': 'TOT',
    'West Ham United': 'WHU',
    'Wolverhampton Wanderers': 'WOL',
  };
  return abbrevs[team] || team.slice(0, 3).toUpperCase();
}

export const MatchweekTable: React.FC<MatchweekTableProps> = ({
  matches,
  selectedMatch,
  onSelectMatch,
  sortBy,
  onSortChange,
  filterBiggest,
  onFilterChange,
}) => {
  // Sort and filter matches
  let displayMatches = [...matches];
  
  if (sortBy === 'discrepancy') {
    displayMatches.sort((a, b) => getMaxDiscrepancy(b) - getMaxDiscrepancy(a));
  } else {
    displayMatches.sort((a, b) => 
      new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime()
    );
  }

  if (filterBiggest) {
    displayMatches = displayMatches.slice(0, 5);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-pl-border">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
          MATCHWEEK OVERVIEW
        </h2>
      </div>

      <div className="flex-1 overflow-auto">
        <table className="w-full">
          <thead className="sticky top-0 bg-pl-card">
            <tr className="text-left text-xs text-pl-text-dim uppercase tracking-wider">
              <th className="px-4 py-3 font-medium">Match</th>
              <th className="px-4 py-3 font-medium">KO</th>
              <th className="px-4 py-3 font-medium">Market Fav</th>
              <th className="px-4 py-3 font-medium">Δ Discrepancy</th>
            </tr>
          </thead>
          <tbody>
            {displayMatches.map((match, idx) => {
              const isSelected = selectedMatch?.home_team === match.home_team && 
                                 selectedMatch?.away_team === match.away_team;
              const maxDelta = getMaxDiscrepancy(match);
              const favAbbrev = getTeamAbbrev(match.market_favorite);

              return (
                <tr
                  key={`${match.home_team}-${match.away_team}-${idx}`}
                  onClick={() => onSelectMatch(match)}
                  className={`
                    cursor-pointer border-b border-pl-border transition-colors
                    ${isSelected ? 'bg-pl-border/50' : 'hover:bg-pl-border/30'}
                  `}
                >
                  <td className="px-4 py-3">
                    <span className="text-white font-medium">
                      {getTeamAbbrev(match.home_team)}
                    </span>
                    <span className="text-pl-text-dim mx-1">vs</span>
                    <span className="text-white font-medium">
                      {getTeamAbbrev(match.away_team)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-pl-text-dim">
                    {formatTime(match.kickoff_utc)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-white">{favAbbrev}</span>
                    <span className="text-pl-text-dim ml-1">
                      ({(match.market_favorite_prob * 100).toFixed(0)}%)
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-medium ${maxDelta > 0.05 ? 'text-pl-accent' : 'text-pl-accent-orange'}`}>
                      {maxDelta > 0 ? '+' : ''}{(maxDelta * 100).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Progress bar placeholder */}
      <div className="px-4 py-3 border-t border-pl-border">
        <div className="h-2 bg-pl-dark rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-pl-accent-orange to-pl-accent"
            style={{ width: `${(matches.length / 20) * 100}%` }}
          />
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-pl-border">
        <label className="flex items-center gap-2 text-sm text-pl-text-dim">
          <span>Filter: Biggest Disagreements</span>
          <button
            onClick={() => onFilterChange(!filterBiggest)}
            className={`
              w-10 h-5 rounded-full transition-colors relative
              ${filterBiggest ? 'bg-pl-accent' : 'bg-pl-border'}
            `}
          >
            <span 
              className={`
                absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform
                ${filterBiggest ? 'translate-x-5' : 'translate-x-0.5'}
              `}
            />
          </button>
        </label>

        <div className="flex items-center gap-2 text-sm">
          <span className="text-pl-text-dim">Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value as 'kickoff' | 'discrepancy')}
            className="bg-pl-dark border border-pl-border rounded px-2 py-1 text-pl-text focus:outline-none focus:border-pl-accent"
          >
            <option value="kickoff">Kickoff Time</option>
            <option value="discrepancy">Discrepancy</option>
          </select>
        </div>
      </div>
    </div>
  );
};
