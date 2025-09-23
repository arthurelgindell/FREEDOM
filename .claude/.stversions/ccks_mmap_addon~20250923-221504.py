#!/usr/bin/env python3
"""
CCKS Memory-Mapped File Addon
Integrates mmap cache with CCKS for ultra-fast file access
"""

import sys
import os
from pathlib import Path

# Add FREEDOM path
sys.path.insert(0, '/Volumes/DATA/FREEDOM/core')

from mmap_cache import MMapCache
import hashlib
import json

class CCKSMMapIntegration:
    """Integrate memory-mapped files with CCKS."""

    def __init__(self):
        self.mmap_cache = MMapCache(max_files=200)  # Use 200 files
        self.preloaded_dirs = set()

    def preload_freedom_core(self):
        """Preload all FREEDOM core files."""
        if '/Volumes/DATA/FREEDOM/core' not in self.preloaded_dirs:
            count = self.mmap_cache.preload_directory('/Volumes/DATA/FREEDOM/core', '*.py')
            self.preloaded_dirs.add('/Volumes/DATA/FREEDOM/core')
            return count
        return 0

    def preload_freedom_services(self):
        """Preload all FREEDOM service files."""
        if '/Volumes/DATA/FREEDOM/services' not in self.preloaded_dirs:
            count = self.mmap_cache.preload_directory('/Volumes/DATA/FREEDOM/services', '*.py')
            self.preloaded_dirs.add('/Volumes/DATA/FREEDOM/services')
            return count
        return 0

    def get_file_instant(self, filepath: str):
        """Get file contents instantly via mmap."""
        return self.mmap_cache.get_file(filepath)

    def add_to_ccks(self, filepath: str, description: str = None):
        """Add file contents to CCKS with mmap speed."""
        content = self.get_file_instant(filepath)
        if content:
            # Create entry for CCKS
            file_hash = hashlib.md5(content).hexdigest()[:8]
            desc = description or f"File: {Path(filepath).name}"

            # Add to CCKS via command line
            import subprocess
            snippet = content[:500].decode('utf-8', errors='ignore')
            entry = f"{desc} [hash:{file_hash}] - {snippet}"

            result = subprocess.run(
                ['~/.claude/ccks', 'add', entry],
                shell=True,
                capture_output=True,
                text=True
            )
            return file_hash
        return None

    def stats(self):
        """Get combined stats."""
        return {
            "mmap": self.mmap_cache.stats(),
            "preloaded_dirs": list(self.preloaded_dirs)
        }


if __name__ == "__main__":
    print("🚀 CCKS Memory-Mapped Integration")
    print("-" * 40)

    integration = CCKSMMapIntegration()

    # Preload FREEDOM files
    core_count = integration.preload_freedom_core()
    print(f"✅ Preloaded {core_count} core files")

    services_count = integration.preload_freedom_services()
    print(f"✅ Preloaded {services_count} service files")

    # Test instant access
    import time
    test_file = "/Volumes/DATA/FREEDOM/services/rag_chunker/rag_api.py"

    start = time.perf_counter()
    content = integration.get_file_instant(test_file)
    access_time = (time.perf_counter() - start) * 1000

    if content:
        print(f"\n⚡ Instant access to rag_api.py:")
        print(f"  Time: {access_time:.3f}ms")
        print(f"  Size: {len(content):,} bytes")

    # Add to CCKS
    file_hash = integration.add_to_ccks(test_file, "RAG API with mmap speed")
    if file_hash:
        print(f"  Added to CCKS: {file_hash}")

    # Show stats
    stats = integration.stats()
    print(f"\n📊 Integration stats:")
    print(f"  Files cached: {stats['mmap']['files_cached']}")
    print(f"  Total size: {stats['mmap']['total_size_mb']:.2f} MB")
    print(f"  Preloaded: {', '.join(Path(d).name for d in stats['preloaded_dirs'])}")

    print("\n✨ CCKS+mmap integration active!")