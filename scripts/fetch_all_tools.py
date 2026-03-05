#!/usr/bin/env python3
"""
Auto-detect installed tools and run their fetch scripts.
This script automatically detects which tools are installed and runs their
corresponding fetch scripts to collect usage data.
"""

import os
import subprocess
import sys
from pathlib import Path


def find_openclaw_sessions() -> bool:
    """Check if OpenClaw sessions directory exists."""
    home = Path.home()
    agents_dir = home / ".openclaw" / "agents"

    if not agents_dir.is_dir():
        return False

    for agent_dir in agents_dir.iterdir():
        if agent_dir.is_dir():
            sessions_dir = agent_dir / "sessions"
            if sessions_dir.is_dir():
                jsonl_files = list(sessions_dir.glob("*.jsonl"))
                if jsonl_files:
                    return True

    return False


def find_claude_history() -> bool:
    """Check if Claude history exists (in typical locations)."""
    # Claude Desktop stores history in various locations
    potential_paths = [
        Path.home() / ".claude",
        Path.home() / ".config" / "Claude",
        Path.home() / "Library" / "Application Support" / "Claude",  # macOS
        Path.home() / "AppData" / "Roaming" / "Claude",  # Windows
    ]

    for path in potential_paths:
        if path.is_dir():
            # Look for history files
            for ext in ["*.json", "*.jsonl", "*.db"]:
                if list(path.rglob(ext)):
                    return True

    return False


def find_qwen_history() -> bool:
    """Check if Qwen history exists."""
    # Qwen Desktop typically stores data here
    potential_paths = [
        Path.home() / ".qwen",
        Path.home() / ".config" / "Qwen",
        Path.home() / "Library" / "Application Support" / "Qwen",  # macOS
        Path.home() / "AppData" / "Roaming" / "Qwen",  # Windows
    ]

    for path in potential_paths:
        if path.is_dir():
            # Look for any data files
            if list(path.rglob("*.json")) or list(path.rglob("*.jsonl")):
                return True

    return False


def run_fetch_script(script_name: str, **kwargs) -> bool:
    """Run a fetch script with the given arguments."""
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        print(f"Warning: Script not found: {script_name}")
        return False

    cmd = [sys.executable, str(script_path)]
    for key, value in kwargs.items():
        cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✓ {script_name}: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ {script_name}: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ {script_name}: Timeout (60s)")
        return False
    except Exception as e:
        print(f"✗ {script_name}: {e}")
        return False


def main():
    hostname = os.environ.get("UPLOAD_HOSTNAME", "localhost")
    days = int(os.environ.get("FETCH_DAYS", "1"))

    print(f"=== Auto-detecting tools (hostname: {hostname}, days: {days}) ===\n")

    collected = 0
    errors = 0

    # Check for OpenClaw
    if find_openclaw_sessions():
        print("Detected: OpenClaw")
        if run_fetch_script("fetch_openclaw_messages.py", hostname=hostname, days=days):
            collected += 1
        else:
            errors += 1
    else:
        print("Not detected: OpenClaw (no session files)")

    # Check for Claude (claude)
    # Note: Claude Desktop doesn't have a standard CLI fetch script yet
    # For now, we skip it unless a fetch_claude.py script exists and is configured
    if find_claude_history():
        print("Detected: Claude")
        if run_fetch_script("fetch_claude.py", hostname=hostname, days=days):
            collected += 1
        else:
            errors += 1
    else:
        print("Not detected: Claude")

    # Check for Qwen (qwen)
    if find_qwen_history():
        print("Detected: Qwen")
        if run_fetch_script("fetch_qwen.py", hostname=hostname, days=days):
            collected += 1
        else:
            errors += 1
    else:
        print("Not detected: Qwen")

    print(f"\n=== Summary ===")
    print(f"Tools collected: {collected}")
    if errors > 0:
        print(f"Errors: {errors}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
