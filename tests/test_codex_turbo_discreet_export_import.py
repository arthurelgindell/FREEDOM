#!/usr/bin/env python3
"""
CodexTurboDiscreet export/import tests using CLI to isolate stores.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, env=None):
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def main():
    repo_root = Path(__file__).resolve().parent.parent
    cli = str(repo_root / "scripts/codex-turbo-discreet")

    store_a = repo_root / "tests/.tmp_codex_ccks_a"
    store_b = repo_root / "tests/.tmp_codex_ccks_b"
    for p in (store_a, store_b):
        if p.exists():
            shutil.rmtree(p)

    env_a = os.environ.copy()
    env_a["CODEX_TURBO_DISCREET_HOME"] = str(store_a)
    env_a["CODEX_TURBO_BRIDGE"] = "0"

    env_b = os.environ.copy()
    env_b["CODEX_TURBO_DISCREET_HOME"] = str(store_b)
    env_b["CODEX_TURBO_BRIDGE"] = "0"

    # ensure A
    rc, out, err = run([cli, "ensure", "--no-bridge"], env=env_a)
    if rc != 0:
        print("ensure A failed", out, err)
        return 1

    # add two entries to A
    rc, out, err = run([cli, "add", "--no-bridge", "--text", "A note one", "--tags", "codex"], env=env_a)
    if rc != 0:
        print("add 1 failed", out, err)
        return 1
    rc, out, err = run([cli, "add", "--no-bridge", "--text", "A note two", "--tags", "discreet"], env=env_a)
    if rc != 0:
        print("add 2 failed", out, err)
        return 1

    # export from A
    rc, out, err = run([cli, "export", "--no-bridge"], env=env_a)
    if rc != 0:
        print("export failed", out, err)
        return 1
    exp = json.loads(out)
    bundle = exp.get("path")
    if not bundle or not Path(bundle).exists():
        print("export bundle missing", out)
        return 1

    # import into B
    rc, out, err = run([cli, "ensure", "--no-bridge"], env=env_b)
    if rc != 0:
        print("ensure B failed", out, err)
        return 1
    rc, out, err = run([cli, "import", "--no-bridge", "--file", bundle], env=env_b)
    if rc != 0:
        print("import failed", out, err)
        return 1
    imp = json.loads(out)
    if imp.get("imported", 0) < 2:
        print("imported less than expected", out)
        return 1

    # re-import into B to test dedupe
    rc, out, err = run([cli, "import", "--no-bridge", "--file", bundle], env=env_b)
    if rc != 0:
        print("re-import failed", out, err)
        return 1
    imp2 = json.loads(out)
    if imp2.get("deduped", 0) < 2:
        print("dedupe not detected", out)
        return 1

    print("✅ export/import tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

