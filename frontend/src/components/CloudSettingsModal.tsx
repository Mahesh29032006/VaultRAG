import React, { useState, useEffect } from 'react';
import {
  X,
  Key,
  Cloud,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Save,
  Radio,
  Server
} from 'lucide-react';
import { api } from '../api';
import { useAppStore } from '../store';
import { ConfigSettings } from '../types';

interface CloudSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CloudSettingsModal: React.FC<CloudSettingsModalProps> = ({ isOpen, onClose }) => {
  const { engineMode, setMode, fetchHealth } = useAppStore();

  const [config, setConfig] = useState<ConfigSettings | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [selectedModel, setSelectedModel] = useState('gemini-3.5-flash');
  const [targetMode, setTargetMode] = useState<'airgap' | 'cloud'>(engineMode);

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ valid: boolean; error?: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadConfig();
      setTargetMode(engineMode);
      setTestResult(null);
      setErrorMessage(null);
      setSaveSuccess(false);
    }
  }, [isOpen, engineMode]);

  const loadConfig = async () => {
    try {
      const data = await api.getConfigSettings();
      setConfig(data);
      if (data.gemini_model) {
        setSelectedModel(data.gemini_model);
      }
    } catch (err) {
      console.error('Failed to load settings config', err);
    }
  };

  if (!isOpen) return null;

  const handleTestKey = async () => {
    setTesting(true);
    setTestResult(null);
    setErrorMessage(null);
    try {
      const res = await api.testGeminiKey(apiKeyInput.trim() || undefined);
      setTestResult(res);
      if (!res.valid && res.error) {
        setErrorMessage(res.error);
      }
    } catch (err) {
      setTestResult({ valid: false, error: err instanceof Error ? err.message : String(err) });
      setErrorMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setTesting(false);
    }
  };

  const handleSaveAndApply = async () => {
    setSaving(true);
    setErrorMessage(null);
    setSaveSuccess(false);
    try {
      // 1. Update config if changed
      const updatePayload: {
        gemini_api_key?: string;
        gemini_model?: string;
      } = {
        gemini_model: selectedModel,
      };

      if (apiKeyInput.trim()) {
        updatePayload.gemini_api_key = apiKeyInput.trim();
      }

      await api.updateConfigSettings(updatePayload);

      // 2. Switch mode if requested
      if (targetMode !== engineMode) {
        await setMode(targetMode, apiKeyInput.trim() || undefined);
      } else {
        await fetchHealth();
      }

      setSaveSuccess(true);
      setApiKeyInput('');
      await loadConfig();
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-xl w-full p-6 shadow-2xl relative space-y-5 dark:bg-[#151518] dark:border-zinc-800">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3.5 border-b border-slate-200 dark:border-zinc-800/80">
          <div className="flex items-center space-x-2.5">
            <Key className="w-4 h-4 text-indigo-600 dark:text-zinc-400" />
            <h3 className="font-semibold text-base text-slate-800 dark:text-zinc-100">Engine Mode & API Settings</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600 dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Status Alerts */}
        {errorMessage && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2 dark:bg-red-950/40 dark:border-red-800/50 dark:text-red-200">
            <AlertCircle className="w-4 h-4 text-rose-600 dark:text-red-400 shrink-0 mt-0.5" />
            <div>{errorMessage}</div>
          </div>
        )}

        {saveSuccess && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2 dark:bg-emerald-950/40 dark:border-emerald-800/50 dark:text-emerald-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>Settings permanently saved and engine mode applied successfully!</span>
          </div>
        )}

        {/* Engine Mode Selection */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-slate-600 dark:text-zinc-400 uppercase tracking-wider font-mono flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
            Engine Execution Mode
          </label>
          <div className="grid grid-cols-2 gap-3">
            {/* Air-Gap Button */}
            <button
              type="button"
              onClick={() => setTargetMode('airgap')}
              className={`p-3.5 rounded-xl border text-left transition-all flex flex-col justify-between ${
                targetMode === 'airgap'
                  ? 'bg-emerald-50/80 border-emerald-500 text-slate-900 shadow-sm dark:bg-zinc-800/90 dark:border-zinc-600 dark:text-zinc-100'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300 dark:bg-[#0f0f11] dark:border-zinc-800/80 dark:text-zinc-400 dark:hover:border-zinc-700'
              }`}
            >
              <div className="flex items-center justify-between w-full mb-1">
                <span className="text-xs font-semibold font-mono text-slate-900 dark:text-zinc-100">AIR-GAP (OFFLINE)</span>
                {targetMode === 'airgap' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-zinc-200" />}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-zinc-500 leading-tight">
                Strict zero-egress loopback. Offline embeddings & synthesis. No internet required.
              </p>
            </button>

            {/* Cloud Button */}
            <button
              type="button"
              onClick={() => setTargetMode('cloud')}
              className={`p-3.5 rounded-xl border text-left transition-all flex flex-col justify-between ${
                targetMode === 'cloud'
                  ? 'bg-indigo-50/80 border-indigo-500 text-slate-900 shadow-sm dark:bg-zinc-800/90 dark:border-zinc-600 dark:text-zinc-100'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300 dark:bg-[#0f0f11] dark:border-zinc-800/80 dark:text-zinc-400 dark:hover:border-zinc-700'
              }`}
            >
              <div className="flex items-center justify-between w-full mb-1">
                <span className="text-xs font-semibold font-mono text-slate-900 dark:text-zinc-100">HYBRID CLOUD</span>
                {targetMode === 'cloud' && <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-200" />}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-zinc-500 leading-tight">
                HIPAA Safe-Harbor PII redaction before egress to Google Gemini. Local re-identification.
              </p>
            </button>
          </div>
        </div>

        {/* Gemini API Key Configuration */}
        <div className="space-y-3 bg-slate-50 border border-slate-200 p-4 rounded-xl dark:bg-[#0f0f11] dark:border-zinc-800/80">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-700 dark:text-zinc-300 font-mono flex items-center gap-1.5">
              <Cloud className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
              Google Gemini API Key
            </label>
            <span className="text-[11px] font-mono">
              {config?.gemini_api_key_configured ? (
                <span className="text-slate-700 dark:text-zinc-300 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400/90" /> Configured ({config.gemini_api_key_masked})
                </span>
              ) : (
                <span className="text-slate-400 dark:text-zinc-500">Not Configured</span>
              )}
            </span>
          </div>

          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder={config?.gemini_api_key_configured ? 'Enter new key to update...' : 'Paste your AIzaSy... API key'}
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono text-slate-900 placeholder-slate-400 pr-20 focus:outline-none focus:border-indigo-500 dark:bg-[#151518] dark:border-zinc-800 dark:text-zinc-100 dark:placeholder-zinc-500 dark:focus:border-zinc-600"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="p-1 text-slate-400 hover:text-slate-600 dark:text-zinc-400 dark:hover:text-white"
                title={showKey ? 'Hide Key' : 'Show Key'}
              >
                {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={handleTestKey}
              disabled={testing || (!apiKeyInput.trim() && !config?.gemini_api_key_configured)}
              className="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 disabled:opacity-50 text-slate-700 rounded-lg text-xs font-mono transition-colors flex items-center gap-1.5 border border-slate-300 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-zinc-300 dark:border-zinc-700/60"
            >
              {testing ? 'Testing Connection...' : 'Test Connection'}
            </button>

            {testResult && (
              <span className={`text-xs font-mono font-medium flex items-center gap-1 ${
                testResult.valid ? 'text-emerald-600 dark:text-emerald-400/90' : 'text-rose-600 dark:text-red-400'
              }`}>
                {testResult.valid ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" /> Verified & Active
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-3.5 h-3.5" /> Failed Verification
                  </>
                )}
              </span>
            )}
          </div>

          {/* Model Selection */}
          <div className="pt-2 border-t border-slate-200 dark:border-zinc-800/80 space-y-1.5">
            <label className="text-[11px] text-slate-500 dark:text-zinc-400 font-mono flex items-center gap-1">
              <Server className="w-3 h-3 text-indigo-600 dark:text-zinc-400" />
              Cloud Synthesis Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-800 focus:outline-none focus:border-indigo-500 dark:bg-[#151518] dark:border-zinc-800 dark:text-zinc-200 dark:focus:border-zinc-600"
            >
              <option value="gemini-3.5-flash">gemini-3.5-flash (Fastest & Verified, Recommended)</option>
              <option value="gemini-3.5-flash-lite">gemini-3.5-flash-lite (Ultra Lightweight)</option>
              <option value="gemini-3.8-flash">gemini-3.8-flash (Latest 3.8 Flash)</option>
              <option value="gemini-2.5-pro">gemini-2.5-pro (Deep Reasoning)</option>
            </select>
          </div>
        </div>

        {/* Security & Persistence Notice */}
        <div className="bg-slate-100/80 border border-slate-200 rounded-xl p-3 text-[11px] text-slate-600 font-mono space-y-1 dark:bg-[#0f0f11]/60 dark:border-zinc-800/60 dark:text-zinc-400">
          <div className="flex items-center gap-1.5 text-slate-800 dark:text-zinc-300 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-zinc-400" />
            Permanent Secret Persistence
          </div>
          <p>
            Keys are saved to <code className="text-slate-800 dark:text-zinc-300">.env</code> and <code className="text-slate-800 dark:text-zinc-300">data/config.json</code> with restrictive <code className="text-slate-800 dark:text-zinc-300">0600</code> filesystem permissions. Keys are never transmitted in terminal logs.
          </p>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition-colors border border-slate-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-zinc-300 dark:border-zinc-700/60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSaveAndApply}
            disabled={saving}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-medium transition-colors flex items-center gap-1.5 shadow-sm dark:bg-zinc-100 dark:hover:bg-white dark:text-zinc-900"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? 'Saving...' : 'Save & Apply'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
