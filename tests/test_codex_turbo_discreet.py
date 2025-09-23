#!/usr/bin/env python3
"""
FREEDOM Platform - CodexTurboDiscreet Local Mode Tests
Verifies discreet local store can ensure/add/query/stats without external deps.
Follows Prime Directive: only claim functionality that actually runs.
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

# Allow running from repo root without install
sys.path.append(os.path.abspath("."))

from typing import Optional, Dict
from core.codex_turbo_discreet import codex_turbo_discreet as ctd


def _print_result(name: str, ok: bool, details: Optional[Dict] = None):
    status = "PASS" if ok else "FAIL"
    icon = "✅" if ok else "❌"
    print(f"{icon} {name}: {status}")
    if details:
        print(json.dumps(details, indent=2))


def main():
    # Isolate local store to tests/ path and disable bridge
    test_store = Path("tests/.tmp_codex_ccks")
    if test_store.exists():
        shutil.rmtree(test_store)
    test_store.mkdir(parents=True, exist_ok=True)
    os.environ["CODEX_TURBO_DISCREET_HOME"] = str(test_store)
    os.environ["CODEX_TURBO_BRIDGE"] = "0"

    print("🧪 CodexTurboDiscreet Local Tests")
    print("=" * 40)

    passed = 0
    total = 0

    # 1) ensure()
    total += 1
    res = ctd.ensure(check_syncthing=False, write_evidence=False)
    ok = bool(res.get("ok")) and res["status"].get("local_available") is True and res["status"].get("bridge_available") is False
    _print_result("ensure_local_only", ok, {"status": res.get("status")})
    passed += 1 if ok else 0

    # 2) add()
    total += 1
    add_res = ctd.add("Codex Turbo Discreet test entry", metadata={"test": True}, tags=["codex", "discreet"])
    ok = bool(add_res.get("ok")) and "id" in add_res
    _print_result("add_entry", ok, {"id": add_res.get("id")})
    passed += 1 if ok else 0

    # 3) query()
    total += 1
    q = ctd.query("discreet codex")
    ok = isinstance(q, list) and len(q) >= 1 and q[0].get("score", 0) >= 1.0
    _print_result("query_basic", ok, {"hits": len(q)})
    passed += 1 if ok else 0

    # 4) stats()
    total += 1
    s = ctd.stats()
    ok = s.get("mode") == "local" and s.get("count", 0) >= 1
    _print_result("stats_local", ok, {"count": s.get("count", 0)})
    passed += 1 if ok else 0

    print("-" * 40)
    print(f"Results: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
