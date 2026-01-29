import React from 'react';

interface TopBarProps {
  lastUpdated: string | null;
  isLive: boolean;
  isDark: boolean;
  onToggleTheme: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  lastUpdated,
  isLive,
  isDark,
  onToggleTheme,
}) => {
  return (
    <header className="flex items-center justify-between px-6 py-3 bg-pl-card border-b border-pl-border">
      <div className="flex items-center gap-6">
        <h1 className="text-xl font-bold text-white tracking-wide">
          PL MARKET INTELLIGENCE
        </h1>
        
        <div className="flex items-center gap-4">
          {isLive && (
            <span className="flex items-center gap-2 text-sm">
              <span className="w-2 h-2 bg-pl-accent rounded-full animate-pulse" />
              <span className="text-pl-accent font-medium">LIVE</span>
            </span>
          )}
          
          <span className="px-2 py-1 text-xs bg-pl-dark rounded text-pl-text-dim">
            API: ACTIVE
          </span>
          
          <span className="px-2 py-1 text-xs bg-pl-dark rounded text-pl-text-dim">
            SYNCED
          </span>
          
          {lastUpdated && (
            <span className="text-xs text-pl-text-dim">
              Last Updated: {new Date(lastUpdated).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="text-pl-text-dim hover:text-white transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
        
        <button
          onClick={onToggleTheme}
          className="flex items-center gap-2 text-sm text-pl-text-dim hover:text-white transition-colors"
        >
          {isDark ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
          Toggle Mode
        </button>
      </div>
    </header>
  );
};
