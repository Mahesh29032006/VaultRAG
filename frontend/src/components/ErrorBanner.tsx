import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useAppStore } from '../store';

export const ErrorBanner: React.FC = () => {
  const { globalError, setGlobalError } = useAppStore();

  if (!globalError) return null;

  return (
    <div className="w-full bg-rose-50 border-b border-rose-200 text-rose-800 px-4 py-2.5 flex items-center justify-between text-xs backdrop-blur-sm sticky top-0 z-50 dark:bg-[#181214] dark:border-red-900/40 dark:text-red-200">
      <div className="flex items-center space-x-2.5">
        <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-red-400 shrink-0" />
        <span className="font-semibold text-rose-900 dark:text-red-200">{globalError}</span>
      </div>
      <button
        onClick={() => setGlobalError(null)}
        className="p-1 hover:bg-rose-100 rounded text-rose-600 hover:text-rose-900 transition-colors dark:hover:bg-red-950/60 dark:text-red-400 dark:hover:text-red-200"
        aria-label="Dismiss error"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
