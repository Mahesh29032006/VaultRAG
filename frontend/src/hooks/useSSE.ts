import { useState, useCallback } from 'react';

interface StreamCallbacks {
  onMetadata?: (data: { requestId: string; retrievalMs: number; sources: number }) => void;
  onToken?: (token: string) => void;
  onComplete?: (data: { verified: boolean; grounding_heuristic: number }) => void;
  onError?: (err: string) => void;
}

export function useSSE() {
  const [isStreaming, setIsStreaming] = useState(false);

  const streamChat = useCallback(
    async (
      query: string,
      mode: 'airgap' | 'cloud',
      callbacks: StreamCallbacks
    ) => {
      setIsStreaming(true);
      try {
        const apiBase = typeof window !== 'undefined' && window.location.port === '8093' ? '' : 'http://127.0.0.1:8093';
        const response = await fetch(`${apiBase}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query, mode, top_k: 4, redact_pii: true, use_rag: true }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('ReadableStream not supported by browser.');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data: ')) {
              const jsonStr = trimmed.slice(6);
              try {
                const event = JSON.parse(jsonStr);
                if (event.type === 'metadata') {
                  callbacks.onMetadata?.({
                    requestId: event.requestId,
                    retrievalMs: event.retrievalMs,
                    sources: event.sources,
                  });
                } else if (event.type === 'token') {
                  callbacks.onToken?.(event.text);
                } else if (event.type === 'complete') {
                  callbacks.onComplete?.({
                    verified: event.verified,
                    grounding_heuristic: event.grounding_heuristic,
                  });
                } else if (event.type === 'error') {
                  callbacks.onError?.(event.message || 'Stream error');
                }
              } catch {
                // Ignore parse errors on incomplete chunk
              }
            }
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        callbacks.onError?.(msg);
      } finally {
        setIsStreaming(false);
      }
    },
    []
  );

  return { streamChat, isStreaming };
}
