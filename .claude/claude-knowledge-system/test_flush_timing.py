#!/usr/bin/env python3
"""Test that CCKS flushes every 2 minutes"""

import time
import subprocess
import json
from datetime import datetime

def get_db_timestamp():
    """Get the last modified time of the database"""
    import os
    from pathlib import Path
    db_path = Path.home() / '.claude' / 'claude-knowledge-system' / 'cache' / 'knowledge.db'
    if db_path.exists():
        return os.path.getmtime(db_path)
    return None

def main():
    print("🧪 Testing 2-minute flush interval...")
    print("=" * 50)

    # Add initial data
    test_data = f"FLUSH_TEST_{datetime.now().isoformat()}"
    subprocess.run(f'~/.claude/ccks add "{test_data}"', shell=True, capture_output=True)
    print(f"✓ Added test data: {test_data[:30]}...")

    # Get initial timestamp
    initial_time = get_db_timestamp()
    if initial_time:
        print(f"✓ Initial DB timestamp: {datetime.fromtimestamp(initial_time).strftime('%H:%M:%S')}")
    else:
        print("❌ Database not found")
        return 1

    # Wait for auto-flush (2 minutes + buffer)
    print("\n⏱️ Waiting 2 minutes for auto-flush...")
    print("   (You can continue working - this runs in background)")

    # Check every 30 seconds
    for i in range(5):  # 2.5 minutes total
        time.sleep(30)
        current_time = get_db_timestamp()
        elapsed = int(time.time() - initial_time)

        if current_time > initial_time:
            print(f"\n✅ AUTO-FLUSH DETECTED after {elapsed} seconds!")
            print(f"   New timestamp: {datetime.fromtimestamp(current_time).strftime('%H:%M:%S')}")

            if elapsed < 150:  # Less than 2.5 minutes
                print("   ✓ Flush interval confirmed: ~2 minutes")
                return 0
            else:
                print("   ⚠️ Flush took longer than expected")
                return 1
        else:
            print(f"   Waiting... ({30 * (i+1)}/150 seconds)")

    print("\n❌ No auto-flush detected after 2.5 minutes")
    return 1

if __name__ == "__main__":
    exit(main())