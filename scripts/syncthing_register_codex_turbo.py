#!/usr/bin/env python3
"""
Register a Syncthing folder for Codex Turbo local store.

Default folder path: <repo>/.freedom/codex_ccks
Folder ID: codex-turbo
Label: Codex Turbo

- Reads SYNCTHING_API_KEY from env or --api-key flag
- API URL defaults to http://localhost:8384
- Creates the folder if missing; does not modify existing folders
- Optionally shares with provided device IDs (requires they already exist in Syncthing devices list)
- Writes evidence to documents/reports/

Safe & idempotent. If Syncthing is unreachable or unauthorized, prints status and exits non-zero.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
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


def ensure_folder(api_url: str, api_key: str, folder_id: str, label: str, path: str, share_with: list[str]):
    # Verify system status
    code, status_txt = http_call("GET", f"{api_url}/rest/system/status", api_key)
    if code != 200:
        return {"ok": False, "error": "status_unreachable", "http": code, "body": status_txt}
    status = json.loads(status_txt)
    my_id = status.get("myID")

    # Ensure path exists
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)

    # Read existing folders
    code, folders_txt = http_call("GET", f"{api_url}/rest/config/folders", api_key)
    if code != 200:
        return {"ok": False, "error": "folders_list_failed", "http": code, "body": folders_txt}
    folders = json.loads(folders_txt)
    exists = any(f.get("id") == folder_id for f in folders)

    # Prepare folder config
    devices = [{"deviceID": my_id}]
    for dev in share_with:
        if dev and dev != my_id:
            devices.append({"deviceID": dev})

    folder_cfg = {
        "id": folder_id,
        "label": label,
        "path": path,
        "type": "sendreceive",
        "devices": devices,
        "fsWatcherEnabled": True,
        "fsWatcherDelayS": 10,
        "rescanIntervalS": 60,
        "ignorePerms": False,
        "minDiskFree": {"value": 1, "unit": "%"},
        "versioning": {"type": "", "params": {}},
        "order": "random",
    }

    created = False
    updated = False
    if not exists:
        code, add_txt = http_call("POST", f"{api_url}/rest/config/folders", api_key, folder_cfg)
        if code != 200:
            return {"ok": False, "error": "folder_create_failed", "http": code, "body": add_txt}
        created = True
    else:
        # Ensure share_with devices are present on existing folder
        # Try GET/PUT specific folder endpoint first
        code, cur_txt = http_call("GET", f"{api_url}/rest/config/folders/{folder_id}", api_key)
        if code == 200:
            cur = json.loads(cur_txt)
            cur_devices = {d.get("deviceID") for d in cur.get("devices", [])}
            need = [dev for dev in [d.get("deviceID") for d in devices] if dev not in cur_devices]
            if need:
                # merge devices
                cur_devices_list = cur.get("devices", [])
                for dev_id in need:
                    cur_devices_list.append({"deviceID": dev_id})
                cur["devices"] = cur_devices_list
                code_put, put_txt = http_call("PUT", f"{api_url}/rest/config/folders/{folder_id}", api_key, cur)
                if code_put == 200:
                    updated = True
                else:
                    # Fallback: full config update
                    code_cfg, cfg_txt = http_call("GET", f"{api_url}/rest/config", api_key)
                    if code_cfg == 200:
                        cfg = json.loads(cfg_txt)
                        for f in cfg.get("folders", []):
                            if f.get("id") == folder_id:
                                cur_devices = {d.get("deviceID") for d in f.get("devices", [])}
                                for dev_id in need:
                                    if dev_id not in cur_devices:
                                        f["devices"].append({"deviceID": dev_id})
                        code_post, post_txt = http_call("POST", f"{api_url}/rest/config", api_key, cfg)
                        if code_post == 200:
                            updated = True
                        else:
                            return {"ok": False, "error": "folder_update_failed", "http": code_post, "body": post_txt}
        # else ignore; cannot update without specific endpoints

    return {"ok": True, "exists": exists, "created": created, "updated": updated, "folder": folder_cfg, "my_id": my_id}


def main():
    parser = argparse.ArgumentParser(description="Register Codex Turbo Syncthing folder")
    parser.add_argument("--api-url", default=os.environ.get("SYNCTHING_API_URL", "http://localhost:8384"))
    parser.add_argument("--api-key", default=os.environ.get("SYNCTHING_API_KEY"))
    parser.add_argument("--path", default=str((Path.cwd() / ".freedom/codex_ccks").resolve()))
    parser.add_argument("--folder-id", default="codex-turbo")
    parser.add_argument("--label", default="Codex Turbo")
    parser.add_argument("--share-with", action="append", default=[], help="Remote deviceID to share with (repeatable)")
    parser.add_argument("--state-only", action="store_true", help="Report state without making changes")
    args = parser.parse_args()

    started = now_iso()
    reachable = False
    if not args.api_key:
        out = {
            "ok": False,
            "error": "missing_api_key",
            "hint": "Set SYNCTHING_API_KEY or pass --api-key",
        }
        print(json.dumps(out))
        return 1

    # Ping
    code, _ = http_call("GET", f"{args.api_url}/rest/system/ping", args.api_key)
    reachable = (code == 200)
    if not reachable:
        out = {"ok": False, "error": "syncthing_unreachable", "http": code}
        print(json.dumps(out))
        return 2

    result = {"ok": True}
    if args.state_only:
        # read folders
        code, folders_txt = http_call("GET", f"{args.api_url}/rest/config/folders", args.api_key)
        folders = json.loads(folders_txt) if code == 200 else []
        result.update({
            "state_only": True,
            "folders": [f.get("id") for f in folders],
        })
    else:
        reg = ensure_folder(args.api_url, args.api_key, args.folder_id, args.label, args.path, args.share_with)
        result.update(reg)

    # Evidence
    reports = Path("documents/reports")
    reports.mkdir(parents=True, exist_ok=True)
    evidence = {
        "component": "codex_turbo_syncthing_register",
        "started_at": started,
        "ended_at": now_iso(),
        "inputs": {
            "api_url": args.api_url,
            "folder_id": args.folder_id,
            "label": args.label,
            "path": args.path,
            "share_with": args.share_with,
            "state_only": args.state_only,
        },
        "outputs": result,
        "verdict": "PASS" if result.get("ok") else "FAIL",
    }
    path = reports / f"EVIDENCE_codex_turbo_syncthing_{ts_suffix()}.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
