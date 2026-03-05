#!/usr/bin/env python3
"""Test upload logic."""
import sys
sys.path.insert(0, '/opt/ai-token-analyzer/scripts/shared')
from db import get_new_usage_since, get_usage_by_tool

print("Testing get_usage_by_tool:")
result = get_usage_by_tool('openclaw', days=30)
print(f"  Found {len(result)} records")
for r in result[:3]:
    print(f"    {r}")

print("\nTesting get_new_usage_since (2026-02-21 to 2026-03-03):")
try:
    result = get_new_usage_since('2026-02-21', '2026-03-03')
    print(f"  Found {len(result)} records")
    for r in result[:3]:
        print(f"    {r}")
except Exception as e:
    print(f"  Error: {e}")
