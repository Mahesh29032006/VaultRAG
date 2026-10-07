import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Sliders,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from 'lucide-react';
import { api } from '../api';
import { MemoryCalculation } from '../types';

interface ModelProfile {
  id: string;
  name: string;
  params: string;
}

const DEFAULT_MODELS: ModelProfile[] = [
  { id: 'llama3:8b', name: 'Meta Llama 3', params: '8.0B' },
  { id: 'phi3:mini', name: 'Microsoft Phi-3 Mini', params: '3.8B' },
  { id: 'mistral:7b', name: 'Mistral Instruct', params: '7.2B' },
  { id: 'qwen2.5:7b', name: 'Alibaba Qwen 2.5', params: '7.6B' },
];

export const QuantizationMatrix: React.FC = () => {
  const [models, setModels] = useState<ModelProfile[]>(DEFAULT_MODELS);
  const [selectedModel, setSelectedModel] = useState<string>('llama3:8b');
  const [quantType, setQuantType] = useState<string>('Q4_K_M');
  const [contextLength, setContextLength] = useState<number>(4096);
  const [batchSize, setBatchSize] = useState<number>(1);
  const [calculation, setCalculation] = useState<MemoryCalculation | null>(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await api.getModels();
        const rawList = res && res.models;
        if (Array.isArray(rawList) && rawList.length > 0) {
          const mapped: ModelProfile[] = rawList.map((item: any) => {
            const id = typeof item === 'string' ? item : item.id;
            const matched = DEFAULT_MODELS.find((d) => d.id === id);
            if (matched) return matched;
            return {
              id: id || 'llama3:8b',
              name: id || 'Local Model',
              params: typeof item === 'object' && item.base_params_billions ? `${item.base_params_billions}B` : '—',
            };
          });
          setModels(mapped);
          setSelectedModel(mapped[0].id);
        } else {
          setModels(DEFAULT_MODELS);
        }
      } catch {
        setModels(DEFAULT_MODELS);
      }
    };
    fetchModels();
  }, []);

  useEffect(() => {
    const updateEstimate = async () => {
      if (!selectedModel) return;
      try {
        const res = await api.getMemoryEstimate({
          model_id: selectedModel,
          quant_type: quantType,
          context_length: contextLength,
          batch_size: batchSize,
        });
        setCalculation(res);
      } catch {
        // fallback calculation
      }
    };
    updateEstimate();
  }, [selectedModel, quantType, contextLength, batchSize]);

  return (
    <div className="max-w-6xl mx-auto w-full px-4 py-6 space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 dark:bg-[#151518] dark:border-zinc-800/80">
        <div>
          <h2 className="text-base font-semibold text-slate-800 dark:text-zinc-100 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-600 dark:text-zinc-400" />
            Quantization & Hardware Memory Telemetry
          </h2>
          <p className="text-xs text-slate-500 font-mono mt-1 dark:text-zinc-400">
            Analytical parameter, KV cache, and activation footprint modeling in GiB (1024³ bytes).
          </p>
        </div>

        <div className="bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-xl text-xs font-mono text-slate-600 dark:bg-[#0f0f11] dark:border-zinc-800/80 dark:text-zinc-300">
          Formula: Weights + KV Cache + Activations
        </div>
      </div>

      {/* Grid: Controls (Left) & Live Memory Cards (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Sliders and Controls (5 cols) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5 dark:bg-[#151518] dark:border-zinc-800/80">
          <h3 className="text-xs font-semibold text-slate-600 dark:text-zinc-400 uppercase tracking-wider font-mono flex items-center gap-2">
            <Sliders className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
            Model Configuration
          </h3>

          {/* Model Selector */}
          <div className="space-y-2">
            <label className="text-xs font-mono text-slate-600 dark:text-zinc-400">Target Model Family:</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs font-mono text-slate-800 focus:outline-none focus:border-indigo-500 dark:bg-[#0f0f11] dark:border-zinc-800 dark:text-zinc-200 dark:focus:border-zinc-600"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.params} Params)
                </option>
              ))}
            </select>
          </div>

          {/* Quantization Type */}
          <div className="space-y-2">
            <label className="text-xs font-mono text-slate-600 dark:text-zinc-400">Quantization Precision:</label>
            <div className="grid grid-cols-2 gap-2">
              {['FP16', 'Q8_0', 'Q4_K_M', 'Q2_K'].map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setQuantType(q)}
                  className={`p-2 rounded-lg text-xs font-mono border transition-all ${
                    quantType === q
                      ? 'bg-indigo-50 border-indigo-300 text-indigo-900 font-semibold shadow-sm dark:bg-zinc-800/90 dark:border-zinc-600 dark:text-zinc-100'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300 dark:bg-[#0f0f11] dark:border-zinc-800/80 dark:text-zinc-400 dark:hover:border-zinc-700'
                  }`}
                >
                  {q}
                  <span className="block text-[10px] text-slate-500 dark:text-zinc-500">
                    {q === 'Q4_K_M' ? '4.5 bpw (Recommended)' : q === 'FP16' ? '16 bpw (Unquantized)' : q === 'Q8_0' ? '8.5 bpw' : '2.5 bpw (High Loss)'}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Context Length Slider */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-slate-600 dark:text-zinc-400">Context Window:</span>
              <span className="text-slate-900 dark:text-zinc-200 font-semibold">{contextLength.toLocaleString()} Tokens</span>
            </div>
            <input
              type="range"
              min={1024}
              max={32768}
              step={1024}
              value={contextLength}
              onChange={(e) => setContextLength(Number(e.target.value))}
              className="w-full accent-indigo-600 dark:accent-zinc-300 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-500 dark:text-zinc-500">
              <span>1K (Low Latency)</span>
              <span>8K (Standard)</span>
              <span>32K (Large Doc)</span>
            </div>
          </div>

          {/* Batch Size Slider */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-slate-600 dark:text-zinc-400">Concurrent Batch Size:</span>
              <span className="text-slate-900 dark:text-zinc-200 font-semibold">N = {batchSize}</span>
            </div>
            <input
              type="range"
              min={1}
              max={8}
              step={1}
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
              className="w-full accent-indigo-600 dark:accent-zinc-300 cursor-pointer"
            />
          </div>
        </div>

        {/* Live Calculation Cards & Recommendations (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Main Total Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6 dark:bg-[#151518] dark:border-zinc-800/80">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-zinc-800/80 pb-4">
              <div>
                <span className="text-xs font-mono text-slate-500 dark:text-zinc-500 uppercase tracking-wider block">
                  Total System VRAM / RAM Required
                </span>
                <div className="flex items-baseline space-x-2 mt-1">
                  <span className="text-4xl font-extrabold text-slate-900 dark:text-zinc-100 font-mono tracking-tight">
                    {calculation ? calculation.total_memory_gib_estimate.toFixed(2) : '—'}
                  </span>
                  <span className="text-xl text-indigo-600 dark:text-zinc-400 font-bold font-mono">GiB</span>
                  <span className="text-xs text-slate-400 dark:text-zinc-500 font-mono">(estimated)</span>
                </div>
              </div>

              <div className="text-right">
                <span className="text-xs font-mono text-slate-500 dark:text-zinc-500 block">Recommended Platform</span>
                <span className="text-xs font-semibold text-slate-800 dark:text-zinc-200 font-mono block mt-1">
                  {calculation ? calculation.recommended_hardware : 'Analyzing...'}
                </span>
              </div>
            </div>

            {/* Breakdown Sub-cards in GiB */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs font-mono space-y-1 dark:bg-[#0f0f11] dark:border-zinc-800/80">
                <span className="text-slate-500 dark:text-zinc-500 block text-[10px]">WEIGHT MEMORY</span>
                <div className="text-base font-semibold text-slate-800 dark:text-zinc-200">
                  {calculation ? calculation.weight_memory_gib.toFixed(2) : '—'} GiB
                </div>
                <span className="text-[10px] text-slate-400 dark:text-zinc-500 block">(estimated)</span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs font-mono space-y-1 dark:bg-[#0f0f11] dark:border-zinc-800/80">
                <span className="text-slate-500 dark:text-zinc-500 block text-[10px]">KV CACHE MEMORY</span>
                <div className="text-base font-semibold text-slate-800 dark:text-zinc-200">
                  {calculation ? calculation.kv_cache_memory_gib.toFixed(2) : '—'} GiB
                </div>
                <span className="text-[10px] text-slate-400 dark:text-zinc-500 block">2 × L × H × D × FP16</span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs font-mono space-y-1 dark:bg-[#0f0f11] dark:border-zinc-800/80">
                <span className="text-slate-500 dark:text-zinc-500 block text-[10px]">ACTIVATION MEMORY</span>
                <div className="text-base font-semibold text-slate-800 dark:text-zinc-200">
                  {calculation ? calculation.activation_memory_gib_estimate.toFixed(2) : '—'} GiB
                </div>
                <span className="text-[10px] text-slate-400 dark:text-zinc-500 block">(heuristic estimate)</span>
              </div>
            </div>

            {/* Hardware Feasibility Badges */}
            <div className="pt-2 border-t border-slate-200 dark:border-zinc-800/80 space-y-3">
              <h4 className="text-xs font-mono uppercase text-slate-600 dark:text-zinc-400 font-semibold">
                Air-Gapped Hardware Compatibility Matrix
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                <div
                  className={`p-3 rounded-xl border flex items-center justify-between ${
                    calculation?.fits_on_8gib
                      ? 'bg-emerald-50/70 border-emerald-300 text-emerald-900 font-medium dark:bg-[#0f0f11] dark:border-zinc-700/80 dark:text-zinc-200'
                      : 'bg-slate-50 border-slate-200 text-slate-400 dark:bg-[#0f0f11] dark:border-zinc-800/60 dark:text-zinc-500'
                  }`}
                >
                  <span>Consumer Laptop (8 GiB RAM)</span>
                  {calculation?.fits_on_8gib ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400/90" />
                  ) : (
                    <XCircle className="w-4 h-4 text-slate-300 dark:text-zinc-600" />
                  )}
                </div>

                <div
                  className={`p-3 rounded-xl border flex items-center justify-between ${
                    calculation?.fits_on_16gib
                      ? 'bg-emerald-50/70 border-emerald-300 text-emerald-900 font-medium dark:bg-[#0f0f11] dark:border-zinc-700/80 dark:text-zinc-200'
                      : 'bg-slate-50 border-slate-200 text-slate-400 dark:bg-[#0f0f11] dark:border-zinc-800/60 dark:text-zinc-500'
                  }`}
                >
                  <span>Pro Workstation (16 GiB RAM)</span>
                  {calculation?.fits_on_16gib ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400/90" />
                  ) : (
                    <XCircle className="w-4 h-4 text-slate-300 dark:text-zinc-600" />
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Caveat & Methodology Box */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs font-mono text-slate-600 space-y-1.5 dark:bg-[#0f0f11] dark:border-zinc-800/80 dark:text-zinc-400">
            <div className="text-slate-800 dark:text-zinc-300 font-semibold flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
              Empirical Memory Caveat
            </div>
            <p className="text-[11px] leading-relaxed text-slate-500 dark:text-zinc-500 font-sans">
              Values above are mathematical estimates computed in GiB (1024³ bytes) assuming standard GGUF quant headers and FlashAttention-2 KV caching. Real runtime memory can fluctuate based on OS unified memory compression, metal shader buffers, and batch concurrency.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
