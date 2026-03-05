#!/usr/bin/env python3
"""Test db functions directly."""
import sys
sys.path.insert(0, '/opt/ai-token-analyzer/scripts/shared')
import db

print("Testing db.get_all_tools():")
tools = db.get_all_tools()
print(f"  Tools: {tools}")

print("\nTesting db.get_usage_by_tool('openclaw', days=30):")
result = db.get_usage_by_tool('openclaw', days=30)
print(f"  Count: {len(result)}")
for r in result[:3]:
    print(f"    {r['date']} - {r['tool_name']} - {r['host_name']} - {r['tokens_used']}")

print("\nTesting db.get_usage_by_tool('openclaw', days=30, end_date='2026-03-03'):")
result = db.get_usage_by_tool('openclaw', days=30, end_date='2026-03-03')
print(f"  Count: {len(result)}")
for r in result[:3]:
    print(f"    {r['date']} - {r['tool_name']} - {r['host_name']} - {r['tokens_used']}")
