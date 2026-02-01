/**
 * Premier League team logo URLs from public CDN
 * Using logo.clearbit.com and fallback sources
 */

export const TEAM_LOGOS: Record<string, string> = {
  // Premier League Teams 2024/25
  'Arsenal': 'https://resources.premierleague.com/premierleague/badges/50/t3.png',
  'Aston Villa': 'https://resources.premierleague.com/premierleague/badges/50/t7.png',
  'Bournemouth': 'https://resources.premierleague.com/premierleague/badges/50/t91.png',
  'Brentford': 'https://resources.premierleague.com/premierleague/badges/50/t94.png',
  'Brighton': 'https://resources.premierleague.com/premierleague/badges/50/t36.png',
  'Brighton and Hove Albion': 'https://resources.premierleague.com/premierleague/badges/50/t36.png',
  'Brighton & Hove Albion': 'https://resources.premierleague.com/premierleague/badges/50/t36.png',
  'Chelsea': 'https://resources.premierleague.com/premierleague/badges/50/t8.png',
  'Crystal Palace': 'https://resources.premierleague.com/premierleague/badges/50/t31.png',
  'Everton': 'https://resources.premierleague.com/premierleague/badges/50/t11.png',
  'Fulham': 'https://resources.premierleague.com/premierleague/badges/50/t54.png',
  'Ipswich Town': 'https://resources.premierleague.com/premierleague/badges/50/t40.png',
  'Leicester City': 'https://resources.premierleague.com/premierleague/badges/50/t13.png',
  'Liverpool': 'https://resources.premierleague.com/premierleague/badges/50/t14.png',
  'Manchester City': 'https://resources.premierleague.com/premierleague/badges/50/t43.png',
  'Manchester United': 'https://resources.premierleague.com/premierleague/badges/50/t1.png',
  'Newcastle United': 'https://resources.premierleague.com/premierleague/badges/50/t4.png',
  'Newcastle': 'https://resources.premierleague.com/premierleague/badges/50/t4.png',
  'Nottingham Forest': 'https://resources.premierleague.com/premierleague/badges/50/t17.png',
  "Nott'ham Forest": 'https://resources.premierleague.com/premierleague/badges/50/t17.png',
  'Southampton': 'https://resources.premierleague.com/premierleague/badges/50/t20.png',
  'Tottenham': 'https://resources.premierleague.com/premierleague/badges/50/t6.png',
  'Tottenham Hotspur': 'https://resources.premierleague.com/premierleague/badges/50/t6.png',
  'West Ham': 'https://resources.premierleague.com/premierleague/badges/50/t21.png',
  'West Ham United': 'https://resources.premierleague.com/premierleague/badges/50/t21.png',
  'Wolverhampton Wanderers': 'https://resources.premierleague.com/premierleague/badges/50/t39.png',
  'Wolves': 'https://resources.premierleague.com/premierleague/badges/50/t39.png',
  
  // Recently relegated/promoted teams (for historical data)
  'Burnley': 'https://resources.premierleague.com/premierleague/badges/50/t90.png',
  'Leeds United': 'https://resources.premierleague.com/premierleague/badges/50/t2.png',
  'Luton Town': 'https://resources.premierleague.com/premierleague/badges/50/t102.png',
  'Sheffield United': 'https://resources.premierleague.com/premierleague/badges/50/t49.png',
  'Watford': 'https://resources.premierleague.com/premierleague/badges/50/t57.png',
  'Norwich City': 'https://resources.premierleague.com/premierleague/badges/50/t45.png',
};

/**
 * Get team logo URL by team name
 * Returns logo URL or null if not found
 */
export function getTeamLogoUrl(teamName: string): string | null {
  // Try exact match first
  if (TEAM_LOGOS[teamName]) {
    return TEAM_LOGOS[teamName];
  }
  
  // Try case-insensitive match
  const normalizedName = teamName.toLowerCase();
  for (const [key, value] of Object.entries(TEAM_LOGOS)) {
    if (key.toLowerCase() === normalizedName) {
      return value;
    }
  }
  
  return null;
}
