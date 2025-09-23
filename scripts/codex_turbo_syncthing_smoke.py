#!/usr/bin/env python3
"""
End-to-end smoke for Codex Turbo + Syncthing on Alpha.

Steps:
1) Capture baseline db/status for folder (sequence, bytes, totals)
2) Add a Codex Turbo note (local store)
3) Create a small file in the folder to force a new item
4) Poll db/status until sequence/bytes/total items change or timeout
5) Write evidence to documents/reports/

Requires: SYNCTHING_API_KEY, Syncthing on localhost:8384, folder id present.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from subprocess import run, PIPE
from urllib import request, error


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def ts_suffix() -> str:
    return time.strftime("%Y-%m-%d_%H%M%S", time.localtime())


def http_get_json(url: str, api_key: str, timeout: int = 5):
    req = request.Request(url, headers={"X-API-Key": api_key})
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_db_status(api_url: str, api_key: str, folder_id: str) -> dict:
    url = f"{api_url}/rest/db/status?folder={folder_id}"
    try:
        return http_get_json(url, api_key)
    except Exception as e:
        return {"error": str(e)}


def codex_add_note(repo_root: Path, text: str) -> dict:
    cli = repo_root / "scripts/codex-turbo"
    env = os.environ.copy()
    env["CODEX_TURBO_BRIDGE"] = "0"
    p = run([str(cli), "add", "--no-bridge", "--text", text, "--tags", "codex,smoke"], stdout=PIPE, stderr=PIPE, text=True, env=env)
    try:
        return json.loads(p.stdout.strip() or "{}")
    except Exception:
        return {"ok": False, "raw": p.stdout, "err": p.stderr}


def touch_smoke_file(folder_path: Path) -> Path:
    smoke_dir = folder_path / "_smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    fp = smoke_dir / f"note_{ts_suffix()}.txt"
    fp.write_text(f"codex turbo smoke {now_iso()}\n")
    return fp


def main():
    parser = argparse.ArgumentParser(description="Codex Turbo + Syncthing smoke")
    parser.add_argument("--api-url", default=os.environ.get("SYNCTHING_API_URL", "http://localhost:8384"))
    parser.add_argument("--api-key", default=os.environ.get("SYNCTHING_API_KEY"))
    parser.add_argument("--folder-id", default="codex-turbo")
    parser.add_argument("--folder-path", default=str((Path.cwd() / ".freedom/codex_ccks").resolve()))
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    if not args.api_key:
        print(json.dumps({"ok": False, "error": "missing_api_key"}))
        return 1

    started = now_iso()
    repo_root = Path.cwd()
    folder_path = Path(args.folder_path)
    folder_path.mkdir(parents=True, exist_ok=True)

    before = get_db_status(args.api_url, args.api_key, args.folder_id)

    add_res = codex_add_note(repo_root, f"Syncthing smoke at {now_iso()}")
    smoke_file = touch_smoke_file(folder_path)

    changed = False
    after = None
    baseline_seq = before.get("sequence") if isinstance(before, dict) else None
    baseline_local = before.get("localTotalItems") if isinstance(before, dict) else None
    baseline_bytes = before.get("localBytes") if isinstance(before, dict) else None

    deadline = time.time() + max(5, args.timeout)
    while time.time() < deadline:
        time.sleep(1)
        cur = get_db_status(args.api_url, args.api_key, args.folder_id)
        seq = cur.get("sequence")
        local_items = cur.get("localTotalItems")
        lbytes = cur.get("localBytes")
        if (
            (isinstance(seq, int) and baseline_seq is not None and seq > baseline_seq)
            or (isinstance(local_items, int) and baseline_local is not None and local_items > baseline_local)
            or (isinstance(lbytes, int) and baseline_bytes is not None and lbytes > baseline_bytes)
        ):
            changed = True
            after = cur
            break
    if after is None:
        after = get_db_status(args.api_url, args.api_key, args.folder_id)

    result = {
        "ok": bool(changed),
        "folder": args.folder_id,
        "folder_path": str(folder_path),
        "add_result": add_res,
        "smoke_file": str(smoke_file),
        "db_before": before,
        "db_after": after,
        "timestamp": now_iso(),
    }
    print(json.dumps(result, indent=2))

    reports = repo_root / "documents/reports"
    reports.mkdir(parents=True, exist_ok=True)
    evidence = {
        "component": "codex_turbo_syncthing_smoke",
        "started_at": started,
        "ended_at": now_iso(),
        "inputs": {
            "api_url": args.api_url,
            "folder_id": args.folder_id,
            "timeout": args.timeout,
        },
        "outputs": result,
        "verdict": "PASS" if result.get("ok") else "FAIL",
    }
    outp = reports / f"EVIDENCE_codex_turbo_syncthing_smoke_{ts_suffix()}.json"
    outp.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
