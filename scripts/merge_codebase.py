#!/usr/bin/env python3
"""
SovereignRAG Codebase Merger
Combines all repository files, backend code, tests, documentation, sample data,
scripts, and frontend code into a single unified text file (merged_codebase.txt).
"""

import os
from pathlib import Path
import sys
import time

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

OUTPUT_FILE = BASE_DIR / "merged_codebase.txt"

CATEGORIES = [
    (
        "PROJECT ROOT & CONFIGURATION",
        [
            "README.md",
            "requirements.txt",
            "start.sh",
            ".env.example",
            ".gitignore",
        ]
    ),
    (
        "BACKEND CORE ENGINE (backend/)",
        [
            "backend/__init__.py",
            "backend/config.py",
            "backend/errors.py",
            "backend/models.py",
            "backend/storage.py",
            "backend/vector_math.py",
            "backend/document_loader.py",
            "backend/chunker.py",
            "backend/bm25.py",
            "backend/rrf.py",
            "backend/privacy_guard.py",
            "backend/audit_ledger.py",
            "backend/telemetry.py",
            "backend/ollama_client.py",
            "backend/gemini_client.py",
            "backend/evaluation.py",
            "backend/fallback_synth.py",
            "backend/rag_engine.py",
            "backend/main.py",
        ]
    ),
    (
        "BACKEND TEST SUITE (backend/tests/)",
        [
            "backend/tests/__init__.py",
            "backend/tests/conftest.py",
            "backend/tests/test_config.py",
            "backend/tests/test_document_loader.py",
            "backend/tests/test_chunker.py",
            "backend/tests/test_vector_math.py",
            "backend/tests/test_bm25.py",
            "backend/tests/test_rrf.py",
            "backend/tests/test_privacy_guard.py",
            "backend/tests/test_audit_ledger.py",
            "backend/tests/test_telemetry.py",
            "backend/tests/test_ollama_client.py",
            "backend/tests/test_evaluation.py",
            "backend/tests/test_errors.py",
            "backend/tests/test_end_to_end.py",
        ]
    ),
    (
        "SAMPLE ENTERPRISE & CLINICAL DATA (sample_data/)",
        [
            "sample_data/clinical_ehr_cardiology.txt",
            "sample_data/financial_audit_q3.txt",
            "sample_data/legal_msa.txt",
            "sample_data/defense_radar.txt",
        ]
    ),
    (
        "SCRIPTS & VERIFICATION SUITE (scripts/)",
        [
            "scripts/verify.py",
            "scripts/benchmark.py",
            "scripts/verify_air_gap.py",
            "scripts/merge_codebase.py",
        ]
    ),
    (
        "FRONTEND INTERFACE (frontend/)",
        [
            "frontend/package.json",
            "frontend/tsconfig.json",
            "frontend/vite.config.ts",
            "frontend/tailwind.config.js",
            "frontend/postcss.config.js",
            "frontend/index.html",
            "frontend/src/main.tsx",
            "frontend/src/App.tsx",
            "frontend/src/types.ts",
            "frontend/src/api.ts",
            "frontend/src/store.ts",
            "frontend/src/index.css",
            "frontend/src/hooks/useSSE.ts",
            "frontend/src/components/AirGapBadge.tsx",
            "frontend/src/components/TelemetryHUD.tsx",
            "frontend/src/components/ChatInterface.tsx",
            "frontend/src/components/RagVault.tsx",
            "frontend/src/components/ChunkLab.tsx",
            "frontend/src/components/QuantizationMatrix.tsx",
            "frontend/src/components/PiiInspector.tsx",
            "frontend/src/components/ComplianceAuditLedger.tsx",
            "frontend/src/components/DiagnosticsView.tsx",
            "frontend/src/components/CloudSettingsModal.tsx",
            "frontend/src/components/ErrorBoundary.tsx",
            "frontend/src/components/ErrorBanner.tsx",
        ]
    ),
]


def main():
    print(f"📦 Merging SovereignRAG codebase into {OUTPUT_FILE.name}...")
    start_time = time.time()

    processed_files = []
    file_contents = {}

    for cat_name, file_paths in CATEGORIES:
        for rel_path in file_paths:
            p = BASE_DIR / rel_path
            if not p.exists():
                continue

            try:
                content = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = p.read_text(encoding="latin-1", errors="replace")

            line_count = len(content.splitlines())
            file_contents[rel_path] = (cat_name, content, f"{line_count:,} lines")
            processed_files.append(rel_path)

    total_lines = sum(len(c[1].splitlines()) for c in file_contents.values())
    total_chars = sum(len(c[1]) for c in file_contents.values())

    lines_out = []
    lines_out.append("=" * 80)
    lines_out.append("SOVEREIGN-RAG: COMPLETE CODEBASE, TESTS, DOCS & SUITE ARCHIVE")
    lines_out.append("=" * 80)
    lines_out.append(f"• Generated:    {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    lines_out.append(f"• Total Files:  {len(processed_files)}")
    lines_out.append(f"• Total Lines:  {total_lines:,}")
    lines_out.append(f"• Total Chars:  {total_chars:,} characters (~{total_chars / 1024 / 1024:.2f} MB)")
    lines_out.append("=" * 80)
    lines_out.append("")
    lines_out.append("TABLE OF CONTENTS")
    lines_out.append("-" * 80)

    for cat_name, file_paths in CATEGORIES:
        lines_out.append(f"\n📂 {cat_name}")
        for fp in file_paths:
            if fp in file_contents:
                _, _, meta = file_contents[fp]
                lines_out.append(f"   • {fp:<55} ({meta})")

    lines_out.append("\n" + "=" * 80)
    lines_out.append("SOURCE CODE & FILE CONTENTS")
    lines_out.append("=" * 80 + "\n")

    for fp in processed_files:
        cat_name, content, meta = file_contents[fp]
        lines_out.append("\n" + "#" * 80)
        lines_out.append(f"### FILE: {fp}")
        lines_out.append(f"### CATEGORY: {cat_name} | {meta}")
        lines_out.append("#" * 80 + "\n")
        lines_out.append(content)
        if not content.endswith("\n"):
            lines_out.append("")

    full_output = "\n".join(lines_out)
    OUTPUT_FILE.write_text(full_output, encoding="utf-8")

    elapsed = round(time.time() - start_time, 2)
    output_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"✅ Successfully created {OUTPUT_FILE.name}!")
    print(f"• Merged Files: {len(processed_files)}")
    print(f"• Total Lines:  {total_lines:,}")
    print(f"• File Size:    {output_size_mb:.2f} MB ({OUTPUT_FILE.stat().st_size:,} bytes)")
    print(f"• Time Taken:   {elapsed}s")


if __name__ == "__main__":
    main()
