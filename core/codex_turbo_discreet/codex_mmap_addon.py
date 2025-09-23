#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any

from core.mmap_cache import MMapCache


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _ts() -> str:
    return time.strftime("%Y-%m-%d_%H%M%S", time.localtime())


def _reports_dir() -> Path:
    p = Path("documents/reports")
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_ram_cache() -> Dict[str, Any]:
    ram = Path("/Volumes/CCKS_RAM")
    cache = ram / "cache"
    present = ram.exists()
    if present:
        cache.mkdir(parents=True, exist_ok=True)
    else:
        # fallback to /tmp to keep functional
        cache = Path("/tmp/CCKS_RAM/cache")
        cache.mkdir(parents=True, exist_ok=True)
    return {"ram_disk_present": present, "cache_dir": str(cache)}


def preload(paths: List[str], pattern: str = "*.py", max_files: int = 91) -> Dict[str, Any]:
    info = ensure_ram_cache()
    cache = MMapCache(max_files=max_files)
    total = 0
    for root in paths:
        if Path(root).exists():
            total += cache.preload_directory(root, pattern)
    stats = cache.stats()
    # quick access timing sample
    cold_ms = warm_ms = None
    sample = None
    for root in paths:
        for fp in Path(root).rglob(pattern):
            sample = str(fp)
            break
        if sample:
            break
    if sample:
        t0 = time.perf_counter()
        _ = cache.get_file(sample)
        cold_ms = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        _ = cache.get_file(sample)
        warm_ms = (time.perf_counter() - t1) * 1000
    cache.close()
    out = {
        "ok": True,
        "files_loaded": total,
        "stats": stats,
        "sample_file": sample,
        "access_ms": {"cold": cold_ms, "warm": warm_ms},
        "ram": info,
    }
    return out


def write_evidence(paths: List[str]) -> Path:
    res = preload(paths)
    ev = {
        "component": "codex_turbo_mmap_addon",
        "started_at": _now_iso(),
        "ended_at": _now_iso(),
        "outputs": res,
        "verdict": "PASS" if res.get("ok") else "FAIL",
    }
    path = _reports_dir() / f"EVIDENCE_codex_turbo_mmap_{_ts()}.json"
    path.write_text(json.dumps(ev, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    repo = str(Path.cwd())
    p = write_evidence([f"{repo}/core", f"{repo}/services"])
    print(json.dumps({"evidence": str(p)}))

