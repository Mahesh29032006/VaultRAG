import React, { useEffect } from 'react';
import {
  MessageSquare,
  Database,
  Split,
  Cpu,
  Shield,
  FileCheck,
  Activity,
} from 'lucide-react';
import { useAppStore, TabId } from './store';
import { TelemetryHUD } from './components/TelemetryHUD';
import { ErrorBanner } from './components/ErrorBanner';
import { ChatInterface } from './components/ChatInterface';
import { RagVault } from './components/RagVault';
import { ChunkLab } from './components/ChunkLab';
import { QuantizationMatrix } from './components/QuantizationMatrix';
import { PiiInspector } from './components/PiiInspector';
import { ComplianceAuditLedger } from './components/ComplianceAuditLedger';
import { DiagnosticsView } from './components/DiagnosticsView';

interface TabItem {
  id: TabId;
  label: string;
  icon: React.FC<{ className?: string }>;
}

const TABS: TabItem[] = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'vault', label: 'RAG Vault', icon: Database },
  { id: 'chunk_lab', label: 'Chunk Lab', icon: Split },
  { id: 'quant_lab', label: 'Quant Lab', icon: Cpu },
  { id: 'privacy', label: 'Privacy', icon: Shield },
  { id: 'audit', label: 'Audit', icon: FileCheck },
  { id: 'diagnostics', label: 'Diagnostics', icon: Activity },
];

export const App: React.FC = () => {
  const { activeTab, setActiveTab, fetchHealth, fetchTelemetry, fetchDocuments } = useAppStore();

  useEffect(() => {
    fetchHealth();
    fetchTelemetry();
    fetchDocuments();

    // Poll health & telemetry every 15s
    const interval = setInterval(() => {
      fetchHealth();
      fetchTelemetry();
    }, 15000);

    return () => clearInterval(interval);
  }, [fetchHealth, fetchTelemetry, fetchDocuments]);

  return (
    <div className="min-h-screen bg-ambient-canvas text-slate-800 dark:text-zinc-100 flex flex-col antialiased selection:bg-indigo-100 selection:text-indigo-900 dark:selection:bg-zinc-800 dark:selection:text-zinc-100 transition-colors duration-150">
      <ErrorBanner />
      <TelemetryHUD />

      {/* Tab Navigation Bar */}
      <nav className="bg-white/80 border-b border-slate-200/80 px-6 backdrop-blur-md sticky top-[57px] z-30 dark:bg-[#141417]/80 dark:border-zinc-800/60">
        <div className="max-w-6xl mx-auto flex space-x-1 sm:space-x-1.5 overflow-x-auto py-2">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl text-xs font-medium transition-all shrink-0 ${
                  isActive
                    ? 'bg-slate-900 text-white shadow-sm border border-slate-900 dark:bg-zinc-800 dark:text-zinc-100 dark:border-zinc-700/60'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70 border border-transparent dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-800/40'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white dark:text-zinc-200' : 'text-slate-400 dark:text-zinc-400'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Tab Content Body */}
      <main className="flex-1 overflow-x-hidden">
        {activeTab === 'chat' && <ChatInterface />}
        {activeTab === 'vault' && <RagVault />}
        {activeTab === 'chunk_lab' && <ChunkLab />}
        {activeTab === 'quant_lab' && <QuantizationMatrix />}
        {activeTab === 'privacy' && <PiiInspector />}
        {activeTab === 'audit' && <ComplianceAuditLedger />}
        {activeTab === 'diagnostics' && <DiagnosticsView />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200/80 bg-white/60 backdrop-blur-sm px-6 py-3.5 text-center text-xs text-slate-500 dark:border-zinc-800/60 dark:bg-[#0f0f11]/60 dark:text-zinc-500">
        SovereignRAG Platform • Strict Loopback 127.0.0.1:8093 • HIPAA Safe Harbor 18-Category Engine • SHA-256 Tamper-Evident Ledger
      </footer>
    </div>
  );
};

export default App;
