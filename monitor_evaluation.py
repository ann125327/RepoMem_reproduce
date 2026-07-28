#!/usr/bin/env python3
"""
Monitor script for batch evaluation progress
"""
import os
import json
import time
from datetime import datetime

OUTPUT_DIR = "results/locagent_verified_batch_continue"
LOG_FILE = os.path.join(OUTPUT_DIR, "localize.log")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "loc_outputs.jsonl")

def get_progress():
    """Get current progress from log file"""
    if not os.path.exists(LOG_FILE):
        return None

    with open(LOG_FILE, 'r') as f:
        content = f.read()

    # Count setup attempts
    setup_count = content.count("setup localize")

    # Count successes
    success_count = content.count("succeed")

    # Count failures
    fail_count = content.count("failed")

    # Check if running
    is_running = "begin localizing" in content

    return {
        "setup_count": setup_count,
        "success_count": success_count,
        "fail_count": fail_count,
        "is_running": is_running
    }

def get_results():
    """Get results from output file"""
    if not os.path.exists(OUTPUT_FILE):
        return []

    results = []
    with open(OUTPUT_FILE, 'r') as f:
        for line in f:
            data = json.loads(line)
            results.append({
                "instance_id": data["instance_id"],
                "files_found": len(data.get("found_files", [[]])[0]),
                "modules_found": len(data.get("found_modules", [[]])[0])
            })
    return results

def main():
    print(f"Monitoring batch evaluation...")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Press Ctrl+C to stop monitoring\n")

    try:
        while True:
            progress = get_progress()
            results = get_results()

            # Clear screen (optional)
            # os.system('cls' if os.name == 'nt' else 'clear')

            print(f"\n{'='*60}")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")

            if progress:
                print(f"\nProgress:")
                print(f"  Setup attempts: {progress['setup_count']}")
                print(f"  Successful: {progress['success_count']}")
                print(f"  Failed: {progress['fail_count']}")
                print(f"  Currently running: {'Yes' if progress['is_running'] else 'No'}")

            if results:
                print(f"\nResults ({len(results)} samples completed):")
                for r in results:
                    print(f"  {r['instance_id']}: {r['files_found']} files, {r['modules_found']} modules")

            # Check log file size
            if os.path.exists(LOG_FILE):
                size = os.path.getsize(LOG_FILE) / 1024
                print(f"\nLog file size: {size:.1f} KB")

                # Show last few lines
                with open(LOG_FILE, 'r') as f:
                    lines = f.readlines()[-5:]
                print(f"\nLast 5 log lines:")
                for line in lines:
                    print(f"  {line.rstrip()}")

            time.sleep(30)  # Update every 30 seconds

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    main()