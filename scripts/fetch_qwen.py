#!/usr/bin/env python3
"""
AI Token Usage - Qwen Fetcher

Fetches daily token usage from Qwen local JSONL logs.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

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
    """Extract token counts from a Qwen log entry."""
    result = {
        "prompt_tokens": 0,
        "candidates_tokens": 0,
        "thoughts_tokens": 0,
        "cached_tokens": 0,
        "total_tokens": 0,
        "model": None,
    }

    if entry.get("type") == "assistant":
        result["model"] = entry.get("model")

    usage = entry.get("usageMetadata", {})
    if isinstance(usage, dict):
        result["prompt_tokens"] = usage.get("promptTokenCount", 0)
        result["candidates_tokens"] = usage.get("candidatesTokenCount", 0)
        result["thoughts_tokens"] = usage.get("thoughtsTokenCount", 0)
        result["cached_tokens"] = usage.get("cachedContentTokenCount", 0)
        result["total_tokens"] = usage.get("totalTokenCount", 0)

    return result


def process_jsonl_file(filepath: Path) -> Dict[str, dict]:
    """Process a single JSONL file and return daily token aggregates."""
    daily = defaultdict(lambda: {
        "prompt_tokens": 0,
        "candidates_tokens": 0,
        "thoughts_tokens": 0,
        "cached_tokens": 0,
        "total_tokens": 0,
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

                if tokens["total_tokens"] == 0:
                    continue

                daily[date_key]["prompt_tokens"] += tokens["prompt_tokens"]
                daily[date_key]["candidates_tokens"] += tokens["candidates_tokens"]
                daily[date_key]["thoughts_tokens"] += tokens["thoughts_tokens"]
                daily[date_key]["cached_tokens"] += tokens["cached_tokens"]
                daily[date_key]["total_tokens"] += tokens["total_tokens"]

                if tokens["model"]:
                    daily[date_key]["models_used"].add(tokens["model"])

            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    return dict(daily)


def find_qwen_project_dir() -> Optional[Path]:
    """Find the Qwen project directory."""
    project_dirs = [
        Path.home() / ".qwen" / "projects" / "-Users-rhuang-workspace" / "chats",
        Path.home() / ".qwen" / "projects",
    ]

    for d in project_dirs:
        if d.is_dir():
            return d

    return None


def fetch_and_save(days: int = 7, project_dir: Optional[Path] = None) -> bool:
    """
    Fetch Qwen usage and save to database.

    Args:
        days: Number of days to look back
        project_dir: Optional specific project directory

    Returns:
        True if successful, False otherwise
    """
    if project_dir is None:
        project_dir = find_qwen_project_dir()

    if not project_dir:
        print("Error: Cannot find Qwen project/chats directory.")
        return False

    jsonl_files = list(project_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"Error: No .jsonl files found in {project_dir}")
        return False

    # Aggregate across all files
    aggregated = defaultdict(lambda: {
        "prompt_tokens": 0,
        "candidates_tokens": 0,
        "thoughts_tokens": 0,
        "cached_tokens": 0,
        "total_tokens": 0,
        "models_used": set(),
    })

    for f in jsonl_files:
        daily = process_jsonl_file(f)
        for date, stats in daily.items():
            for key in ["prompt_tokens", "candidates_tokens", "thoughts_tokens", "cached_tokens", "total_tokens"]:
                aggregated[date][key] += stats[key]
            aggregated[date]["models_used"].update(stats["models_used"])

    # Filter by date range
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days-1)).strftime("%Y-%m-%d")

    saved = 0
    for date, stats in aggregated.items():
        if start_date <= date <= today:
            total = stats["total_tokens"]

            if db.save_usage(
                date=date,
                tool_name="qwen",
                tokens_used=total,
                input_tokens=stats["prompt_tokens"],
                output_tokens=stats["candidates_tokens"],
                cache_tokens=stats["cached_tokens"],
                models_used=sorted(stats["models_used"])
            ):
                saved += 1
            print(f"  {date}: {total:,} tokens")

    print(f"\nSaved {saved} days of Qwen usage data")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch Qwen token usage')
    parser.add_argument('--days', type=int, default=7, help='Number of days')
    parser.add_argument('--project', help='Specific project directory')
    args = parser.parse_args()

    db.init_database()
    success = fetch_and_save(days=args.days, project_dir=Path(args.project) if args.project else None)
    sys.exit(0 if success else 1)
