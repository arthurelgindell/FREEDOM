#!/usr/bin/env python3
"""
Memory-mapped file cache for ultra-fast file access.
Uses mmap to treat files as memory regions for zero-copy operations.
"""

import mmap
import os
import hashlib
from pathlib import Path
from typing import Dict, Optional
import time

class MMapCache:
    """Memory-mapped file cache for instant file access."""

    def __init__(self, max_files: int = 100):
        self.max_files = max_files
        self.cache: Dict[str, mmap.mmap] = {}
        self.access_times: Dict[str, float] = {}

    def get_file(self, filepath: str) -> Optional[bytes]:
        """Get file contents via memory mapping."""
        filepath = str(Path(filepath).resolve())

        # Check if already mapped
        if filepath in self.cache:
            self.access_times[filepath] = time.time()
            return self.cache[filepath][:]

        # Evict oldest if at capacity
        if len(self.cache) >= self.max_files:
            oldest = min(self.access_times.items(), key=lambda x: x[1])
            self._evict(oldest[0])

        # Map new file
        try:
            with open(filepath, 'rb') as f:
                # Memory map the file
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                self.cache[filepath] = mm
                self.access_times[filepath] = time.time()
                return mm[:]
        except Exception as e:
            print(f"Error mapping {filepath}: {e}")
            return None

    def _evict(self, filepath: str):
        """Remove file from cache."""
        if filepath in self.cache:
            self.cache[filepath].close()
            del self.cache[filepath]
            del self.access_times[filepath]

    def preload_directory(self, directory: str, pattern: str = "*.py"):
        """Preload all matching files from directory."""
        path = Path(directory)
        files_loaded = 0

        for file_path in path.rglob(pattern):
            if files_loaded >= self.max_files:
                break
            if file_path.is_file():
                self.get_file(str(file_path))
                files_loaded += 1

        return files_loaded

    def stats(self):
        """Get cache statistics."""
        total_size = sum(mm.size() for mm in self.cache.values())
        return {
            "files_cached": len(self.cache),
            "total_size_mb": total_size / (1024 * 1024),
            "max_files": self.max_files
        }

    def close(self):
        """Close all memory mappings."""
        for mm in self.cache.values():
            mm.close()
        self.cache.clear()
        self.access_times.clear()


if __name__ == "__main__":
    # Test the memory-mapped cache
    import sys

    print("🚀 Memory-Mapped File Cache Test")
    print("-" * 40)

    cache = MMapCache(max_files=50)

    # Preload FREEDOM core files
    loaded = cache.preload_directory("/Volumes/DATA/FREEDOM/core", "*.py")
    print(f"✅ Preloaded {loaded} Python files from core/")

    # Show stats
    stats = cache.stats()
    print(f"📊 Cache stats: {stats}")

    # Test access speed
    test_file = "/Volumes/DATA/FREEDOM/README.md"

    # First access (cold)
    start = time.perf_counter()
    content = cache.get_file(test_file)
    cold_time = (time.perf_counter() - start) * 1000

    # Second access (warm)
    start = time.perf_counter()
    content = cache.get_file(test_file)
    warm_time = (time.perf_counter() - start) * 1000

    if content:
        print(f"\n⚡ Access times for README.md:")
        print(f"  Cold: {cold_time:.3f}ms")
        print(f"  Warm: {warm_time:.3f}ms")
        print(f"  Speedup: {cold_time/warm_time:.1f}x")
        print(f"  Size: {len(content):,} bytes")

    cache.close()
    print("\n✨ Memory-mapped cache ready for integration!")