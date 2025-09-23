#!/usr/bin/env python3
"""
Check Codex Turbo Syncthing folder health and sharing.
- Verifies folder id exists
- Ensures Beta device is configured on the folder (if provided)
- Reports folder db status and connections summary
Writes evidence to documents/reports/.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from urllib import request, error


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def ts_suffix() -> str:
    return time.strftime("%Y-%m-%d_%H%M", time.localtime())


def http_call(method: str, url: str, api_key: str | None = None, data: dict | None = None, timeout: int = 5):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = request.Request(url, data=body, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            txt = resp.read().decode("utf-8", errors="ignore")
            return code, txt
    except error.HTTPError as e:
        txt = e.read().decode("utf-8", errors="ignore") if hasattr(e, 'read') else str(e)
        return e.code, txt
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Check Codex Turbo folder status")
    parser.add_argument("--api-url", default=os.environ.get("SYNCTHING_API_URL", "http://localhost:8384"))
    parser.add_argument("--api-key", default=os.environ.get("SYNCTHING_API_KEY"))
    parser.add_argument("--folder-id", default="codex-turbo")
    parser.add_argument("--beta-id", default=os.environ.get("CODEX_TURBO_BETA_ID"))
    args = parser.parse_args()

    if not args.api_key:
        print(json.dumps({"ok": False, "error": "missing_api_key"}))
        return 1

    ping_code, _ = http_call("GET", f"{args.api_url}/rest/system/ping", args.api_key)
    if ping_code != 200:
        print(json.dumps({"ok": False, "error": "syncthing_unreachable", "http": ping_code}))
        return 2

    # Folders
    f_code, f_txt = http_call("GET", f"{args.api_url}/rest/config/folders", args.api_key)
    folders = json.loads(f_txt) if f_code == 200 else []
    folder = next((f for f in folders if f.get("id") == args.folder_id), None)
    exists = folder is not None
    devices = [d.get("deviceID") for d in (folder.get("devices", []) if folder else [])]
    beta_ok = (args.beta_id in devices) if args.beta_id else None

    # DB status
    s_code, s_txt = http_call("GET", f"{args.api_url}/rest/db/status?folder={args.folder_id}", args.api_key)
    db_status = json.loads(s_txt) if s_code == 200 else {"http": s_code, "raw": s_txt}

    # Connections
    c_code, c_txt = http_call("GET", f"{args.api_url}/rest/system/connections", args.api_key)
    conns = json.loads(c_txt) if c_code == 200 else {"http": c_code}

    result = {
        "ok": exists and (beta_ok is True or beta_ok is None),
        "exists": exists,
        "beta_ok": beta_ok,
        "devices": devices,
        "db_status": db_status,
        "connections": conns,
        "timestamp": now_iso(),
    }
    print(json.dumps(result, indent=2))

    reports = Path("documents/reports")
    reports.mkdir(parents=True, exist_ok=True)
    evidence = {
        "component": "codex_turbo_syncthing_check",
        "started_at": now_iso(),
        "ended_at": now_iso(),
        "inputs": {
            "api_url": args.api_url,
            "folder_id": args.folder_id,
            "beta_id": args.beta_id,
        },
        "outputs": result,
        "verdict": "PASS" if result.get("ok") else "FAIL",
    }
    path = reports / f"EVIDENCE_codex_turbo_syncthing_check_{ts_suffix()}.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

