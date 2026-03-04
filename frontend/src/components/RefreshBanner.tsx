import React, { useState, useEffect } from 'react';

interface RefreshBannerProps {
  isRefreshing: boolean;
  justUpdated: boolean;
}

export const RefreshBanner: React.FC<RefreshBannerProps> = ({ isRefreshing, justUpdated }) => {
  const [showUpdated, setShowUpdated] = useState(false);

  useEffect(() => {
    if (justUpdated) {
      setShowUpdated(true);
      const timer = setTimeout(() => setShowUpdated(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [justUpdated]);

  if (!isRefreshing && !showUpdated) return null;

  return (
    <div className={`px-4 py-2 text-center text-sm font-medium transition-colors ${
      showUpdated 
        ? 'bg-pl-accent/20 text-pl-accent' 
        : 'bg-pl-accent-orange/20 text-pl-accent-orange'
    }`}>
      {showUpdated ? (
        <span className="flex items-center justify-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Match data updated
        </span>
      ) : (
        <span className="flex items-center justify-center gap-2">
          <div className="w-3 h-3 border-2 border-pl-accent-orange border-t-transparent rounded-full animate-spin" />
          Retrieving updated match data...
        </span>
      )}
    </div>
  );
};
