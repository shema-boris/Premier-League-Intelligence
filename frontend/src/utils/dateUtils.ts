import type { AnalysisResponse } from '../types';

export interface GroupedMatches {
  date: string;
  dateLabel: string;
  matches: AnalysisResponse[];
}

/**
 * Format date to display label (e.g., "SATURDAY, FEBRUARY 3")
 */
export function formatDateLabel(dateString: string): string {
  const date = new Date(dateString);
  const options: Intl.DateTimeFormatOptions = {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  };
  return date.toLocaleDateString('en-US', options).toUpperCase();
}

/**
 * Get date string (YYYY-MM-DD) from ISO timestamp
 */
export function getDateString(isoString: string): string {
  const date = new Date(isoString);
  return date.toISOString().split('T')[0];
}

/**
 * Group matches by date
 */
export function groupMatchesByDate(matches: AnalysisResponse[]): GroupedMatches[] {
  const groups = new Map<string, AnalysisResponse[]>();

  // Group matches by date
  matches.forEach(match => {
    const dateStr = getDateString(match.kickoff_utc);
    if (!groups.has(dateStr)) {
      groups.set(dateStr, []);
    }
    groups.get(dateStr)!.push(match);
  });

  // Convert to array and sort by date
  const groupedArray: GroupedMatches[] = Array.from(groups.entries())
    .map(([date, matches]) => ({
      date,
      dateLabel: formatDateLabel(matches[0].kickoff_utc),
      matches: matches.sort((a, b) => 
        new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime()
      ),
    }))
    .sort((a, b) => a.date.localeCompare(b.date));

  return groupedArray;
}

/**
 * Get relative date label (e.g., "Today", "Tomorrow", or formatted date)
 */
export function getRelativeDateLabel(dateString: string): string {
  const date = new Date(dateString);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  // Reset time parts for comparison
  const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const tomorrowOnly = new Date(tomorrow.getFullYear(), tomorrow.getMonth(), tomorrow.getDate());

  if (dateOnly.getTime() === todayOnly.getTime()) {
    return 'TODAY';
  } else if (dateOnly.getTime() === tomorrowOnly.getTime()) {
    return 'TOMORROW';
  } else {
    return formatDateLabel(dateString);
  }
}
