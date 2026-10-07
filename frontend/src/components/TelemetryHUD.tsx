import React, { useState } from 'react';
import { Cpu, Database, Activity, RefreshCw, Settings, Sun, Moon } from 'lucide-react';
import { useAppStore } from '../store';
import { AirGapBadge } from './AirGapBadge';
import { CloudSettingsModal } from './CloudSettingsModal';

export const TelemetryHUD: React.FC = () => {
  const {
    hostTelemetry,
    health,
    engineMode,
    setMode,
    tps,
    ttft,
    fetchTelemetry,
    fetchHealth,
    theme,
    toggleTheme,
  } = useAppStore();

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleModeToggle = async () => {
    if (engineMode === 'airgap') {
      if (!health?.gemini?.available) {
        setIsSettingsOpen(true);
        return;
      }
      try {
        await setMode('cloud');
      } catch {
        setIsSettingsOpen(true);
      }
    } else {
      await setMode('airgap');
    }
  };

  const handleRefresh = async () => {
    await Promise.all([fetchHealth(), fetchTelemetry()]);
  };

  return (
    <header className="bg-white/80 border-b border-slate-200/80 px-6 py-2.5 flex items-center justify-between sticky top-0 z-40 backdrop-blur-md dark:bg-[#141417]/80 dark:border-zinc-800/80 transition-colors duration-150">
      {/* Left: Brand + AirGap Badge */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold text-xs tracking-wider shadow-sm dark:bg-zinc-800 dark:border dark:border-zinc-700/60 dark:text-zinc-200">
            SR
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-slate-900 dark:text-zinc-100 flex items-center gap-1.5">
              SovereignRAG
              <span className="text-[10px] font-sans px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700/50">
                v2.0
              </span>
            </h1>
            <p className="text-[11px] text-slate-500 dark:text-zinc-400 font-sans">Private RAG Platform</p>
          </div>
        </div>

        <div className="h-5 w-px bg-slate-200 dark:bg-zinc-800 hidden sm:block" />

        <AirGapBadge />
      </div>

      {/* Center/Right: Live Telemetry Metrics */}
      <div className="flex items-center space-x-3 text-xs font-sans">
        {/* Host Memory HUD in GiB */}
        <div className="hidden lg:flex items-center space-x-2 text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 dark:text-zinc-400 dark:bg-zinc-900/60 dark:border-zinc-800/80">
          <Cpu className="w-3.5 h-3.5 text-slate-500 dark:text-zinc-400" />
          <span>RAM:</span>
          <span className="text-slate-900 font-medium dark:text-zinc-200">
            {(() => {
              const u = hostTelemetry?.used_memory_gib ?? hostTelemetry?.memory_used_gib;
              const t = hostTelemetry?.total_memory_gib ?? hostTelemetry?.memory_total_gib;
              return (u !== undefined && t !== undefined) ? `${u.toFixed(1)} / ${t.toFixed(1)} GiB` : '— GiB';
            })()}
          </span>
          <span className="text-slate-400 dark:text-zinc-500 text-[10px]">
            {(() => {
              const p = hostTelemetry?.memory_usage_percent ?? hostTelemetry?.memory_percent;
              return p !== undefined ? `(${p.toFixed(0)}%)` : '';
            })()}
          </span>
        </div>

        {/* Corpus HUD */}
        <div className="hidden md:flex items-center space-x-2 text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 dark:text-zinc-400 dark:bg-zinc-900/60 dark:border-zinc-800/80">
          <Database className="w-3.5 h-3.5 text-slate-500 dark:text-zinc-400" />
          <span>Vault:</span>
          <span className="text-slate-900 font-medium dark:text-zinc-200">
            {health?.documents ?? health?.total_documents ?? 0} docs / {health?.chunks ?? health?.total_chunks ?? 0} chunks
          </span>
        </div>

        {/* Generation Latency / TPS */}
        <div className="hidden xl:flex items-center space-x-2 text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 dark:text-zinc-400 dark:bg-zinc-900/60 dark:border-zinc-800/80">
          <Activity className="w-3.5 h-3.5 text-slate-500 dark:text-zinc-400" />
          <span>Perf:</span>
          <span className="text-slate-900 dark:text-zinc-200 font-medium">
            {tps ? `${tps.toFixed(1)} tok/s` : 'N/A'}
          </span>
          <span className="text-slate-300 dark:text-zinc-600">•</span>
          <span className="text-slate-900 dark:text-zinc-200 font-medium">
            {ttft ? `${ttft.toFixed(0)}ms TTFT` : 'N/A'}
          </span>
        </div>

        {/* Live Ollama Status Badge */}
        <div
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border text-xs font-mono transition-all ${
            health?.ollama?.available
              ? 'bg-emerald-50/70 border-emerald-300/80 text-emerald-800 dark:bg-emerald-950/30 dark:border-emerald-800/60 dark:text-emerald-300'
              : 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/30 dark:border-amber-800/50 dark:text-amber-400'
          }`}
          title={health?.ollama?.available ? `Ollama active with model: ${health?.ollama?.model}` : 'Ollama daemon offline (deterministic fallback active)'}
        >
          <span className={`w-2 h-2 rounded-full ${health?.ollama?.available ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-amber-500'}`} />
          <span className="font-semibold">Ollama:</span>
          <span className="truncate max-w-[110px]">{health?.ollama?.available ? (health?.ollama?.model || 'Online') : 'Offline'}</span>
        </div>

        {/* Engine Mode Toggle */}
        <div className="flex items-center space-x-1.5">
          <button
            onClick={handleModeToggle}
            className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition-all ${
              engineMode === 'airgap'
                ? 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100 dark:bg-zinc-800/90 dark:border-zinc-700/70 dark:text-zinc-200 dark:hover:bg-zinc-750'
                : 'bg-indigo-50 text-indigo-800 border-indigo-300 hover:bg-indigo-100 dark:bg-amber-950/40 dark:border-amber-800/50 dark:text-amber-300 dark:hover:bg-amber-950/60'
            }`}
            title="Toggle between strictly air-gapped local mode and hybrid cloud mode"
          >
            {engineMode === 'airgap' ? 'Air-gap mode' : 'Cloud mode'}
          </button>

          {/* Theme Toggle Button (Dark / Light) */}
          <button
            onClick={toggleTheme}
            className="p-1.5 text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-lg transition-colors dark:text-zinc-400 dark:hover:text-zinc-200 dark:bg-zinc-800/50 dark:hover:bg-zinc-800 dark:border-zinc-700/40"
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            aria-label="Toggle theme mode"
          >
            {theme === 'dark' ? (
              <Sun className="w-3.5 h-3.5 text-amber-400" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-slate-600" />
            )}
          </button>

          <button
            onClick={() => setIsSettingsOpen(true)}
            className="p-1.5 text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-lg transition-colors dark:text-zinc-400 dark:hover:text-zinc-200 dark:bg-zinc-800/50 dark:hover:bg-zinc-800 dark:border-zinc-700/40"
            title="Configure Gemini API Key & Mode Settings"
          >
            <Settings className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleRefresh}
            className="p-1.5 text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-lg transition-colors dark:text-zinc-400 dark:hover:text-zinc-200 dark:bg-zinc-800/50 dark:hover:bg-zinc-800 dark:border-zinc-700/40"
            title="Refresh host telemetry and health"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <CloudSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </header>
  );
};
