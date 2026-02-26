#!/usr/bin/env python3
"""
AI Token Usage - Claude Fetcher

Fetches daily token usage from Claude Code local JSONL logs.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add shared directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
shared_dir = os.path.join(script_dir, 'shared')
if shared_dir not in sys.path:
    sys.path.insert(0, script_dir)
from shared import db


def parse_timestamp(ts_str: str) -> str:
    """Extract date from ISO timestamp."""
    if not ts_str:
        return "unknown"
    try:
        if ts_str.endswith("Z"):
            if "." in ts_str:
                base, rest = ts_str.rsplit(".", 1)
                ms = rest.rstrip("Z")
                ms = ms[:3].ljust(3, "0")
                dt = datetime.strptime(f"{base}.{ms}Z", "%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
        else:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "unknown"


def extract_tokens_from_entry(entry: dict) -> dict:
    """Extract token counts from a Claude Code log entry."""
    result = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "model": None,
    }

    if entry.get("type") == "assistant":
        msg = entry.get("message", {})
        if isinstance(msg, dict):
            result["model"] = msg.get("model")

    usage = None
    if "usage" in entry:
        usage = entry["usage"]
    elif entry.get("type") == "assistant" and "message" in entry:
        msg = entry["message"]
        if isinstance(msg, dict):
            usage = msg.get("usage")

    if usage and isinstance(usage, dict):
        result["input_tokens"] = usage.get("input_tokens", 0)
        result["output_tokens"] = usage.get("output_tokens", 0)
        result["cache_read_tokens"] = usage.get("cache_read_input_tokens", 0)
        result["cache_creation_tokens"] = usage.get("cache_creation_input_tokens", 0)

    return result


def process_jsonl_file(filepath: Path) -> Dict[str, dict]:
    """Process a single JSONL file and return daily token aggregates."""
    daily = defaultdict(lambda: {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "models_used": set(),
    })

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    continue

                ts = entry.get("timestamp")
                if not ts:
                    continue

                date_key = parse_timestamp(ts)
                tokens = extract_tokens_from_entry(entry)

                if sum([
                    tokens["input_tokens"],
                    tokens["output_tokens"],
                    tokens["cache_read_tokens"],
                    tokens["cache_creation_tokens"],
                ]) == 0:
                    continue

                daily[date_key]["input_tokens"] += tokens["input_tokens"]
                daily[date_key]["output_tokens"] += tokens["output_tokens"]
                daily[date_key]["cache_read_tokens"] += tokens["cache_read_tokens"]
                daily[date_key]["cache_creation_tokens"] += tokens["cache_creation_tokens"]

                if tokens["model"]:
                    daily[date_key]["models_used"].add(tokens["model"])

            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    return dict(daily)


def find_claude_project_dir() -> Optional[Path]:
    """Find the Claude project directory."""
    project_dirs = [
        Path.home() / ".claude" / "projects" / "-Users-rhuang-workspace",
        Path.home() / ".config" / "claude" / "projects",
    ]

    for d in project_dirs:
        if d.is_dir():
            return d

    return None


def fetch_and_save(days: int = 7, project_dir: Optional[Path] = None) -> bool:
    """
    Fetch Claude usage and save to database.

    Args:
        days: Number of days to look back
        project_dir: Optional specific project directory

    Returns:
        True if successful, False otherwise
    """
    # Add shared directory to path for db module
    script_dir = os.path.dirname(os.path.abspath(__file__))
    shared_dir = os.path.join(script_dir, 'shared')
    if shared_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from shared import db

    if project_dir is None:
        project_dir = find_claude_project_dir()

    if not project_dir:
        print("Error: Cannot find Claude project directory.")
        return False

    jsonl_files = list(project_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"Error: No .jsonl files found in {project_dir}")
        return False

    # Aggregate across all files
    aggregated = defaultdict(lambda: {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "models_used": set(),
    })

    for f in jsonl_files:
        daily = process_jsonl_file(f)
        for date, stats in daily.items():
            for key in ["input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"]:
                aggregated[date][key] += stats[key]
            aggregated[date]["models_used"].update(stats["models_used"])

    # Filter by date range
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days-1)).strftime("%Y-%m-%d")

    saved = 0
    for date, stats in aggregated.items():
        if start_date <= date <= today:
            total = (
                stats["input_tokens"]
                + stats["output_tokens"]
                + stats["cache_read_tokens"]
                + stats["cache_creation_tokens"]
            )

            if db.save_usage(
                date=date,
                tool_name="claude",
                tokens_used=total,
                input_tokens=stats["input_tokens"],
                output_tokens=stats["output_tokens"],
                cache_tokens=stats["cache_read_tokens"] + stats["cache_creation_tokens"],
                models_used=sorted(stats["models_used"])
            ):
                saved += 1
            print(f"  {date}: {total:,} tokens")

    print(f"\nSaved {saved} days of Claude usage data")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch Claude token usage')
    parser.add_argument('--days', type=int, default=7, help='Number of days')
    parser.add_argument('--project', help='Specific project directory')
    args = parser.parse_args()

    db.init_database()
    success = fetch_and_save(days=args.days, project_dir=Path(args.project) if args.project else None)
    sys.exit(0 if success else 1)
