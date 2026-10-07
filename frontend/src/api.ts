import {
  AuditRecord,
  ConfigSettings,
  HealthResponse,
  HostTelemetry,
  IngestedDocument,
  MemoryCalculation,
  ModelOption,
  QueryRequest,
  QueryResponse,
  RedactionResult,
} from './types';

const API_BASE = typeof window !== 'undefined' && window.location.port === '8093' ? '' : 'http://127.0.0.1:8093';

export async function fetchJSON<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson) {
        if (typeof errJson.detail === 'string' && errJson.detail.trim()) {
          errorDetail = errJson.detail.trim();
        } else if (typeof errJson.message === 'string' && errJson.message.trim()) {
          errorDetail = errJson.message.trim();
        } else if (typeof errJson.error === 'string' && errJson.error.trim()) {
          errorDetail = errJson.error.trim();
        } else if (errJson.detail) {
          errorDetail = JSON.stringify(errJson.detail);
        }
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return res.json() as Promise<T>;
}

export const api = {
  getHealth: () => fetchJSON<HealthResponse>('/health'),

  getMode: () => fetchJSON<{ mode: string }>('/api/mode'),

  setMode: (mode: 'airgap' | 'cloud', gemini_api_key?: string) =>
    fetchJSON<{ mode: string }>('/api/mode', {
      method: 'POST',
      body: JSON.stringify({ mode, gemini_api_key }),
    }),

  getConfigSettings: () =>
    fetchJSON<ConfigSettings>('/api/settings/config'),

  updateConfigSettings: (payload: {
    gemini_api_key?: string;
    gemini_model?: string;
    ollama_url?: string;
    ollama_model?: string;
  }) =>
    fetchJSON<ConfigSettings>('/api/settings/config', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  testGeminiKey: (gemini_api_key?: string) =>
    fetchJSON<{ valid: boolean; model?: string; error?: string }>('/api/settings/test-gemini', {
      method: 'POST',
      body: JSON.stringify({ gemini_api_key }),
    }),

  deleteDocument: (docId: string) =>
    fetchJSON<{ deleted_chunks: number }>(`/api/rag/documents/${docId}`, {
      method: 'DELETE',
    }),

  clearDocuments: () =>
    fetchJSON<{ deleted_chunks: number }>('/api/rag/documents', {
      method: 'DELETE',
    }),


  getDocuments: () =>
    fetchJSON<{ documents: IngestedDocument[]; total_chunks: number }>('/api/rag/documents'),

  uploadDocument: (file: File, category = 'GENERAL') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);
    return fetchJSON<{ document: IngestedDocument; chunks_ingested: number }>('/api/rag/ingest', {
      method: 'POST',
      body: formData,
    });
  },

  updateDocumentCategory: (docId: string, category: string) =>
    fetchJSON<{ status: string; id: string; category: string }>(`/api/rag/documents/${docId}/category`, {
      method: 'PATCH',
      body: JSON.stringify({ category }),
    }),

  query: (req: QueryRequest) =>
    fetchJSON<QueryResponse>('/api/rag/query', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  redactPii: (text: string) =>
    fetchJSON<RedactionResult>('/api/privacy/redact', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  restorePii: (text: string, token_map: Record<string, string>) =>
    fetchJSON<{ restored_text: string }>('/api/privacy/restore', {
      method: 'POST',
      body: JSON.stringify({ text, token_map }),
    }),

  getAuditLogs: () =>
    fetchJSON<{ total_records: number; is_valid: boolean; records: AuditRecord[] }>('/api/audit/logs'),

  verifyAuditLedger: () =>
    fetchJSON<{ is_valid: boolean; total_records: number; checked_at: string }>('/api/audit/verify', {
      method: 'POST',
    }),

  getMemoryEstimate: (params: {
    model_id: string;
    quant_type: string;
    context_length: number;
    batch_size: number;
  }) => {
    const q = new URLSearchParams({
      model_id: params.model_id,
      quant_type: params.quant_type,
      context_length: params.context_length.toString(),
      batch_size: params.batch_size.toString(),
    });
    return fetchJSON<MemoryCalculation>(`/api/telemetry/memory?${q.toString()}`);
  },

  getHostTelemetry: () => fetchJSON<HostTelemetry>('/api/telemetry/host'),

  getModels: () => fetchJSON<{ models: ModelOption[] }>('/api/telemetry/models'),
};
