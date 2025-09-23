#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        cur = conn.execute("PRAGMA compile_options")
        for row in cur.fetchall():
            if "ENABLE_FTS5" in row[0]:
                return True
        # Fallback probe
        try:
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5probe USING fts5(x)")
            conn.execute("DROP TABLE _fts5probe")
            return True
        except Exception:
            return False
    except Exception:
        return False


@dataclass
class SQLiteStore:
    base: Path
    db_path: Path
    fts5: bool = False

    @classmethod
    def create(cls, base: Path) -> "SQLiteStore":
        _ensure_dir(base)
        db_path = base / "codex_turbo.db"
        store = cls(base=base, db_path=db_path)
        store._init_db()
        return store

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        # Pragmas for performance; ignore errors
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")
            conn.execute("PRAGMA cache_size=-20000")  # 20MB
        except Exception:
            pass
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    text TEXT NOT NULL,
                    tags TEXT,
                    metadata TEXT
                )
                """
            )
            self.fts5 = _fts5_available(conn)
            if self.fts5:
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                        text,
                        content='entries',
                        content_rowid='rowid'
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
                      INSERT INTO entries_fts(rowid, text) VALUES (new.rowid, new.text);
                    END;
                    """
                )
                conn.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
                      INSERT INTO entries_fts(entries_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
                    END;
                    """
                )
                conn.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
                      INSERT INTO entries_fts(entries_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
                      INSERT INTO entries_fts(rowid, text) VALUES (new.rowid, new.text);
                    END;
                    """
                )
            conn.commit()
        finally:
            conn.close()

    def ensure(self) -> Dict[str, Any]:
        self._init_db()
        size = self.db_path.stat().st_size if self.db_path.exists() else 0
        count = self.count_entries()
        ram_disk = Path("/Volumes/CCKS_RAM")
        ram_present = ram_disk.exists()
        cache_dir = ram_disk / "cache"
        return {
            "ok": True,
            "db_path": str(self.db_path),
            "db_size": size,
            "count": count,
            "fts5": self.fts5,
            "ram_disk_present": ram_present,
            "ram_cache_dir": str(cache_dir) if ram_present else None,
        }

    def count_entries(self) -> int:
        conn = self._connect()
        try:
            cur = conn.execute("SELECT COUNT(*) FROM entries")
            return int(cur.fetchone()[0])
        except Exception:
            return 0
        finally:
            conn.close()

    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        entry_id = str(uuid.uuid4())
        ts = _now_iso()
        metadata = metadata or {}
        tags = tags or []
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO entries (id, ts, text, tags, metadata) VALUES (?, ?, ?, ?, ?)",
                (
                    entry_id,
                    ts,
                    text,
                    json.dumps(tags, ensure_ascii=False),
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "id": entry_id, "ts": ts, "source": "codex_db"}

    def query(self, text: str, tags: Optional[List[str]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        tags = [t.lower() for t in (tags or [])]
        conn = self._connect()
        rows: List[Tuple[str, str, str, str]] = []
        try:
            if self.fts5 and text.strip():
                # use simple OR query for tokens
                q = " ".join([t for t in text.split() if t])
                cur = conn.execute(
                    """
                    SELECT e.id, e.ts, e.text, e.tags, e.metadata
                    FROM entries e
                    JOIN entries_fts f ON e.rowid = f.rowid
                    WHERE f.text MATCH ?
                    LIMIT ?
                    """,
                    (q, max(1, top_k * 3)),
                )
                rows = cur.fetchall()
            else:
                like = f"%{text}%"
                cur = conn.execute(
                    "SELECT id, ts, text, tags, metadata FROM entries WHERE text LIKE ? LIMIT ?",
                    (like, max(1, top_k * 3)),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        # Tag filter and basic scoring by overlap
        out = []
        q_tokens = set([t.lower() for t in text.split() if t])
        now = time.time()
        for (eid, ts, txt, tags_json, meta_json) in rows:
            try:
                entry_tags = json.loads(tags_json) if tags_json else []
            except Exception:
                entry_tags = []
            if tags and not (set([t.lower() for t in entry_tags]) & set(tags)):
                continue
            # score
            tokens = set([t.lower() for t in txt.split() if t])
            overlap = len(tokens & q_tokens)
            try:
                ts_struct = time.strptime(ts, "%Y-%m-%dT%H:%M:%S")
                age_hours = max(0.0, (now - time.mktime(ts_struct)) / 3600.0)
            except Exception:
                age_hours = 24.0
            recency = max(0.0, 1.0 - min(age_hours / 168.0, 1.0))
            score = overlap + 0.5 * recency
            try:
                metadata = json.loads(meta_json) if meta_json else {}
            except Exception:
                metadata = {}
            out.append({
                "id": eid,
                "text": txt,
                "tags": entry_tags,
                "metadata": metadata,
                "score": round(float(score), 4),
                "source": "codex_db",
            })
        out.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return out[: max(1, top_k)]

    def stats(self) -> Dict[str, Any]:
        size = self.db_path.stat().st_size if self.db_path.exists() else 0
        count = self.count_entries()
        return {
            "mode": "db",
            "db_path": str(self.db_path),
            "db_size": size,
            "count": count,
            "fts5": self.fts5,
        }

