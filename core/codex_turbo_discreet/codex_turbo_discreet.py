#!/usr/bin/env python3
"""
CodexTurboDiscreet – discreet, local-first knowledge helper for Codex.

Follows FREEDOM Prime Directives:
- Functional reality: works standalone in local mode without external deps.
- Optional bridge to ~/.claude/ccks if present; otherwise falls back to local store.
- Evidence generation on ensure() in documents/reports/.

Capabilities:
- is_turbo_available() -> (bool, status_dict)
- ensure(check_syncthing: bool = False, write_evidence: bool = True) -> dict
- add(text: str, metadata: dict | None = None, tags: list[str] | None = None) -> dict
- query(text: str, tags: list[str] | None = None, top_k: int = 5) -> list[dict]
- stats() -> dict

Environment variables:
- CODEX_TURBO_DISCREET_HOME: override local store path (default .freedom/codex_ccks)
- CODEX_TURBO_BRIDGE: "1" to allow bridging to ~/.claude/ccks (default 1). "0" disables.
- SYNCTHING_API_KEY: optional; used only when ensure(check_syncthing=True).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
import gzip
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Prefer SQLite store (replicates CCKS Turbo DB characteristic) with local ndjson fallback
try:
    from .sqlite_store import SQLiteStore
    _HAS_SQLITE = True
except Exception:
    _HAS_SQLITE = False


# -----------------------------
# Constants and configuration
# -----------------------------

DEFAULT_HOME = Path(os.environ.get("CODEX_TURBO_DISCREET_HOME", ".freedom/codex_ccks"))
BRIDGE_BIN = Path.home() / ".claude/ccks"
BRIDGE_STATUS = Path.home() / ".claude/ccks_turbo_status.json"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _timestamp_suffix() -> str:
    return time.strftime("%Y-%m-%d_%H%M", time.localtime())


def _safe_json_loads(s: str) -> Optional[dict]:
    try:
        return json.loads(s)
    except Exception:
        return None


def _read_json_file(path: Path) -> Optional[dict]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def _git_commit_short() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except Exception:
        return "unknown"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^A-Za-z0-9_]+", text.lower()) if t]


@dataclass
class LocalStore:
    base: Path

    @property
    def manifest(self) -> Path:
        return self.base / "manifest.json"

    @property
    def data(self) -> Path:
        return self.base / "data.ndjson"

    @property
    def index(self) -> Path:
        return self.base / "index.json"

    def ensure(self) -> Dict[str, Any]:
        _ensure_dir(self.base)
        if not self.manifest.exists():
            self.manifest.write_text(json.dumps({
                "component": "codex_turbo_discreet",
                "created_at": _now_iso(),
                "version": 1
            }, indent=2), encoding="utf-8")
        if not self.data.exists():
            self.data.write_text("", encoding="utf-8")
        if not self.index.exists():
            self.index.write_text(json.dumps({"terms": {}, "count": 0}, indent=2), encoding="utf-8")
        return {"ok": True, "path": str(self.base)}

    def _load_index(self) -> Dict[str, Any]:
        d = _read_json_file(self.index)
        if not d:
            d = {"terms": {}, "count": 0}
        return d

    def _save_index(self, idx: Dict[str, Any]) -> None:
        self.index.write_text(json.dumps(idx, indent=2), encoding="utf-8")

    def _append_data(self, obj: Dict[str, Any]) -> None:
        with self.data.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        metadata = metadata or {}
        tags = tags or []
        entry_id = str(uuid.uuid4())
        ts = _now_iso()
        tokens = _tokenize(text)
        obj = {
            "id": entry_id,
            "ts": ts,
            "text": text,
            "tokens": tokens,
            "tags": tags,
            "metadata": metadata,
            "source": "codex_local"
        }
        self._append_data(obj)

        idx = self._load_index()
        terms = idx.get("terms", {})
        for t in set(tokens):
            # Maintain small posting lists; only counts for simplicity
            terms[t] = terms.get(t, 0) + 1
        idx["terms"] = terms
        idx["count"] = int(idx.get("count", 0)) + 1
        self._save_index(idx)
        return {"ok": True, "id": entry_id, "ts": ts}

    def stats(self) -> Dict[str, Any]:
        idx = self._load_index()
        count = int(idx.get("count", 0))
        top_terms = sorted(idx.get("terms", {}).items(), key=lambda kv: kv[1], reverse=True)[:10]
        last_ts = None
        try:
            with self.data.open("r", encoding="utf-8") as f:
                for line in f:
                    pass
                if line:
                    last = json.loads(line)
                    last_ts = last.get("ts")
        except Exception:
            pass
        return {
            "mode": "local",
            "count": count,
            "top_terms": top_terms,
            "last_ts": last_ts,
            "path": str(self.base)
        }

    def _iter_entries(self):
        if not self.data.exists():
            return
        with self.data.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = _safe_json_loads(line)
                if obj:
                    yield obj

    def query(self, text: str, tags: Optional[List[str]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        q_tokens = _tokenize(text)
        tag_filter = set([t.lower() for t in (tags or [])])
        results: List[Tuple[float, Dict[str, Any]]] = []
        now = time.time()

        for obj in self._iter_entries() or []:
            if tag_filter:
                obj_tags = set([str(t).lower() for t in obj.get("tags", [])])
                if not (obj_tags & tag_filter):
                    continue
            tokens = obj.get("tokens", [])
            # score: keyword overlap + recency boost
            overlap = len(set(tokens) & set(q_tokens))
            # recency in hours decay
            try:
                ts_struct = time.strptime(obj.get("ts", ""), "%Y-%m-%dT%H:%M:%S")
                age_hours = max(0.0, (now - time.mktime(ts_struct)) / 3600.0)
            except Exception:
                age_hours = 24.0
            recency = max(0.0, 1.0 - min(age_hours / 168.0, 1.0))  # within a week gets boost
            score = overlap + 0.5 * recency
            if score > 0:
                results.append((score, obj))

        results.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, obj in results[: max(1, top_k)]:
            out.append({
                "id": obj.get("id"),
                "text": obj.get("text"),
                "tags": obj.get("tags", []),
                "metadata": obj.get("metadata", {}),
                "score": round(float(score), 4),
                "source": obj.get("source", "codex_local")
            })
        return out

    def _existing_ids(self) -> set:
        ids = set()
        for obj in self._iter_entries() or []:
            eid = obj.get("id")
            if eid:
                ids.add(eid)
        return ids

    def export_bundle(self, out_dir: Optional[Path] = None) -> Dict[str, Any]:
        out_dir = out_dir or (self.base / "export")
        _ensure_dir(out_dir)
        count = 0
        ts = _timestamp_suffix()
        out_path = out_dir / f"bundle_{ts}.ndjson.gz"
        with gzip.open(out_path, "wt", encoding="utf-8") as gz:
            for obj in self._iter_entries() or []:
                gz.write(json.dumps(obj, ensure_ascii=False) + "\n")
                count += 1
        return {"ok": True, "path": str(out_path), "count": count}

    def import_bundle(self, file_path: Path) -> Dict[str, Any]:
        # Detect gzip vs plain
        fp = Path(file_path)
        if not fp.exists():
            return {"ok": False, "error": "file_not_found", "path": str(file_path)}

        existed_ids = self._existing_ids()
        imported = 0
        deduped = 0

        # Accumulate index updates for new rows
        idx = self._load_index()
        terms = idx.get("terms", {})
        count = int(idx.get("count", 0))

        def _handle_line(line: str):
            nonlocal imported, deduped, count, terms
            line = line.strip()
            if not line:
                return
            obj = _safe_json_loads(line)
            if not obj:
                return
            eid = obj.get("id")
            if eid in existed_ids:
                deduped += 1
                return
            # Append to data
            self._append_data(obj)
            existed_ids.add(eid)
            imported += 1
            # Update index counts
            for t in set(obj.get("tokens", [])):
                terms[t] = terms.get(t, 0) + 1
            count += 1

        try:
            if fp.suffix == ".gz":
                with gzip.open(fp, "rt", encoding="utf-8") as gz:
                    for line in gz:
                        _handle_line(line)
            else:
                with fp.open("r", encoding="utf-8") as f:
                    for line in f:
                        _handle_line(line)
            # Save updated index
            idx["terms"] = terms
            idx["count"] = count
            self._save_index(idx)
            return {"ok": True, "imported": imported, "deduped": deduped}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# -----------------------------
# Bridge helpers (~/.claude/ccks)
# -----------------------------

def _bridge_available() -> Tuple[bool, Dict[str, Any]]:
    bridge_allowed = os.environ.get("CODEX_TURBO_BRIDGE", "0") != "0"
    if not bridge_allowed:
        return False, {"allowed": False}
    available = BRIDGE_BIN.exists() and os.access(BRIDGE_BIN, os.X_OK)
    status = _read_json_file(BRIDGE_STATUS) or {}
    return available, {"allowed": True, "bin": str(BRIDGE_BIN), "status_file": str(BRIDGE_STATUS), "status": status}


def _bridge_run(args: List[str], timeout: int = 10) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(args, capture_output=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.decode(errors="ignore"), proc.stderr.decode(errors="ignore")
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:
        return 1, "", str(e)


# -----------------------------
# Public API
# -----------------------------

def is_turbo_available() -> Tuple[bool, Dict[str, Any]]:
    bridge_ok, bridge_info = _bridge_available()
    local_ok = False
    status_local: Dict[str, Any] = {}
    if _HAS_SQLITE:
        try:
            db = SQLiteStore.create(DEFAULT_HOME)
            status_local = db.ensure()
            local_ok = bool(status_local.get("ok"))
        except Exception:
            local_ok = False
    if not local_ok:
        local = LocalStore(DEFAULT_HOME)
        local_ok = local.ensure().get("ok", False)
        status_local = {"path": str(DEFAULT_HOME), "fallback": True}
    return (bridge_ok or local_ok), {
        "bridge_available": bridge_ok,
        "local_available": local_ok,
        "local_path": str(DEFAULT_HOME),
        "bridge": bridge_info,
        "db": status_local,
    }


def ensure(check_syncthing: bool = False, write_evidence: bool = True) -> Dict[str, Any]:
    ok, status = is_turbo_available()

    syncthing = {"checked": False, "available": False}
    if check_syncthing:
        syncthing["checked"] = True
        # Only attempt a harmless /rest/ping if explicitly requested and API key present
        api_key = os.environ.get("SYNCTHING_API_KEY")
        if api_key:
            try:
                # Avoid adding requests; use curl if available, otherwise skip
                rc, out, _ = _bridge_run(["curl", "-s", "-H", f"X-API-Key: {api_key}", "http://localhost:8384/rest/system/ping"], timeout=3)
                if rc == 0 and "pong" in out.lower():
                    syncthing["available"] = True
            except Exception:
                pass

    result = {
        "ok": ok,
        "status": status,
        "syncthing": syncthing,
        "timestamp": _now_iso(),
    }

    if write_evidence:
        try:
            reports = Path("documents/reports")
            _ensure_dir(reports)
            evidence = {
                "component": "codex_turbo_discreet",
                "git_commit": _git_commit_short(),
                "build_hash": "n/a",
                "started_at": _now_iso(),
                "ended_at": _now_iso(),
                "inputs_sample": {"check_syncthing": check_syncthing},
                "outputs_sample": {"status": {"bridge_available": status.get("bridge_available"), "local_available": status.get("local_available")}},
                "metrics": {},
                "verdict": "PASS" if ok else "FAIL",
            }
            path = reports / f"EVIDENCE_codex_turbo_discreet_{_timestamp_suffix()}.json"
            path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            result["evidence_path"] = str(path)
        except Exception:
            # Stay discreet: no hard failure on evidence write
            pass

    return result


def add(text: str, metadata: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    # Prefer bridge if available and allowed
    bridge_ok, _ = _bridge_available()
    if bridge_ok:
        # Attempt bridge add
        args = [str(BRIDGE_BIN), "add", text]
        rc, out, err = _bridge_run(args, timeout=10)
        if rc == 0:
            data = _safe_json_loads(out)
            if data:
                return {"ok": True, "bridge": True, "result": data}
            # non-JSON: still consider success with raw echo
            return {"ok": True, "bridge": True, "result": {"raw": out.strip()}}
        # Fall back to local if bridge fails silently

    # Prefer SQLite DB if available
    if _HAS_SQLITE:
        try:
            db = SQLiteStore.create(DEFAULT_HOME)
            db.ensure()
            return db.add(text=text, metadata=metadata, tags=tags)
        except Exception:
            pass
    store = LocalStore(DEFAULT_HOME)
    store.ensure()
    return store.add(text=text, metadata=metadata, tags=tags)


def query(text: str, tags: Optional[List[str]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
    bridge_ok, _ = _bridge_available()
    if bridge_ok:
        # Prefer bridge query
        args = [str(BRIDGE_BIN), "query", text]
        rc, out, err = _bridge_run(args, timeout=15)
        if rc == 0:
            data = _safe_json_loads(out)
            if isinstance(data, list):
                # normalize
                for d in data:
                    d.setdefault("source", "ccks")
                return data[: max(1, top_k)]
            elif isinstance(data, dict):
                return [data]
            else:
                # non-JSON fallback: wrap raw text
                return [{"text": out.strip(), "source": "ccks", "score": 0.0}]
        # else: fall through to local if bridge fails

    if _HAS_SQLITE:
        try:
            db = SQLiteStore.create(DEFAULT_HOME)
            db.ensure()
            return db.query(text=text, tags=tags, top_k=top_k)
        except Exception:
            pass
    store = LocalStore(DEFAULT_HOME)
    store.ensure()
    return store.query(text=text, tags=tags, top_k=top_k)


def stats() -> Dict[str, Any]:
    bridge_ok, _ = _bridge_available()
    if bridge_ok:
        args = [str(BRIDGE_BIN), "stats"]
        rc, out, err = _bridge_run(args, timeout=10)
        if rc == 0:
            data = _safe_json_loads(out)
            if isinstance(data, dict):
                data.setdefault("mode", "bridge")
                return data
            return {"mode": "bridge", "raw": out.strip()}

    if _HAS_SQLITE:
        try:
            db = SQLiteStore.create(DEFAULT_HOME)
            db.ensure()
            return db.stats()
        except Exception:
            pass
    store = LocalStore(DEFAULT_HOME)
    store.ensure()
    return store.stats()


def export(out_dir: Optional[str] = None) -> Dict[str, Any]:
    store = LocalStore(DEFAULT_HOME)
    store.ensure()
    out = store.export_bundle(Path(out_dir) if out_dir else None)
    return out


def import_(file_path: str) -> Dict[str, Any]:
    store = LocalStore(DEFAULT_HOME)
    store.ensure()
    return store.import_bundle(Path(file_path))


# If invoked directly, provide a tiny demo for functional proof
if __name__ == "__main__":
    # Minimal smoke: ensure, add, query, stats without printing sensitive info
    res = ensure(check_syncthing=False, write_evidence=True)
    _ = add("CodexTurboDiscreet initial entry for local verification.", {"init": True}, tags=["codex", "discreet"])
    q = query("CodexTurboDiscreet verification", top_k=3)
    s = stats()
    # Print compact JSON
    print(json.dumps({
        "ensure_ok": res.get("ok"),
        "query_hits": len(q),
        "mode": s.get("mode"),
        "count": s.get("count", 0)
    }))
