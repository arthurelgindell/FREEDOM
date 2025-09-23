#!/usr/bin/env python3
"""
List Syncthing devices (device IDs and names) by parsing local config.xml.
No network or API key required. Writes evidence to documents/reports/.

Search paths:
- macOS: ~/Library/Application Support/Syncthing/config.xml
- Unix: ~/.config/syncthing/config.xml

Output: JSON with devices and inferred candidates for Beta by name heuristics.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def ts_suffix() -> str:
    return time.strftime("%Y-%m-%d_%H%M", time.localtime())


def find_config_paths() -> List[Path]:
    home = Path.home()
    paths = [
        home / "Library/Application Support/Syncthing/config.xml",
        home / ".config/syncthing/config.xml",
    ]
    return [p for p in paths if p.exists()]


def list_devices_from_config(cfg_path: Path) -> List[Dict]:
    devices: List[Dict] = []
    try:
        tree = ET.parse(str(cfg_path))
        root = tree.getroot()
        # device elements are usually under root -> device
        for dev in root.findall("device"):
            device_id = dev.get("id") or dev.get("deviceID") or ""
            name = dev.get("name") or ""
            addresses = [a.text or "" for a in dev.findall("address")]
            devices.append({
                "id": device_id,
                "name": name,
                "addresses": addresses,
            })
    except Exception as e:
        devices = [{"error": f"xml_parse_error: {e}"}]
    return devices


def infer_beta_candidates(devices: List[Dict]) -> List[Dict]:
    candidates = []
    for d in devices:
        name = (d.get("name") or "").lower()
        if any(k in name for k in ["beta", "worker", "studio", "node-b", "b-"]):
            candidates.append(d)
    return candidates


def main():
    cfgs = find_config_paths()
    if not cfgs:
        out = {"ok": False, "error": "config_not_found"}
        print(json.dumps(out))
        return 1

    # Use the first available config
    cfg = cfgs[0]
    devices = list_devices_from_config(cfg)
    beta = infer_beta_candidates(devices)
    result = {
        "ok": True,
        "config_path": str(cfg),
        "devices": devices,
        "beta_candidates": beta,
        "timestamp": now_iso(),
    }
    print(json.dumps(result, indent=2))

    # Evidence
    reports = Path("documents/reports")
    reports.mkdir(parents=True, exist_ok=True)
    evidence = {
        "component": "syncthing_devices_from_config",
        "started_at": now_iso(),
        "ended_at": now_iso(),
        "outputs": result,
        "verdict": "PASS" if result.get("ok") else "FAIL",
    }
    path = reports / f"EVIDENCE_syncthing_devices_{ts_suffix()}.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

