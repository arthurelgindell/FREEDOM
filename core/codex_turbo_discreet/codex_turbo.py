#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Any

from .codex_turbo_discreet import ensure as ensure_store, stats as store_stats
from .codex_mmap_addon import ensure_ram_cache, preload as mmap_preload
from .codex_gpu_accelerator import is_available as gpu_is_available, write_evidence as gpu_write_evidence


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _ts() -> str:
    return time.strftime("%Y-%m-%d_%H%M%S", time.localtime())


def _reports_dir() -> Path:
    p = Path("documents/reports")
    p.mkdir(parents=True, exist_ok=True)
    return p


def facilities_summary() -> Dict[str, Any]:
    # Storage (DB + RAM)
    store = ensure_store(check_syncthing=False, write_evidence=False)
    db = store.get("status", {}).get("db", {})
    ram = ensure_ram_cache()

    # Syncthing (state-only; health script handles deeper checks)
    syn = {"folder_id": "codex-turbo", "path": str((Path.cwd() / ".freedom/codex_ccks").resolve())}

    # Components
    components = {
        "orchestrator": __file__,
        "gpu_accelerator": "core/codex_turbo_discreet/codex_gpu_accelerator.py",
        "mmap_addon": "core/codex_turbo_discreet/codex_mmap_addon.py",
        "engine": "core/codex_turbo_discreet/sqlite_store.py",
    }

    # GPU availability
    gpu = gpu_is_available()

    # Performance resources (reported, not reserved)
    perf = {
        "gpu_backend": gpu.get("backend"),
        "ram_disk_present": ram.get("ram_disk_present"),
        "db_size_bytes": db.get("db_size"),
        "entries_count": db.get("count"),
    }

    # Knowledge capabilities (from stats)
    s = store_stats()
    knowledge = {
        "entries": s.get("count", 0),
        "db_path": s.get("db_path", ""),
        "mode": s.get("mode", "db"),
        "fts5": s.get("fts5", False),
    }

    summary = {
        "timestamp": _now_iso(),
        "storage": {
            "ram_disk": {
                "path": "/Volumes/CCKS_RAM",
                "present": ram.get("ram_disk_present"),
                "cache_dir": ram.get("cache_dir"),
            },
            "database": {
                "type": "sqlite",
                "path": db.get("db_path"),
                "size_bytes": db.get("db_size"),
                "entries": db.get("count"),
            },
        },
        "syncthing": syn,
        "components": components,
        "performance": perf,
        "knowledge": knowledge,
    }
    return summary


def write_evidence_preload() -> Path:
    repo = Path.cwd()
    res = mmap_preload([str(repo / "core"), str(repo / "services")])
    ev = {
        "component": "codex_turbo_preload",
        "started_at": _now_iso(),
        "ended_at": _now_iso(),
        "outputs": res,
        "verdict": "PASS" if res.get("ok") else "FAIL",
    }
    p = _reports_dir() / f"EVIDENCE_codex_turbo_preload_{_ts()}.json"
    p.write_text(json.dumps(ev, indent=2), encoding="utf-8")
    return p


def write_evidence_facilities() -> Path:
    summ = facilities_summary()
    ev = {
        "component": "codex_turbo_facilities",
        "started_at": _now_iso(),
        "ended_at": _now_iso(),
        "outputs": summ,
        "verdict": "PASS",
    }
    p = _reports_dir() / f"EVIDENCE_codex_turbo_facilities_{_ts()}.json"
    p.write_text(json.dumps(ev, indent=2), encoding="utf-8")
    return p


if __name__ == "__main__":
    f1 = write_evidence_facilities()
    f2 = write_evidence_preload()
    f3 = gpu_write_evidence(200)
    print(json.dumps({"facilities": str(f1), "preload": str(f2), "gpu": str(f3)}))

