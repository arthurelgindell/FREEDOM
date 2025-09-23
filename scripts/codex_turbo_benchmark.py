#!/usr/bin/env python3
"""
Codex Turbo benchmark (local-only) for Alpha.

Measures:
- Add throughput (entries/sec)
- Query latency (min/avg/p95 ms)
- Memory usage (tracemalloc peak, ru_maxrss)

Writes evidence to documents/reports/.
Uses a temporary local store so the real store is not polluted.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import shutil
import statistics
import string
import sys
import time
from pathlib import Path


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def ts_suffix() -> str:
    return time.strftime("%Y-%m-%d_%H%M%S", time.localtime())


def try_ru_maxrss_bytes() -> int | None:
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss = usage.ru_maxrss
        if platform.system() == "Darwin":
            # macOS returns bytes
            return int(rss)
        else:
            # Linux returns kilobytes
            return int(rss) * 1024
    except Exception:
        return None


def gen_text(idx: int) -> str:
    words = [
        "codex", "turbo", "alpha", "notes", "performance", "memory",
        "syncthing", "folder", "vector", "search", "index", "evidence",
    ]
    random.shuffle(words)
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    return f"{idx} {' '.join(words)} {suffix}"


def bench(n_add: int, n_queries: int, top_k: int, seed: int, temp_store: Path) -> dict:
    random.seed(seed)
    sys.path.append(os.path.abspath("."))
    from core.codex_turbo_discreet import codex_turbo_discreet as ctd

    # Point to temp store and disable bridge
    os.environ["CODEX_TURBO_DISCREET_HOME"] = str(temp_store)
    os.environ["CODEX_TURBO_BRIDGE"] = "0"

    ctd.ensure(check_syncthing=False, write_evidence=False)

    # Memory tracking
    try:
        import tracemalloc

        tracemalloc.start()
        tracing = True
    except Exception:
        tracing = False

    # Add phase
    t0 = time.perf_counter()
    for i in range(n_add):
        ctd.add(gen_text(i), metadata={"i": i}, tags=["bench", "alpha"])
    t1 = time.perf_counter()
    add_time = t1 - t0

    # Query phase
    latencies = []
    queries = ["codex turbo", "alpha performance", "memory evidence", "vector index", "syncthing folder"]
    t2 = time.perf_counter()
    for i in range(n_queries):
        q = queries[i % len(queries)]
        q0 = time.perf_counter()
        _ = ctd.query(q, top_k=top_k)
        latencies.append((time.perf_counter() - q0) * 1000.0)
    t3 = time.perf_counter()
    query_time = t3 - t2

    peak_bytes = None
    if tracing:
        current, peak = tracemalloc.get_traced_memory()
        peak_bytes = int(peak)
        tracemalloc.stop()

    rss_bytes = try_ru_maxrss_bytes()

    # Stats
    add_eps = n_add / add_time if add_time > 0 else float("inf")
    q_min = min(latencies) if latencies else 0.0
    q_avg = statistics.mean(latencies) if latencies else 0.0
    q_p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0.0)

    return {
        "n_add": n_add,
        "n_queries": n_queries,
        "top_k": top_k,
        "add_seconds": add_time,
        "add_eps": add_eps,
        "query_seconds": query_time,
        "query_latency_ms": {
            "min": q_min,
            "avg": q_avg,
            "p95": q_p95,
        },
        "memory": {
            "ru_maxrss_bytes": rss_bytes,
            "tracemalloc_peak_bytes": peak_bytes,
        },
        "timestamp": now_iso(),
    }


def main():
    ap = argparse.ArgumentParser(description="Codex Turbo benchmark (local-only)")
    ap.add_argument("--n-add", type=int, default=2000)
    ap.add_argument("--n-queries", type=int, default=100)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--temp-store", type=str, default=".freedom/.tmp_codex_bench")
    ap.add_argument("--keep", action="store_true", help="Keep temp store (do not delete)")
    args = ap.parse_args()

    temp_store = Path(args.temp_store)
    if temp_store.exists():
        shutil.rmtree(temp_store)
    temp_store.mkdir(parents=True, exist_ok=True)

    started = now_iso()
    res = bench(args.n_add, args.n_queries, args.top_k, args.seed, temp_store)
    print(json.dumps(res, indent=2))

    # Evidence
    reports = Path("documents/reports")
    reports.mkdir(parents=True, exist_ok=True)
    evidence = {
        "component": "codex_turbo_benchmark",
        "started_at": started,
        "ended_at": now_iso(),
        "inputs": {
            "n_add": args.n_add,
            "n_queries": args.n_queries,
            "top_k": args.top_k,
        },
        "outputs": res,
        "verdict": "PASS",
    }
    outp = reports / f"EVIDENCE_codex_turbo_benchmark_{ts_suffix()}.json"
    outp.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    if not args.keep:
        shutil.rmtree(temp_store, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

