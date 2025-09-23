#!/usr/bin/env python3
"""
Codex Turbo mandatory bootstrap (Alpha startup).

Actions (idempotent):
- Ensure Codex Turbo local store (evidence optional)
- Discover Beta device ID from local Syncthing config
- If SYNCTHING_API_KEY present: register/share folder with Beta and verify status
- Write a single bootstrap evidence report under documents/reports/

Exit 0 if local ensure succeeds (Turbo Mode ON locally). Non-zero only on fatal local errors.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def ts_suffix() -> str:
    return time.strftime("%Y-%m-%d_%H%M%S", time.localtime())


def run_json(cmd: list[str], env: dict | None = None):
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    try:
        return p.returncode, json.loads(p.stdout or "{}"), p.stderr
    except Exception:
        return p.returncode, {"raw": p.stdout, "stderr": p.stderr}, p.stderr


def main():
    repo = Path.cwd()
    reports = repo / "documents/reports"
    reports.mkdir(parents=True, exist_ok=True)

    started = now_iso()
    results = {
        "local": None,
        "beta": None,
        "register": None,
        "check": None,
    }

    # 1) Ensure local Codex Turbo
    env_local = os.environ.copy()
    env_local.setdefault("CODEX_TURBO_BRIDGE", "0")
    rc, ensure_out, _ = run_json([str(repo / "scripts/codex-turbo"), "ensure", "--no-bridge"], env=env_local)
    results["local"] = {"rc": rc, "out": ensure_out}

    # If ensure fails, still continue to try registering Syncthing but mark failure
    # 2) Discover Beta ID from local Syncthing config
    rc, devices_out, _ = run_json(["python3", str(repo / "scripts/syncthing_list_devices_from_config.py")])
    results["beta"] = {"rc": rc, "out": devices_out}
    beta_id = None
    if devices_out.get("ok"):
        cands = devices_out.get("beta_candidates") or []
        if cands:
            beta_id = cands[0].get("id")

    # 3) Register/share via Syncthing REST if API key present
    syn_key = os.environ.get("SYNCTHING_API_KEY")
    if syn_key:
        env_syn = os.environ.copy()
        env_syn["SYNCTHING_API_KEY"] = syn_key
        reg_cmd = ["python3", str(repo / "scripts/syncthing_register_codex_turbo.py"), "--api-url", "http://localhost:8384"]
        if beta_id:
            reg_cmd += ["--share-with", beta_id]
        rc, reg_out, _ = run_json(reg_cmd, env=env_syn)
        results["register"] = {"rc": rc, "out": reg_out}

        chk_cmd = ["python3", str(repo / "scripts/syncthing_check_codex_turbo.py"), "--api-url", "http://localhost:8384"]
        if beta_id:
            chk_cmd += ["--beta-id", beta_id]
        rc, chk_out, _ = run_json(chk_cmd, env=env_syn)
        results["check"] = {"rc": rc, "out": chk_out}
    else:
        results["register"] = {"skipped": True, "reason": "missing_SYNCTHING_API_KEY"}
        results["check"] = {"skipped": True}

    verdict = "PASS" if (results["local"]["rc"] == 0) else "FAIL"

    evidence = {
        "component": "codex_turbo_bootstrap",
        "started_at": started,
        "ended_at": now_iso(),
        "outputs": results,
        "verdict": verdict,
    }
    outp = reports / f"EVIDENCE_codex_turbo_bootstrap_{ts_suffix()}.json"
    outp.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print(json.dumps({"ok": verdict == "PASS", "beta_id": beta_id, "evidence": str(outp)}))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

