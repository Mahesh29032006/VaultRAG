import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Shield,
  FileText,
  Zap,
  Lock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useAppStore } from '../store';
import { api } from '../api';
import { QueryResponse, RetrievedChunk, ClaimVerification } from '../types';

export const ChatInterface: React.FC = () => {
  const {
    messages,
    addMessage,
    updateMessageContent,
    setQueryResponse,
    engineMode,
    setMode,
    setGlobalError,
  } = useAppStore();

  const [input, setInput] = useState('');
  const [topK, setTopK] = useState(4);
  const [redactPii, setRedactPii] = useState(true);
  const [loading, setLoading] = useState(false);
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const toggleDetails = (id: string) => {
    setExpandedDetails((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const queryText = input.trim();
    if (!queryText || loading) return;

    setInput('');
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    addMessage({
      id: userMsgId,
      role: 'user',
      content: queryText,
      timestamp: new Date().toLocaleTimeString(),
    });

    addMessage({
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      streaming: true,
      timestamp: new Date().toLocaleTimeString(),
    });

    setLoading(true);

    try {
      const resp: QueryResponse = await api.query({
        query: queryText,
        top_k: topK,
        mode: engineMode,
        redact_pii: redactPii,
        use_rag: true,
      });

      setQueryResponse(assistantMsgId, resp);
      updateMessageContent(assistantMsgId, resp.answer, true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setGlobalError(`Query Error: ${msg}`);
      updateMessageContent(
        assistantMsgId,
        `⚠️ Error processing query: ${msg}`,
        true
      );
    } finally {
      setLoading(false);
    }
  };

  const handleQuickPrompt = (promptText: string) => {
    setInput(promptText);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] max-w-6xl mx-auto w-full px-4 py-4">
      {/* Quick Prompt Suggestions */}
      {messages.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-6 space-y-6">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-100/70 via-rose-100/50 to-slate-100 border border-amber-200/40 text-slate-700 dark:bg-zinc-900 dark:border-zinc-800 dark:text-zinc-400 flex items-center justify-center shadow-sm">
            <Lock className="w-5 h-5" />
          </div>
          <div className="max-w-md space-y-2">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-zinc-100 tracking-tight">Private Document Intelligence</h2>
            <p className="text-xs text-slate-500 dark:text-zinc-400 leading-relaxed">
              Query confidential clinical, financial, defense, and legal documents with HIPAA Safe Harbor de-identification, SHA-256 tamper-evident logging, and strict air-gapped isolation.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl w-full text-left">
            <button
              onClick={() => handleQuickPrompt("What is the Torsemide dosage prescribed to the patient?")}
              className="p-3.5 bg-white hover:bg-emerald-50/50 border border-slate-200 hover:border-emerald-300 rounded-xl text-xs text-slate-700 transition-all text-left flex items-start gap-3 shadow-sm dark:bg-[#151518] dark:hover:bg-[#1b1b1f] dark:border-zinc-800/80 dark:hover:border-zinc-700 dark:text-zinc-300"
            >
              <div className="p-1.5 rounded-lg bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 shrink-0 mt-0.5">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <span className="font-semibold text-slate-900 dark:text-zinc-200 block">Clinical EHR Query</span>
                <span className="text-slate-500 dark:text-zinc-500 text-[11px]">Torsemide dosage & switch from IV Lasix</span>
              </div>
            </button>

            <button
              onClick={() => handleQuickPrompt("What is the aggregate liability cap under Section 8?")}
              className="p-3.5 bg-white hover:bg-sky-50/50 border border-slate-200 hover:border-sky-300 rounded-xl text-xs text-slate-700 transition-all text-left flex items-start gap-3 shadow-sm dark:bg-[#151518] dark:hover:bg-[#1b1b1f] dark:border-zinc-800/80 dark:hover:border-zinc-700 dark:text-zinc-300"
            >
              <div className="p-1.5 rounded-lg bg-sky-100 text-sky-700 dark:bg-sky-500/10 dark:text-sky-400 shrink-0 mt-0.5">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <span className="font-semibold text-slate-900 dark:text-zinc-200 block">Legal MSA Query</span>
                <span className="text-slate-500 dark:text-zinc-500 text-[11px]">Aggregate liability cap and governing state law</span>
              </div>
            </button>

            <button
              onClick={() => handleQuickPrompt("What are the operational frequency bands of the Spectre-9 AESA radar?")}
              className="p-3.5 bg-white hover:bg-amber-50/50 border border-slate-200 hover:border-amber-300 rounded-xl text-xs text-slate-700 transition-all text-left flex items-start gap-3 shadow-sm dark:bg-[#151518] dark:hover:bg-[#1b1b1f] dark:border-zinc-800/80 dark:hover:border-zinc-700 dark:text-zinc-300"
            >
              <div className="p-1.5 rounded-lg bg-amber-100 text-amber-800 dark:bg-amber-500/10 dark:text-amber-400 shrink-0 mt-0.5">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <span className="font-semibold text-slate-900 dark:text-zinc-200 block">Defense Radar Query</span>
                <span className="text-slate-500 dark:text-zinc-500 text-[11px]">Spectre-9 radar frequencies & GaN T/R modules</span>
              </div>
            </button>

            <button
              onClick={() => handleQuickPrompt("What is the Net Asset Value NAV of Apex Meridian Master Fund?")}
              className="p-3.5 bg-white hover:bg-purple-50/50 border border-slate-200 hover:border-purple-300 rounded-xl text-xs text-slate-700 transition-all text-left flex items-start gap-3 shadow-sm dark:bg-[#151518] dark:hover:bg-[#1b1b1f] dark:border-zinc-800/80 dark:hover:border-zinc-700 dark:text-zinc-300"
            >
              <div className="p-1.5 rounded-lg bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400 shrink-0 mt-0.5">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <span className="font-semibold text-slate-900 dark:text-zinc-200 block">Financial Audit Query</span>
                <span className="text-slate-500 dark:text-zinc-500 text-[11px]">Fund Net Asset Value and 1-Day Value at Risk</span>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Messages Scroll Area */}
      {messages.length > 0 && (
        <div className="flex-1 overflow-y-auto space-y-6 pr-2 mb-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${
                msg.role === 'user' ? 'items-end' : 'items-start'
              }`}
            >
              <div
                className={`max-w-3xl rounded-2xl p-4 text-sm ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-sm shadow-sm dark:bg-zinc-800 dark:text-zinc-100 dark:border dark:border-zinc-700/50'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm dark:bg-[#151518] dark:border-zinc-800/80 dark:text-zinc-200'
                }`}
              >
                {/* User Role indicator */}
                <div
                  className={`text-[10px] font-mono mb-1 flex items-center justify-between gap-4 ${
                    msg.role === 'user' ? 'text-indigo-200 dark:text-zinc-400' : 'text-slate-400 dark:text-zinc-500'
                  }`}
                >
                  <span>{msg.role === 'user' ? 'YOU (QUERY)' : 'SOVEREIGN RAG'}</span>
                  <span>{msg.timestamp}</span>
                </div>

                {/* Message Body */}
                <div
                  className={`whitespace-pre-wrap leading-relaxed font-sans ${
                    msg.role === 'user' ? 'text-white dark:text-zinc-100' : 'text-slate-800 dark:text-zinc-200'
                  }`}
                >
                  {msg.content || (msg.streaming ? 'Synthesizing air-gapped evidence...' : '')}
                </div>

                {/* Cloud Egress Policy Blocked Banner */}
                {msg.content && (msg.content.includes('SensitiveDataCloudBlocked') || msg.content.includes('sensitive category') || msg.content.includes('Transfer to external cloud model is prohibited')) && (
                  <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs space-y-2 dark:bg-amber-950/20 dark:border-amber-600/30">
                    <div className="font-semibold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                      <Shield className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                      <span>Sovereign Air-Gap Security Safeguard</span>
                    </div>
                    <p className="text-slate-700 dark:text-zinc-300 leading-relaxed text-[11px]">
                      By design, documents categorized as <strong>CLINICAL, FINANCIAL, LEGAL, or DEFENSE</strong> are strictly air-gapped and prohibited from external cloud API transmission (Gemini) to prevent data leakage.
                    </p>
                    <div className="flex items-center gap-2 pt-1">
                      <button
                        onClick={async () => {
                          try {
                            await setMode('airgap');
                          } catch (e) {
                            console.error(e);
                          }
                        }}
                        className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all shadow-sm dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-zinc-200 dark:border dark:border-zinc-700"
                      >
                        <Shield className="w-3.5 h-3.5" />
                        Switch to AIRGAP Mode & Query Privately
                      </button>
                    </div>
                  </div>
                )}

                {/* Assistant Query Details & Metrics */}
                {msg.response && (
                  <div className="mt-4 pt-3 border-t border-slate-100 dark:border-zinc-800/80 space-y-3">
                    {/* Redaction Notice Banner */}
                    {msg.response.redaction && (msg.response.redaction.detected_entities?.length ?? 0) > 0 && (
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs text-slate-700 flex items-center justify-between dark:bg-zinc-900 dark:border-zinc-800 dark:text-zinc-300">
                        <div className="flex items-center space-x-2">
                          <Shield className="w-4 h-4 text-indigo-600 dark:text-zinc-400 shrink-0" />
                          <span>
                            HIPAA Guard redacted <strong>{msg.response.redaction.detected_entities?.length ?? 0}</strong> sensitive entities prior to inference.
                          </span>
                        </div>
                        <span className="font-mono text-[11px] text-slate-700 bg-slate-200/80 px-2 py-0.5 rounded border border-slate-300 dark:text-zinc-300 dark:bg-zinc-800 dark:border-zinc-700/60">
                          Risk: {msg.response.redaction.risk_score_heuristic ?? 0} (heuristic)
                        </span>
                      </div>
                    )}

                    {/* Grounding & Latency HUD */}
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono bg-slate-50 p-2.5 rounded-lg border border-slate-200 dark:bg-[#101012] dark:border-zinc-800/80">
                      <div className="flex items-center space-x-3">
                        <span className="text-slate-500 dark:text-zinc-500">Grounding:</span>
                        <span
                          className={`font-semibold ${
                            (msg.response.evaluation?.grounding_confidence_heuristic ?? 0) >= 0.7
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-amber-600 dark:text-amber-400'
                          }`}
                        >
                          {((msg.response.evaluation?.grounding_confidence_heuristic ?? 0) * 100).toFixed(1)}%
                        </span>
                        <span className="text-slate-300 dark:text-zinc-700">|</span>
                        <span className="text-slate-500 dark:text-zinc-500">Unsupported:</span>
                        <span className="text-slate-700 dark:text-zinc-300">
                          {((msg.response.evaluation?.unsupported_claim_rate_heuristic ?? 0) * 100).toFixed(1)}%
                        </span>
                      </div>

                      <div className="flex items-center space-x-3 text-slate-500 dark:text-zinc-400">
                        <span>Retr: {(msg.response.retrieval_latency_ms ?? 0).toFixed(1)}ms</span>
                        <span>Gen: {(msg.response.generation_latency_ms ?? 0).toFixed(1)}ms</span>
                        {msg.response.offline_fallback && (
                          <span className="text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 text-[10px] font-medium dark:text-zinc-300 dark:bg-zinc-800/80 dark:border-zinc-700">
                            OFFLINE FALLBACK
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Toggle Detailed Evidence & Claims Matrix */}
                    <button
                      onClick={() => toggleDetails(msg.id)}
                      className="text-xs text-slate-600 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-200 flex items-center gap-1 font-mono pt-1 transition-colors"
                    >
                      {expandedDetails[msg.id] ? (
                        <>
                          <ChevronUp className="w-3.5 h-3.5" />
                          Hide Evidence & Claim Matrix
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-3.5 h-3.5" />
                          View Evidence ({(msg.response.retrieved_chunks?.length ?? 0)} chunks) & Claim Matrix ({(msg.response.evaluation?.claim_matrix?.length ?? 0)} claims)
                        </>
                      )}
                    </button>

                    {expandedDetails[msg.id] && (
                      <div className="space-y-4 pt-2">
                        {/* Verifiable Claim Matrix */}
                        <div>
                          <h4 className="text-xs font-semibold text-slate-600 dark:text-zinc-400 uppercase tracking-wider mb-2 font-mono">
                            Claim Verification Matrix ({msg.response.evaluation?.claim_matrix?.length ?? 0})
                          </h4>
                          <div className="overflow-x-auto border border-slate-200 dark:border-zinc-800/80 rounded-lg">
                            <table className="w-full text-left text-xs font-mono">
                              <thead className="bg-slate-100 text-slate-600 border-b border-slate-200 dark:bg-zinc-900/90 dark:text-zinc-400 dark:border-zinc-800">
                                <tr>
                                  <th className="p-2 font-medium">Claim</th>
                                  <th className="p-2 font-medium">Status</th>
                                  <th className="p-2 font-medium">Verifying Document</th>
                                  <th className="p-2 font-medium">Confidence</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100 bg-white dark:divide-zinc-800/60 dark:bg-[#121215]">
                                {(msg.response.evaluation?.claim_matrix || []).map((c: ClaimVerification, cIdx: number) => (
                                  <tr key={cIdx} className="hover:bg-slate-50 dark:hover:bg-zinc-900/40">
                                    <td className="p-2 text-slate-800 dark:text-zinc-300 max-w-xs truncate" title={c.claim_text}>
                                      {c.claim_text}
                                    </td>
                                    <td className="p-2">
                                      <span
                                        className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                          c.status === 'VERIFIED'
                                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20'
                                            : c.status === 'INFERRED'
                                            ? 'bg-slate-100 text-slate-700 border border-slate-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700'
                                            : 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20'
                                        }`}
                                      >
                                        {c.status}
                                      </span>
                                    </td>
                                    <td className="p-2 text-slate-600 dark:text-zinc-400">
                                      {c.verifying_doc ? `${c.verifying_doc} (${c.verifying_lines || ''})` : '—'}
                                    </td>
                                    <td className="p-2 text-slate-800 dark:text-zinc-300 font-medium">
                                      {((c.confidence_heuristic ?? 0) * 100).toFixed(0)}%
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>

                        {/* Retrieved Citation Chunks */}
                        <div>
                          <h4 className="text-xs font-semibold text-slate-600 dark:text-zinc-400 uppercase tracking-wider mb-2 font-mono">
                            Retrieved Evidence Passages
                          </h4>
                          <div className="space-y-2">
                            {(msg.response.retrieved_chunks || []).map((chk: RetrievedChunk, chkIdx: number) => (
                              <div
                                key={chkIdx}
                                className="bg-slate-50 border border-slate-200 dark:bg-[#101012] dark:border-zinc-800/80 rounded-lg p-3 text-xs space-y-1.5 font-mono"
                              >
                                <div className="flex items-center justify-between text-slate-600 dark:text-zinc-400 border-b border-slate-200 dark:border-zinc-800/80 pb-1">
                                  <span className="font-semibold text-slate-800 dark:text-zinc-300">
                                    {chk.citation_label}
                                  </span>
                                  <div className="flex items-center space-x-2 text-[10px] text-slate-500 dark:text-zinc-500">
                                    <span>Sim: {(chk.similarity_score ?? 0).toFixed(3)}</span>
                                    <span>BM25: {(chk.bm25_score ?? 0).toFixed(2)}</span>
                                    <span className="text-indigo-600 dark:text-zinc-300 font-medium">
                                      RRF: {(chk.rrf_score ?? 0).toFixed(4)}
                                    </span>
                                  </div>
                                </div>
                                <p className="text-slate-700 dark:text-zinc-300 text-xs font-sans whitespace-pre-wrap leading-relaxed">
                                  {chk.text}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input Bar & Controls */}
      <div className="bg-white border border-slate-200 rounded-2xl p-3.5 shadow-sm space-y-3 dark:bg-[#151518] dark:border-zinc-800/90 dark:shadow-black/20">
        <form onSubmit={handleSend} className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question against your private corpus (e.g. clinical dosage, liability cap)..."
            disabled={loading}
            className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 font-sans transition-colors dark:bg-[#0f0f11] dark:border-zinc-800 dark:text-zinc-100 dark:placeholder-zinc-500 dark:focus:border-zinc-600"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white font-medium rounded-xl text-sm flex items-center gap-2 transition-all shadow-sm dark:bg-zinc-100 dark:hover:bg-white dark:disabled:bg-zinc-800 dark:disabled:text-zinc-600 dark:text-zinc-900"
          >
            {loading ? (
              <Zap className="w-4 h-4 animate-spin text-white dark:text-zinc-700" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>Send</span>
          </button>
        </form>

        {/* Configuration Row */}
        <div className="flex flex-wrap items-center justify-between text-xs text-slate-500 font-mono pt-1.5 border-t border-slate-100 dark:border-zinc-800/60 dark:text-zinc-400">
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={redactPii}
                onChange={(e) => setRedactPii(e.target.checked)}
                className="rounded border-slate-300 bg-white text-indigo-600 focus:ring-0 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
              />
              <span className="text-slate-700 dark:text-zinc-300">HIPAA Safe Harbor Redaction</span>
            </label>

            <div className="flex items-center space-x-2">
              <span>Top-K:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="bg-slate-50 border border-slate-200 rounded px-2 py-0.5 text-slate-700 focus:outline-none focus:border-indigo-500 dark:bg-[#0f0f11] dark:border-zinc-800 dark:text-zinc-200 dark:focus:border-zinc-600"
              >
                <option value={2}>2</option>
                <option value={4}>4 (default)</option>
                <option value={6}>6</option>
                <option value={8}>8</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-2 text-[11px] text-slate-400 dark:text-zinc-500">
            <span>Air-Gapped Embedding: 384-D FAISS</span>
            <span>•</span>
            <span>Deterministic Grounding Verification</span>
          </div>
        </div>
      </div>
    </div>
  );
};
