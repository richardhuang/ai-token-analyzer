#!/usr/bin/env python3
"""Check timestamps in database."""
import sys
sys.path.insert(0, '/opt/ai-token-analyzer/scripts/shared')
import db

print("=== Usage Data ===")
usage_data = db.get_usage_by_date('2026-03-03')
for u in usage_data:
    print(f"  {u['date']} {u['created_at']}: {u['host_name']}/{u['tool_name']} = {u['tokens_used']} tokens")

print("\n=== Messages Data ===")
messages = db.get_messages_by_date('2026-03-03', 'openclaw', page=1, limit=5)
for m in messages.get('messages', []):
    print(f"  {m['date']} {m['timestamp']}: {m['role']} - {m['content'][:50]}...")
