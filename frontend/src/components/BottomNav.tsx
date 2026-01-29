import React from 'react';

interface BottomNavProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: 'raw', label: 'Raw Market Data', icon: '🏠' },
  { id: 'overround', label: 'Overround Removal', icon: '→' },
  { id: 'baseline', label: 'Historical Baseline', icon: '📊' },
  { id: 'news', label: 'Team News Overlay', icon: '◆' },
  { id: 'report', label: 'Final Intelligence Report', icon: '📋' },
];

export const BottomNav: React.FC<BottomNavProps> = ({ activeTab, onTabChange }) => {
  return (
    <nav className="flex items-center justify-between px-6 py-3 bg-pl-card border-t border-pl-border">
      <div className="flex items-center gap-1">
        {tabs.map((tab, idx) => (
          <React.Fragment key={tab.id}>
            <button
              onClick={() => onTabChange(tab.id)}
              className={`
                flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors
                ${activeTab === tab.id 
                  ? 'bg-pl-border text-white' 
                  : 'text-pl-text-dim hover:text-white'
                }
              `}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
            {idx < tabs.length - 1 && (
              <span className="text-pl-text-dim mx-1">→</span>
            )}
          </React.Fragment>
        ))}
      </div>

      <button className="flex items-center gap-2 px-4 py-2 bg-pl-border rounded text-sm text-pl-text hover:text-white transition-colors">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
        Single Match
      </button>
    </nav>
  );
};
