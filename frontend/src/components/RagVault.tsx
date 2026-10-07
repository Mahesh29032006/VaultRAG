import React, { useState, useEffect } from 'react';
import {
  Upload,
  FileText,
  Database,
  CheckCircle,
  Clock,
  Layers,
  Search,
  Hash,
  Trash2,
} from 'lucide-react';
import { useAppStore } from '../store';
import { api } from '../api';
import { DocumentCategory, IngestedDocument } from '../types';

export const RagVault: React.FC = () => {
  const {
    documents,
    totalChunks,
    fetchDocuments,
    fetchHealth,
    setGlobalError,
  } = useAppStore();

  const [uploading, setUploading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<DocumentCategory>('GENERAL');
  const [dragActive, setDragActive] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDelete = async (docId: string, title: string) => {
    if (!window.confirm(`Delete document "${title}" from the RAG Vault?`)) return;
    try {
      await api.deleteDocument(docId);
      await Promise.all([fetchDocuments(), fetchHealth()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setGlobalError(`Delete failed: ${msg}`);
    }
  };

  const handleCategoryChange = async (docId: string, newCategory: string) => {
    try {
      await api.updateDocumentCategory(docId, newCategory);
      await Promise.all([fetchDocuments(), fetchHealth()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setGlobalError(`Update category failed: ${msg}`);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    try {
      await api.uploadDocument(selectedFile, selectedCategory);
      setSelectedFile(null);
      await Promise.all([fetchDocuments(), fetchHealth()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setGlobalError(`Upload failed: ${msg}`);
    } finally {
      setUploading(false);
    }
  };

  const filteredDocs = documents.filter(
    (d) =>
      d.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      d.category.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const getCategoryColor = (cat: DocumentCategory) => {
    switch (cat) {
      case 'CLINICAL':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/20';
      case 'FINANCIAL':
        return 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-500/10 dark:text-purple-300 dark:border-purple-500/20';
      case 'LEGAL':
        return 'bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-500/10 dark:text-sky-300 dark:border-sky-500/20';
      case 'DEFENSE':
        return 'bg-amber-100 text-amber-900 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/20';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700';
    }
  };

  return (
    <div className="max-w-6xl mx-auto w-full px-4 py-6 space-y-6">
      {/* Top Banner & Stats */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm dark:bg-[#151518] dark:border-zinc-800/80">
        <div>
          <h2 className="text-base font-semibold text-slate-800 dark:text-zinc-100 flex items-center gap-2">
            <Database className="w-4 h-4 text-indigo-600 dark:text-zinc-400" />
            Knowledge Vault
          </h2>
          <p className="text-xs text-slate-500 font-mono mt-1 dark:text-zinc-400">
            Documents indexed locally in DualIndex (FAISS 384-D Airgap / ChromaDB 768-D Cloud)
          </p>
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="bg-slate-50 px-3.5 py-2 rounded-xl border border-slate-200 text-center dark:bg-[#0f0f11] dark:border-zinc-800/80">
            <span className="text-slate-500 dark:text-zinc-500 block text-[10px]">DOCUMENTS</span>
            <span className="text-slate-900 dark:text-zinc-200 font-semibold text-sm">{documents.length}</span>
          </div>
          <div className="bg-slate-50 px-3.5 py-2 rounded-xl border border-slate-200 text-center dark:bg-[#0f0f11] dark:border-zinc-800/80">
            <span className="text-slate-500 dark:text-zinc-500 block text-[10px]">CHUNKS</span>
            <span className="text-slate-900 dark:text-zinc-200 font-semibold text-sm">{totalChunks}</span>
          </div>
        </div>
      </div>

      {/* Drag & Drop Ingestion Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4 dark:bg-[#151518] dark:border-zinc-800/80">
        <h3 className="text-xs font-semibold text-slate-600 dark:text-zinc-400 uppercase tracking-wider font-mono flex items-center gap-2">
          <Upload className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
          Ingest Knowledge File
        </h3>

        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
            dragActive
              ? 'border-indigo-400 bg-indigo-50/50 dark:border-zinc-500 dark:bg-zinc-800/30'
              : 'border-slate-300 hover:border-indigo-400 bg-slate-50/50 dark:border-zinc-800/80 dark:hover:border-zinc-700 dark:bg-[#0f0f11]/50'
          }`}
        >
          <input
            type="file"
            id="file-upload"
            onChange={handleFileChange}
            accept=".txt,.pdf,.md,.py"
            className="hidden"
          />
          <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center space-y-2">
            <Upload className="w-7 h-7 text-indigo-500 dark:text-zinc-500" />
            <span className="text-sm font-medium text-slate-800 dark:text-zinc-200">
              {selectedFile ? selectedFile.name : 'Click to select or drag and drop document'}
            </span>
            <span className="text-xs text-slate-500 dark:text-zinc-500 font-mono">
              Supported: .txt, .pdf, .md, .py (Max 50MB, &le;5M characters)
            </span>
          </label>
        </div>

        {/* Ingestion Options Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="text-slate-600 dark:text-zinc-400">Category Tag:</span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as DocumentCategory)}
              className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-slate-700 text-xs font-mono focus:outline-none focus:border-indigo-500 dark:bg-[#0f0f11] dark:border-zinc-800 dark:text-zinc-200 dark:focus:border-zinc-600"
            >
              <option value="CLINICAL">CLINICAL</option>
              <option value="FINANCIAL">FINANCIAL</option>
              <option value="LEGAL">LEGAL</option>
              <option value="DEFENSE">DEFENSE</option>
              <option value="GENERAL">GENERAL</option>
            </select>
          </div>

          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl text-xs font-medium flex items-center gap-2 transition-all shadow-sm dark:bg-zinc-100 dark:hover:bg-white dark:disabled:bg-zinc-800 dark:disabled:text-zinc-600 dark:text-zinc-900"
          >
            {uploading ? (
              <>
                <Clock className="w-3.5 h-3.5 animate-spin text-white dark:text-zinc-700" />
                <span>Chunking & Indexing...</span>
              </>
            ) : (
              <>
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Ingest into Vault</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Document Library Table */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4 dark:bg-[#151518] dark:border-zinc-800/80">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="text-xs font-semibold text-slate-600 dark:text-zinc-400 uppercase tracking-wider font-mono flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-indigo-600 dark:text-zinc-400" />
            Active Vault Corpus ({documents.length})
          </h3>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 dark:text-zinc-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Search documents by title or category..."
              className="bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 font-mono w-64 focus:outline-none focus:border-indigo-500 dark:bg-[#0f0f11] dark:border-zinc-800 dark:text-zinc-200 dark:placeholder-zinc-500 dark:focus:border-zinc-600"
            />
          </div>
        </div>

        {filteredDocs.length === 0 ? (
          <div className="text-center py-10 text-slate-400 dark:text-zinc-500 text-xs font-mono">
            No matching documents found in knowledge vault.
          </div>
        ) : (
          <div className="overflow-x-auto border border-slate-200 rounded-xl dark:border-zinc-800/80">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-100 text-slate-600 border-b border-slate-200 dark:bg-zinc-900/90 dark:text-zinc-400 dark:border-zinc-800">
                <tr>
                  <th className="p-3 font-medium">Document Title</th>
                  <th className="p-3 font-medium">Category</th>
                  <th className="p-3 font-medium">Chunks</th>
                  <th className="p-3 font-medium">SHA-256 Digest</th>
                  <th className="p-3 font-medium">Ingested At</th>
                  <th className="p-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white dark:divide-zinc-800/60 dark:bg-[#121215]">
                {filteredDocs.map((doc: IngestedDocument) => (
                  <tr key={doc.id} className="hover:bg-slate-50 dark:hover:bg-zinc-900/40">
                    <td className="p-3 text-slate-800 dark:text-zinc-200 font-medium flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-slate-400 dark:text-zinc-400 shrink-0" />
                      {doc.title}
                    </td>
                    <td className="p-3">
                      <select
                        value={doc.category}
                        onChange={(e) => handleCategoryChange(doc.id, e.target.value)}
                        className={`px-2 py-0.5 rounded border text-[10px] font-semibold cursor-pointer ${getCategoryColor(
                          doc.category
                        )}`}
                        title="Change document category tag"
                      >
                        <option value="GENERAL">GENERAL</option>
                        <option value="CLINICAL">CLINICAL</option>
                        <option value="FINANCIAL">FINANCIAL</option>
                        <option value="LEGAL">LEGAL</option>
                        <option value="DEFENSE">DEFENSE</option>
                      </select>
                    </td>
                    <td className="p-3 text-slate-600 dark:text-zinc-300">
                      <span className="flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5 text-slate-400 dark:text-zinc-500" />
                        {doc.chunk_count}
                      </span>
                    </td>
                    <td className="p-3 text-slate-500 dark:text-zinc-400 font-mono text-[11px]">
                      <span className="flex items-center gap-1" title={doc.sha256}>
                        <Hash className="w-3 h-3 text-slate-400 dark:text-zinc-500" />
                        {doc.sha256.substring(0, 16)}...
                      </span>
                    </td>
                    <td className="p-3 text-slate-400 dark:text-zinc-500 text-[11px]">
                      {doc.ingested_at.replace('T', ' ').substring(0, 19)}
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleDelete(doc.id, doc.title)}
                        className="p-1 hover:bg-rose-50 text-slate-400 hover:text-rose-600 rounded transition-colors dark:hover:bg-zinc-800 dark:text-zinc-500 dark:hover:text-red-400"
                        title="Delete document from Vault"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
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
