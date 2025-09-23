#!/usr/bin/env python3
"""
Diagnose CCKS Turbo facilities and Syncthing connectivity for planning.
Produces a single evidence JSON under documents/reports/.

Checks:
- ~/.claude/ccks presence and basic commands (stats/query) with timeouts
- ~/.claude/ccks_turbo_status.json existence and selected fields
- Syncthing REST reachability on localhost:8384 (403 => reachable without key)
- CodexTurboDiscreet bridge/local availability via ensure()

No secrets read from files; uses SYNCTHING_API_KEY env var if provided.
Outputs: concise summary to stdout and writes evidence file.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
import sys


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def ts_suffix() -> str:
    return time.strftime("%Y-%m-%d_%H%M", time.localtime())


def run(cmd: list[str], timeout: int = 5):
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.decode(errors="ignore"), proc.stderr.decode(errors="ignore")
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:
        return 1, "", str(e)


def safe_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


def check_ccks_cli():
    ccks_bin = Path.home() / ".claude/ccks"
    status_file = Path.home() / ".claude/ccks_turbo_status.json"
    available = ccks_bin.exists() and os.access(ccks_bin, os.X_OK)
    status_json = None
    if status_file.exists():
        try:
            status_json = json.loads(status_file.read_text())
        except Exception:
            status_json = None

    stats_rc = None
    stats = None
    if available:
        rc, out, err = run([str(ccks_bin), "stats"], timeout=6)
        stats_rc = rc
        stats = safe_json(out) or {"raw": out.strip(), "stderr": err.strip()}

    query_rc = None
    query = None
    if available:
        rc, out, err = run([str(ccks_bin), "query", "health check"], timeout=8)
        query_rc = rc
        query = safe_json(out) or {"raw": out.strip(), "stderr": err.strip()}

    return {
        "bin": str(ccks_bin),
        "available": available,
        "status_file": str(status_file),
        "status": status_json,
        "stats_rc": stats_rc,
        "stats": stats,
        "query_rc": query_rc,
        "query": query,
    }


def check_syncthing():
    api_key = os.environ.get("SYNCTHING_API_KEY")
    base = "http://localhost:8384"
    headers = []
    if api_key:
        headers = ["-H", f"X-API-Key: {api_key}"]

    # ping
    rc, out, err = run(["curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}", *headers, f"{base}/rest/system/ping"], timeout=4)
    # Interpret http code in stderr due to -o redirect
    http_code = err.strip()[-3:] if err else ""

    details = {"reachable": False, "http": http_code, "has_key": bool(api_key)}
    if http_code in ("200", "403"):
        details["reachable"] = True

    # connections (optional; only if reachable and has key)
    connections = None
    if details["reachable"] and api_key:
        rc2, out2, err2 = run(["curl", "-s", *headers, f"{base}/rest/system/connections"], timeout=4)
        connections = safe_json(out2) or {"raw": out2.strip()}

    details["connections"] = connections
    return details


def check_codex_module():
    # Ensure repo root on sys.path for local import
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from core.codex_turbo_discreet import codex_turbo_discreet as ctd
    # local only
    os.environ["CODEX_TURBO_BRIDGE"] = "0"
    local = ctd.ensure(check_syncthing=False, write_evidence=False)
    # bridge (do not fail if not present)
    os.environ["CODEX_TURBO_BRIDGE"] = "1"
    bridge = ctd.ensure(check_syncthing=False, write_evidence=False)
    return {"local": local, "bridge": bridge}


def main():
    ccks = check_ccks_cli()
    syn = check_syncthing()
    codex = check_codex_module()

    summary = {
        "timestamp": now_iso(),
        "ccks": {
            "available": ccks["available"],
            "stats_ok": ccks["stats_rc"] == 0 if ccks["stats_rc"] is not None else False,
            "query_ok": ccks["query_rc"] == 0 if ccks["query_rc"] is not None else False,
            "status": ccks.get("status"),
        },
        "syncthing": syn,
        "codex": {
            "local_ok": bool(codex.get("local", {}).get("ok")),
            "bridge_available": bool(codex.get("bridge", {}).get("status", {}).get("bridge_available")),
        },
    }

    print(json.dumps(summary, indent=2))

    # Write evidence
    reports = Path("documents/reports")
    reports.mkdir(parents=True, exist_ok=True)
    evidence = {
        "component": "ccks_facilities_diagnose",
        "started_at": now_iso(),
        "ended_at": now_iso(),
        "summary": summary,
        "verdict": "PASS" if (summary["ccks"]["available"] or summary["syncthing"]["reachable"]) else "UNKNOWN",
    }
    out_path = reports / f"EVIDENCE_ccks_facilities_{ts_suffix()}.json"
    out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
