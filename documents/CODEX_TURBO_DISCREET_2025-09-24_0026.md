# Codex Turbo – Local-First Knowledge Helper

Status: ✅ Implemented and verified (local mode)

Prime Directives: Functional reality, local-first, evidence-backed

Capabilities
- ensure: initialize local store, write evidence
- add: append entry with tags/metadata
- query: lexical + recency scoring, optional tag filter
- stats: counts and top terms
- export/import: portable replication (ndjson.gz bundles)

Storage & Paths
- Database: SQLite at `.freedom/codex_ccks/codex_turbo.db` (FTS5 when available)
- File-backed log (fallback): `.freedom/codex_ccks/data.ndjson`
- Evidence: `documents/reports/EVIDENCE_codex_turbo_discreet_*.json`
- RAM cache: auto-detected `/Volumes/CCKS_RAM/cache` if present (for SQLite temp/mmap tuning)

Env Vars
- `CODEX_TURBO_DISCREET_HOME`: override store path
- `CODEX_TURBO_BRIDGE`: set `1` to allow bridge to `~/.claude/ccks`; default disabled for separation
- `SYNCTHING_API_KEY`: used for Syncthing API (registration/health)

CLI Usage (alias: `scripts/codex-turbo`)
```bash
# Ensure + evidence (local only)
scripts/codex-turbo ensure --no-bridge

# Add and query
scripts/codex-turbo add --no-bridge --text "note" --tags codex,notes --meta topic=ccks
scripts/codex-turbo query --no-bridge --text "codex notes" --top-k 5

# Stats
scripts/codex-turbo stats --no-bridge

# Export/import bundles
scripts/codex-turbo export --no-bridge
scripts/codex-turbo import --no-bridge --file .freedom/codex_ccks/export/bundle_<ts>.ndjson.gz
```

Python API
```python
from core.codex_turbo_discreet import ensure, add, query, stats, export, import_
ensure()
add("text", metadata={"k":"v"}, tags=["codex"]) 
hits = query("codex discreet", top_k=5)
print(stats())
export()
import_(".freedom/codex_ccks/export/bundle_<ts>.ndjson.gz")
```

Testing
- `python3 tests/test_codex_turbo_discreet.py` (local-only)
- `python3 tests/test_codex_turbo_discreet_export_import.py` (CLI export/import)
- Facilities: `python3 scripts/diagnose_ccks_facilities.py`

Syncthing
- Register a Syncthing folder for Codex Turbo (id: `codex-turbo`) and optionally share with Beta:
```bash
SYNCTHING_API_KEY=<key> \
python3 scripts/syncthing_register_codex_turbo.py \
  --path "$(pwd)/.freedom/codex_ccks" \
  --folder-id codex-turbo \
  --label "Codex Turbo" \
  --share-with <BETA_DEVICE_ID>
```
- Health + facilities diagnostics:
```bash
python3 scripts/diagnose_ccks_facilities.py
```

Design Notes
- SQLite DB used by default (CCKS-like), with FTS search when available; ndjson is a fallback log
- Bridge disabled by default to keep separation from cloud instance (enable with `CODEX_TURBO_BRIDGE=1`)
- Export/import enable manual or scheduled replication without Syncthing
- Syncthing integration is opt-in and evidence-backed
