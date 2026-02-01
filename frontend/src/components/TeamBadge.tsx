import React, { useState } from 'react';
import { getTeamLogoUrl } from '../utils/teamLogos';

interface TeamBadgeProps {
  teamName: string;
  size?: 'small' | 'medium' | 'large';
  showName?: boolean;
}

const sizeClasses = {
  small: 'w-6 h-6',
  medium: 'w-12 h-12',
  large: 'w-16 h-16',
};

const textSizeClasses = {
  small: 'text-xs',
  medium: 'text-sm',
  large: 'text-base',
};

function getTeamAbbrev(team: string): string {
  const abbrevs: Record<string, string> = {
    'Arsenal': 'ARS',
    'Aston Villa': 'AVL',
    'Bournemouth': 'BOU',
    'Brentford': 'BRE',
    'Brighton and Hove Albion': 'BHA',
    'Brighton': 'BHA',
    'Burnley': 'BUR',
    'Chelsea': 'CHE',
    'Crystal Palace': 'CRY',
    'Everton': 'EVE',
    'Fulham': 'FUL',
    'Ipswich Town': 'IPS',
    'Leeds United': 'LEE',
    'Leicester City': 'LEI',
    'Liverpool': 'LIV',
    'Manchester City': 'MCI',
    'Manchester United': 'MUN',
    'Newcastle United': 'NEW',
    'Nottingham Forest': 'NFO',
    "Nott'ham Forest": 'NFO',
    'Sheffield United': 'SHU',
    'Southampton': 'SOU',
    'Tottenham Hotspur': 'TOT',
    'Tottenham': 'TOT',
    'West Ham United': 'WHU',
    'West Ham': 'WHU',
    'Wolverhampton Wanderers': 'WOL',
    'Wolves': 'WOL',
  };
  return abbrevs[team] || team.slice(0, 3).toUpperCase();
}

export const TeamBadge: React.FC<TeamBadgeProps> = ({ 
  teamName, 
  size = 'medium',
  showName = false 
}) => {
  const [error, setError] = useState(false);
  const logoUrl = getTeamLogoUrl(teamName);

  const sizeClass = sizeClasses[size];
  const textSizeClass = textSizeClasses[size];

  return (
    <div className="flex items-center gap-2">
      <div className={`${sizeClass} flex items-center justify-center flex-shrink-0`}>
        {logoUrl && !error ? (
          // Team logo from CDN
          <img
            src={logoUrl}
            alt={`${teamName} logo`}
            className={`${sizeClass} object-contain`}
            onError={() => setError(true)}
          />
        ) : (
          // Fallback badge with abbreviation
          <div className={`${sizeClass} bg-pl-border rounded-full flex items-center justify-center`}>
            <span className={`${textSizeClass} font-bold text-white`}>
              {getTeamAbbrev(teamName)}
            </span>
          </div>
        )}
      </div>
      {showName && (
        <span className="text-sm text-pl-text font-medium">{teamName}</span>
      )}
    </div>
  );
};
