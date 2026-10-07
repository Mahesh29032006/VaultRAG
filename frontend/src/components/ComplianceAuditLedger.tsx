import React, { useState, useEffect } from 'react';
import {
  FileCheck,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Layers,
} from 'lucide-react';
import { useAppStore } from '../store';
import { api } from '../api';
import { AuditRecord, AuditEventType } from '../types';

export const ComplianceAuditLedger: React.FC = () => {
  const {
    auditRecords,
    auditValid,
    fetchAudit,
    setGlobalError,
  } = useAppStore();

  const [verifying, setVerifying] = useState(false);
  const [filterType, setFilterType] = useState<string>('ALL');
  const [verificationResult, setVerificationResult] = useState<{
    is_valid: boolean;
    total_records: number;
    checked_at: string;
  } | null>(null);

  useEffect(() => {
    fetchAudit();
  }, [fetchAudit]);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const res = await api.verifyAuditLedger();
      setVerificationResult(res);
      await fetchAudit();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setGlobalError(`Audit verification failed: ${msg}`);
    } finally {
      setVerifying(false);
    }
  };

  const getEventBadgeColor = (eventType: AuditEventType) => {
    switch (eventType) {
      case 'GENESIS':
        return 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-500/10 dark:text-purple-300 dark:border-purple-500/20';
      case 'DOCUMENT_INGEST':
        return 'bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-500/10 dark:text-sky-300 dark:border-sky-500/20';
      case 'PII_REDACT':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/20';
      case 'LOCAL_QUERY':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-zinc-800 dark:text-zinc-200 dark:border-zinc-700/60';
      case 'AIR_GAP_VERIFY':
        return 'bg-teal-100 text-teal-800 border-teal-200 dark:bg-teal-500/10 dark:text-teal-300 dark:border-teal-500/20';
      case 'MODE_SWITCH':
        return 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/20';
      case 'ERROR':
        return 'bg-rose-100 text-rose-800 border-rose-200 dark:bg-red-500/10 dark:text-red-300 dark:border-red-500/20';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700';
    }
  };

  const filteredRecords = auditRecords.filter((rec) => {
    if (filterType === 'ALL') return true;
    return rec.event_type === filterType;
  });

  return (
    <div className="max-w-6xl mx-auto w-full px-4 py-6 space-y-6">
      {/* Top Banner & Status */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 dark:bg-[#151518] dark:border-zinc-800/80">
        <div>
          <h2 className="text-base font-semibold text-slate-800 dark:text-zinc-100 flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-indigo-600 dark:text-zinc-400" />
            Cryptographic SHA-256 Audit Ledger
          </h2>
          <p className="text-xs text-slate-500 font-mono mt-1 dark:text-zinc-400">
            Append-only tamper-evident hash chain logging all ingestions, redactions, and queries without storing raw PII.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchAudit}
            className="p-2 text-slate-500 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors border border-slate-200 dark:text-zinc-400 dark:hover:text-white dark:bg-zinc-800 dark:border-zinc-700/60"
            title="Refresh Ledger"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={handleVerify}
            disabled={verifying}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl text-xs font-medium flex items-center gap-2 transition-all shadow-sm font-mono dark:bg-zinc-100 dark:hover:bg-white dark:disabled:bg-zinc-800 dark:disabled:text-zinc-600 dark:text-zinc-900"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>{verifying ? 'Verifying Chain...' : 'Verify Ledger Integrity'}</span>
          </button>
        </div>
      </div>

      {/* Ledger Integrity Indicator Card */}
      <div
        className={`rounded-2xl p-4 border flex items-center justify-between text-xs font-mono ${
          auditValid
            ? 'bg-emerald-50/80 border-emerald-300 text-emerald-900 dark:bg-[#0f0f11] dark:border-zinc-800/80 dark:text-zinc-300'
            : 'bg-rose-50 border-rose-300 text-rose-900 dark:bg-red-950/30 dark:border-red-800/40 dark:text-red-300'
        }`}
      >
        <div className="flex items-center space-x-3">
          {auditValid ? (
            <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400/90 shrink-0" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-rose-600 dark:text-red-400 shrink-0" />
          )}
          <div>
            <span className="font-semibold text-xs block text-slate-900 dark:text-zinc-100">
              {auditValid
                ? 'INTEGRITY VERIFIED: ALL SHA-256 HASHES VALID'
                : 'SECURITY ALERT: TAMPER DETECTED IN LEDGER'}
            </span>
            <span className="text-[11px] text-slate-600 dark:text-zinc-500">
              {verificationResult
                ? `Last full verification at ${verificationResult.checked_at} across ${verificationResult.total_records} chained blocks.`
                : `Active chain length: ${auditRecords.length} blocks.`}
            </span>
          </div>
        </div>

        <div className="hidden sm:block text-right">
          <span className="block text-[10px] text-slate-500 dark:text-zinc-500">CRYPTOGRAPHIC ALGORITHM</span>
          <span className="font-semibold text-slate-700 dark:text-zinc-300">SHA-256 Merkle Chain</span>
        </div>
      </div>

      {/* Ledger Records Table */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4 dark:bg-[#151518] dark:border-zinc-800/80">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="text-xs font-semibold text-slate-600 dark:text-zinc-400 uppercase tracking-wider font-mono flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
            Chain Blocks ({filteredRecords.length})
          </h3>

          <div className="flex items-center space-x-2 text-xs font-mono">
            <span className="text-slate-600 dark:text-zinc-400">Event Filter:</span>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 focus:outline-none focus:border-indigo-500 dark:bg-[#0f0f11] dark:border-zinc-800 dark:text-zinc-200 dark:focus:border-zinc-600"
            >
              <option value="ALL">ALL EVENTS</option>
              <option value="GENESIS">GENESIS</option>
              <option value="DOCUMENT_INGEST">DOCUMENT_INGEST</option>
              <option value="PII_REDACT">PII_REDACT</option>
              <option value="LOCAL_QUERY">LOCAL_QUERY</option>
              <option value="AIR_GAP_VERIFY">AIR_GAP_VERIFY</option>
              <option value="MODE_SWITCH">MODE_SWITCH</option>
            </select>
          </div>
        </div>

        {filteredRecords.length === 0 ? (
          <div className="text-center py-10 text-slate-400 dark:text-zinc-500 text-xs font-mono">
            No audit records matching criteria.
          </div>
        ) : (
          <div className="overflow-x-auto border border-slate-200 rounded-xl dark:border-zinc-800/80">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-100 text-slate-600 border-b border-slate-200 dark:bg-zinc-900/90 dark:text-zinc-400 dark:border-zinc-800">
                <tr>
                  <th className="p-3 font-medium">Index</th>
                  <th className="p-3 font-medium">Timestamp</th>
                  <th className="p-3 font-medium">Event Type</th>
                  <th className="p-3 font-medium">Payload Summary</th>
                  <th className="p-3 font-medium">Current Block Hash</th>
                  <th className="p-3 font-medium">Previous Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white dark:divide-zinc-800/60 dark:bg-[#121215]">
                {filteredRecords.map((rec: AuditRecord) => (
                  <tr key={rec.index} className="hover:bg-slate-50 dark:hover:bg-zinc-900/40">
                    <td className="p-3 text-slate-500 dark:text-zinc-400 font-medium">#{rec.index}</td>
                    <td className="p-3 text-slate-400 dark:text-zinc-500 text-[11px]">
                      {rec.timestamp.replace('T', ' ').substring(0, 19)}
                    </td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-semibold ${getEventBadgeColor(
                          rec.event_type
                        )}`}
                      >
                        {rec.event_type}
                      </span>
                    </td>
                    <td className="p-3 text-slate-800 dark:text-zinc-200 max-w-sm truncate" title={rec.payload_summary}>
                      {rec.payload_summary}
                    </td>
                    <td className="p-3 text-slate-500 dark:text-zinc-400 text-[11px]" title={rec.current_hash}>
                      {rec.current_hash.substring(0, 12)}...
                    </td>
                    <td className="p-3 text-slate-400 dark:text-zinc-500 text-[11px]" title={rec.previous_hash}>
                      {rec.previous_hash.substring(0, 12)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
