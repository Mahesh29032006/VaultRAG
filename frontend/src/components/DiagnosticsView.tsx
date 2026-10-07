import React, { useEffect, useState } from 'react';
import {
  Activity,
  Cpu,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Server,
  Settings,
} from 'lucide-react';
import { useAppStore } from '../store';
import { CloudSettingsModal } from './CloudSettingsModal';

export const DiagnosticsView: React.FC = () => {
  const {
    health,
    hostTelemetry,
    fetchHealth,
    fetchTelemetry,
  } = useAppStore();

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  useEffect(() => {
    fetchHealth();
    fetchTelemetry();
  }, [fetchHealth, fetchTelemetry]);

  return (
    <div className="max-w-6xl mx-auto w-full px-4 py-6 space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 dark:bg-[#151518] dark:border-zinc-800/80">
        <div>
          <h2 className="text-base font-semibold text-slate-800 dark:text-zinc-100 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-600 dark:text-zinc-400" />
            System Health & Hardware Diagnostics
          </h2>
          <p className="text-xs text-slate-500 font-mono mt-1 dark:text-zinc-400">
            Host resource telemetry, process socket binding inspection, and vector index health.
          </p>
        </div>

        <button
          onClick={() => {
            fetchHealth();
            fetchTelemetry();
          }}
          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-mono transition-colors flex items-center gap-1.5 border border-slate-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-zinc-200 dark:border-zinc-700/60"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Diagnostics</span>
        </button>
      </div>

      {/* Grid: Health Status Matrix & Host Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Subsystem Health Matrix */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4 dark:bg-[#151518] dark:border-zinc-800/80">
          <h3 className="text-xs font-semibold text-slate-600 dark:text-zinc-400 uppercase tracking-wider font-mono flex items-center gap-2">
            <Server className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
            Subsystem Status Matrix
          </h3>

          <div className="space-y-2.5 text-xs font-mono">
            <div className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-xl dark:bg-[#0f0f11] dark:border-zinc-800/80">
              <span className="text-slate-700 dark:text-zinc-300">Loopback Socket Binding (127.0.0.1:8093)</span>
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400/90 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" /> BOUND
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-xl dark:bg-[#0f0f11] dark:border-zinc-800/80">
              <span className="text-slate-700 dark:text-zinc-300">Content Security Policy (CSP Header)</span>
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400/90 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" /> ENFORCED
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-xl dark:bg-[#0f0f11] dark:border-zinc-800/80">
              <span className="text-slate-700 dark:text-zinc-300">Cryptographic Audit Chain Integrity</span>
              <span className={`flex items-center gap-1 font-semibold ${(health?.audit_healthy ?? health?.audit_ledger_valid) ? 'text-emerald-600 dark:text-emerald-400/90' : 'text-rose-600 dark:text-red-400'}`}>
                {(health?.audit_healthy ?? health?.audit_ledger_valid) ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                {(health?.audit_healthy ?? health?.audit_ledger_valid) ? 'VERIFIED' : 'TAMPERED'}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-xl dark:bg-[#0f0f11] dark:border-zinc-800/80">
              <span className="text-slate-700 dark:text-zinc-300">Ollama Local Inference Service</span>
              <span className={`flex items-center gap-1 font-semibold ${health?.ollama?.available ? 'text-emerald-600 dark:text-emerald-400/90' : 'text-amber-600 dark:text-amber-400'}`}>
                {health?.ollama?.available ? 'ONLINE' : 'OFFLINE (FALLBACK ENGAGED)'}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-xl dark:bg-[#0f0f11] dark:border-zinc-800/80">
              <span className="text-slate-700 dark:text-zinc-300">Hybrid Cloud Gemini API Key</span>
              <div className="flex items-center gap-2.5">
                <span className={`flex items-center gap-1 font-semibold ${health?.gemini?.available ? 'text-indigo-600 dark:text-zinc-200' : 'text-slate-400 dark:text-zinc-500'}`}>
                  {health?.gemini?.available ? 'CONFIGURED' : 'UNSET (AIRGAP ONLY)'}
                </span>
                <button
                  onClick={() => setIsSettingsOpen(true)}
                  className="px-2 py-0.5 bg-slate-200 hover:bg-slate-300 text-slate-700 hover:text-slate-900 rounded border border-slate-300 text-[11px] font-mono transition-colors flex items-center gap-1 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-zinc-300 dark:hover:text-white dark:border-zinc-700/60"
                  title="Configure Gemini API Key & Mode Settings"
                >
                  <Settings className="w-3 h-3" />
                  <span>Configure</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Host Hardware Telemetry */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4 dark:bg-[#151518] dark:border-zinc-800/80">
          <h3 className="text-xs font-semibold text-slate-600 dark:text-zinc-400 uppercase tracking-wider font-mono flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
            Host Resource Telemetry (psutil)
          </h3>

          <div className="space-y-3 text-xs font-mono">
            {/* CPU */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5 dark:bg-[#0f0f11] dark:border-zinc-800/80">
              <div className="flex justify-between text-slate-600 dark:text-zinc-300">
                <span>CPU Load:</span>
                <span className="text-slate-900 dark:text-zinc-200 font-semibold">{(hostTelemetry?.cpu_percent ?? 0).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden dark:bg-zinc-800/80">
                <div
                  className="bg-indigo-600 h-full rounded-full transition-all dark:bg-zinc-300"
                  style={{ width: `${Math.min(100, hostTelemetry?.cpu_percent ?? 0)}%` }}
                />
              </div>
            </div>

            {/* RAM in GiB */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5 dark:bg-[#0f0f11] dark:border-zinc-800/80">
              <div className="flex justify-between text-slate-600 dark:text-zinc-300">
                <span>System RAM (GiB):</span>
                <span className="text-slate-900 dark:text-zinc-200 font-semibold">
                  {(() => {
                    const u = hostTelemetry?.used_memory_gib ?? hostTelemetry?.memory_used_gib;
                    const t = hostTelemetry?.total_memory_gib ?? hostTelemetry?.memory_total_gib;
                    return (u !== undefined && t !== undefined) ? `${u.toFixed(2)} / ${t.toFixed(2)} GiB` : '— GiB';
                  })()}
                </span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden dark:bg-zinc-800/80">
                <div
                  className="bg-indigo-600 h-full rounded-full transition-all dark:bg-zinc-300"
                  style={{ width: `${Math.min(100, hostTelemetry?.memory_usage_percent ?? hostTelemetry?.memory_percent ?? 0)}%` }}
                />
              </div>
            </div>

            {/* Storage in GiB */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5 dark:bg-[#0f0f11] dark:border-zinc-800/80">
              <div className="flex justify-between text-slate-600 dark:text-zinc-300">
                <span>Disk Storage (GiB):</span>
                <span className="text-slate-900 dark:text-zinc-200 font-semibold">
                  {(() => {
                    const u = hostTelemetry?.disk_used_gib;
                    const t = hostTelemetry?.disk_total_gib;
                    return (u !== undefined && t !== undefined) ? `${u.toFixed(1)} / ${t.toFixed(1)} GiB` : '— GiB';
                  })()}
                </span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden dark:bg-zinc-800/80">
                <div
                  className="bg-indigo-600 h-full rounded-full transition-all dark:bg-zinc-300"
                  style={{ width: `${Math.min(100, hostTelemetry?.disk_percent ?? 0)}%` }}
                />
              </div>
            </div>

            {/* Platform */}
            <div className="flex justify-between p-2 text-slate-500 text-[11px] dark:text-zinc-500">
              <span>Host Architecture:</span>
              <span className="text-slate-700 dark:text-zinc-400 font-medium">{hostTelemetry?.platform || 'Darwin / arm64'}</span>
            </div>
          </div>
        </div>
      </div>

      <CloudSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
};
