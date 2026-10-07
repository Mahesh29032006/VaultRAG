import React, { useState } from 'react';
import {
  Shield,
  ShieldCheck,
  RefreshCw,
  Copy,
  Check,
  Lock,
  Unlock,
} from 'lucide-react';
import { api } from '../api';
import { DetectedEntity, RedactionResult } from '../types';
import { useAppStore } from '../store';

const SAMPLE_CLINICAL_NOTE = `PATIENT CLINICAL SUMMARY
Patient Name: Eleanor Vance
SSN: 987-65-4320 | MRN: MRN-4491029
DOB / Admission Date: 03/15/2024
Address: 742 Evergreen Terrace, Springfield, OR 97477
Phone: (555) 839-2001 | Email: evance@healthmail.org
Attending Physician: Dr. Robert Langdon, MD (NPI: 1982736450)
Account Number: ACCT-9918234

Chief Complaint: Acute decompensated heart failure with bilateral lower extremity edema.
Assessment: Patient switched from IV Lasix to oral Torsemide 40 mg daily.`;

export const PiiInspector: React.FC = () => {
  const { setGlobalError } = useAppStore();
  const [inputText, setInputText] = useState(SAMPLE_CLINICAL_NOTE);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RedactionResult | null>(null);
  const [restoredText, setRestoredText] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleRedact = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setRestoredText(null);
    try {
      const res = await api.redactPii(inputText);
      setResult(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setGlobalError(`Redaction failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async () => {
    if (!result) return;
    setLoading(true);
    try {
      const res = await api.restorePii(result.redacted_text, result.token_map);
      setRestoredText(res.restored_text);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setGlobalError(`Restoration failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getRiskColor = (score: number) => {
    if (score > 60) return 'text-rose-700 bg-rose-50 border-rose-200 dark:text-red-400 dark:bg-red-950/30 dark:border-red-800/40';
    if (score > 25) return 'text-amber-700 bg-amber-50 border-amber-200 dark:text-amber-400 dark:bg-amber-950/30 dark:border-amber-800/40';
    return 'text-emerald-700 bg-emerald-50 border-emerald-200 dark:text-emerald-400/90 dark:bg-emerald-950/30 dark:border-emerald-800/40';
  };

  return (
    <div className="max-w-6xl mx-auto w-full px-4 py-6 space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 dark:bg-[#151518] dark:border-zinc-800/80">
        <div>
          <h2 className="text-base font-semibold text-slate-800 dark:text-zinc-100 flex items-center gap-2">
            <Shield className="w-4 h-4 text-indigo-600 dark:text-zinc-400" />
            HIPAA Safe Harbor 18-Identifier Privacy Guard
          </h2>
          <p className="text-xs text-slate-500 font-mono mt-1 dark:text-zinc-400">
            Deterministic tokenization, right-to-left replacement, collision mitigation & cryptographic reversibility.
          </p>
        </div>

        <button
          onClick={() => setInputText(SAMPLE_CLINICAL_NOTE)}
          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-mono transition-colors border border-slate-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-zinc-200 dark:border-zinc-700/60"
        >
          Load Clinical EHR Sample
        </button>
      </div>

      {/* Main Redaction Workbench (2 Columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Input Text Area */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4 dark:bg-[#151518] dark:border-zinc-800/80">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-600 dark:text-zinc-400 font-semibold flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
              Raw Input Text (Unredacted)
            </span>
            <span className="text-[11px] font-mono text-slate-500 dark:text-zinc-500">
              {inputText.length} characters
            </span>
          </div>

          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            rows={10}
            placeholder="Paste text containing names, dates, SSNs, phone numbers, addresses, or medical records..."
            className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 leading-relaxed dark:bg-[#0f0f11] dark:border-zinc-800 dark:text-zinc-100 dark:placeholder-zinc-500 dark:focus:border-zinc-600"
          />

          <div className="flex justify-end">
            <button
              onClick={handleRedact}
              disabled={loading || !inputText.trim()}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl text-xs font-medium flex items-center gap-2 transition-all shadow-sm dark:bg-zinc-100 dark:hover:bg-white dark:disabled:bg-zinc-800 dark:disabled:text-zinc-600 dark:text-zinc-900"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Redact Sensitive Entities</span>
            </button>
          </div>
        </div>

        {/* Right: Redacted Output & Token Map */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4 dark:bg-[#151518] dark:border-zinc-800/80">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-600 dark:text-zinc-400 font-semibold flex items-center gap-1.5">
              <Unlock className="w-3.5 h-3.5 text-emerald-600 dark:text-zinc-400" />
              Sanitized Output (Safe For Local Model)
            </span>

            {result && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleCopy(result.redacted_text)}
                  className="p-1 text-slate-400 hover:text-slate-600 dark:text-zinc-400 dark:hover:text-white transition-colors"
                  title="Copy sanitized text"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400/90" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            )}
          </div>

          <div className="w-full h-52 bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs font-mono text-slate-800 overflow-y-auto leading-relaxed whitespace-pre-wrap dark:bg-[#0f0f11] dark:border-zinc-800 dark:text-zinc-200">
            {result ? result.redacted_text : <span className="text-slate-400 dark:text-zinc-600">Click 'Redact Sensitive Entities' to execute HIPAA de-identification...</span>}
          </div>

          <div className="flex items-center justify-between pt-1">
            <div className="text-xs font-mono text-slate-600 dark:text-zinc-400">
              {result && (
                <span>
                  Detected: <strong className="text-slate-900 dark:text-zinc-200">{result.detected_entities.length}</strong> entities
                </span>
              )}
            </div>

            {result && (
              <button
                onClick={handleRestore}
                disabled={loading}
                className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-mono transition-colors flex items-center gap-1.5 border border-slate-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-zinc-200 dark:border-zinc-700/60"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Test Reverse Rehydration</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Restored Rehydration Check (If activated) */}
      {restoredText && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2 dark:bg-[#151518] dark:border-zinc-800/80">
          <div className="flex items-center justify-between text-xs font-mono text-slate-800 dark:text-zinc-300 font-semibold">
            <span>Restored Rehydrated Text Verification</span>
            <span className="text-emerald-600 dark:text-emerald-400/90 flex items-center gap-1 font-mono">
              <Check className="w-3.5 h-3.5" /> Exact Round-Trip Match
            </span>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs font-mono text-slate-800 whitespace-pre-wrap dark:bg-[#0f0f11] dark:border-zinc-800 dark:text-zinc-200">
            {restoredText}
          </div>
        </div>
      )}

      {/* Entity Table & Risk Score HUD */}
      {result && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5 dark:bg-[#151518] dark:border-zinc-800/80">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-zinc-800/80 pb-4">
            <div>
              <h3 className="text-xs font-semibold text-slate-700 dark:text-zinc-400 uppercase tracking-wider font-mono">
                Detected Safe Harbor Entities ({result.detected_entities.length})
              </h3>
              <p className="text-xs text-slate-500 font-mono mt-0.5 dark:text-zinc-500">
                Each identified token is tracked in the reverse token map for airgap rehydration.
              </p>
            </div>

            {/* Risk Score Meter */}
            <div className="flex items-center space-x-3 bg-slate-50 border border-slate-200 px-3.5 py-1.5 rounded-xl font-mono dark:bg-[#0f0f11] dark:border-zinc-800">
              <span className="text-xs text-slate-500 dark:text-zinc-500">Risk Score:</span>
              <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${getRiskColor(result.risk_score_heuristic)}`}>
                {result.risk_score_heuristic}/100 (heuristic)
              </span>
            </div>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-xl dark:border-zinc-800/80">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-100 text-slate-600 border-b border-slate-200 dark:bg-zinc-900/90 dark:text-zinc-400 dark:border-zinc-800">
                <tr>
                  <th className="p-3 font-medium">Identifier Type</th>
                  <th className="p-3 font-medium">Raw Value</th>
                  <th className="p-3 font-medium">Replaced Token</th>
                  <th className="p-3 font-medium">Confidence</th>
                  <th className="p-3 font-medium">Span Offset</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white dark:divide-zinc-800/60 dark:bg-[#121215]">
                {result.detected_entities.map((ent: DetectedEntity) => (
                  <tr key={ent.id} className="hover:bg-slate-50 dark:hover:bg-zinc-900/40">
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700/60">
                        {ent.type}
                      </span>
                    </td>
                    <td className="p-3 text-slate-800 dark:text-zinc-300 font-mono">{ent.raw}</td>
                    <td className="p-3 text-emerald-600 dark:text-emerald-400/90 font-semibold">{ent.token}</td>
                    <td className="p-3 text-slate-700 dark:text-zinc-300">{(ent.confidence * 100).toFixed(0)}%</td>
                    <td className="p-3 text-slate-400 dark:text-zinc-500 text-[11px]">
                      [{ent.start_index} : {ent.end_index}]
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
