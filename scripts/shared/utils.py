#!/usr/bin/env python3
"""
AI Token Usage - Utils Module

Provides utility functions for the ai_token_usage project.
"""

from typing import Dict, List, Optional


def format_tokens(tokens: int) -> str:
    """Format token count with human-readable units (K, M, B)."""
    if tokens >= 1_000_000_000:
        return f"{tokens / 1_000_000_000:.2f}B"
    elif tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.2f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.2f}K"
    else:
        return str(tokens)


def parse_date(date_str: str) -> Optional[str]:
    """Validate and normalize a date string (YYYY-MM-DD)."""
    if not date_str:
        return None
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        return None


def load_config(config_path: str = None) -> Dict:
    """Load configuration from JSON file."""
    import json
    import os

    if config_path is None:
        config_path = os.path.expanduser("~/.ai_token_usage/config.json")

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def save_config(config: Dict, config_path: str = None) -> None:
    """Save configuration to JSON file."""
    import json
    import os

    if config_path is None:
        config_path = os.path.expanduser("~/.ai_token_usage/config.json")

    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def get_today() -> str:
    """Get today's date in YYYY-MM-DD format."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def get_days_ago(days: int) -> str:
    """Get the date that was 'days' days ago."""
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def aggregate_daily_stats(entries: List[Dict]) -> Dict:
    """Aggregate daily statistics from multiple entries."""
    total = sum(e.get('tokens_used', 0) for e in entries)
    input_total = sum(e.get('input_tokens', 0) for e in entries)
    output_total = sum(e.get('output_tokens', 0) for e in entries)
    cache_total = sum(e.get('cache_tokens', 0) for e in entries)

    all_models = set()
    for e in entries:
        if e.get('models_used'):
            all_models.update(e['models_used'])

    return {
        'total_tokens': total,
        'input_tokens': input_total,
        'output_tokens': output_total,
        'cache_tokens': cache_total,
        'models': sorted(all_models)
    }
