import { create } from 'zustand';
import { api } from './api';
import {
  AuditRecord,
  HealthResponse,
  HostTelemetry,
  IngestedDocument,
  QueryResponse,
} from './types';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: QueryResponse;
  streaming?: boolean;
  timestamp: string;
}

export type TabId =
  | 'chat'
  | 'vault'
  | 'chunk_lab'
  | 'quant_lab'
  | 'privacy'
  | 'audit'
  | 'diagnostics';

export type ThemeMode = 'light' | 'dark';

interface AppState {
  theme: ThemeMode;
  toggleTheme: () => void;

  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;

  globalError: string | null;
  setGlobalError: (err: string | null) => void;

  health: HealthResponse | null;
  hostTelemetry: HostTelemetry | null;
  engineMode: 'airgap' | 'cloud';

  documents: IngestedDocument[];
  totalChunks: number;

  auditRecords: AuditRecord[];
  auditValid: boolean;
  auditCheckedAt: string | null;

  messages: ChatMessage[];
  tps: number | null;
  ttft: number | null;
  lastAirgapVerify: string | null;

  fetchHealth: () => Promise<void>;
  fetchTelemetry: () => Promise<void>;
  fetchDocuments: () => Promise<void>;
  fetchAudit: () => Promise<void>;
  setMode: (mode: 'airgap' | 'cloud', key?: string) => Promise<void>;
  addMessage: (msg: ChatMessage) => void;
  updateMessageContent: (id: string, chunk: string, isDone?: boolean) => void;
  setQueryResponse: (id: string, resp: QueryResponse) => void;
}

const getInitialTheme = (): ThemeMode => {
  if (typeof window !== 'undefined' && window.localStorage) {
    const saved = localStorage.getItem('sr_theme') as ThemeMode | null;
    if (saved === 'dark' || saved === 'light') {
      if (typeof document !== 'undefined') {
        if (saved === 'dark') document.documentElement.classList.add('dark');
        else document.documentElement.classList.remove('dark');
      }
      return saved;
    }
  }
  // Default to light mode for fresh, clean, aesthetic experience
  if (typeof document !== 'undefined') {
    document.documentElement.classList.remove('dark');
  }
  return 'light';
};

export const useAppStore = create<AppState>((set, get) => ({
  theme: getInitialTheme(),
  toggleTheme: () => {
    const next: ThemeMode = get().theme === 'dark' ? 'light' : 'dark';
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem('sr_theme', next);
    }
    if (typeof document !== 'undefined') {
      if (next === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
    set({ theme: next });
  },

  activeTab: 'chat',
  setActiveTab: (tab) => set({ activeTab: tab }),

  globalError: null,
  setGlobalError: (err) => set({ globalError: err }),

  health: null,
  hostTelemetry: null,
  engineMode: 'airgap',

  documents: [],
  totalChunks: 0,

  auditRecords: [],
  auditValid: true,
  auditCheckedAt: null,

  messages: [],
  tps: null,
  ttft: null,
  lastAirgapVerify: '127.0.0.1:8093 (Strict Loopback Binding)',

  fetchHealth: async () => {
    try {
      const data = await api.getHealth();
      set({
        health: data,
        engineMode: (data.mode === 'cloud' || data.engine_mode === 'cloud') ? 'cloud' : 'airgap',
        auditValid: data.audit_healthy ?? data.audit_ledger_valid ?? true,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ globalError: `Failed to connect to backend: ${msg}` });
    }
  },

  fetchTelemetry: async () => {
    try {
      const data = await api.getHostTelemetry();
      set({ hostTelemetry: data });
    } catch {
      // quiet fallback for telemetry polling
    }
  },

  fetchDocuments: async () => {
    try {
      const data = await api.getDocuments();
      const docs = data?.documents || [];
      const total = data?.total_chunks ?? docs.reduce((acc, d) => acc + (d.chunk_count || 0), 0);
      set({ documents: docs, totalChunks: total });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ globalError: `Failed to load documents: ${msg}` });
    }
  },

  fetchAudit: async () => {
    try {
      const data = await api.getAuditLogs();
      set({ auditRecords: data.records, auditValid: data.is_valid });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ globalError: `Failed to load audit logs: ${msg}` });
    }
  },

  setMode: async (mode, key) => {
    try {
      const res = await api.setMode(mode, key);
      set({ engineMode: res.mode === 'cloud' ? 'cloud' : 'airgap', globalError: null });
      await get().fetchHealth();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ globalError: `Failed to switch engine mode: ${msg}` });
      throw err;
    }
  },

  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),

  updateMessageContent: (id, chunk, isDone = false) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id
          ? {
              ...m,
              content: m.content + chunk,
              streaming: !isDone,
            }
          : m
      ),
    }));
  },

  setQueryResponse: (id, resp) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id
          ? {
              ...m,
              response: resp,
              streaming: false,
            }
          : m
      ),
    }));
  },
}));
