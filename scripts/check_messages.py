#!/usr/bin/env python3
"""Check messages data."""
import sys
sys.path.insert(0, '/opt/ai-token-analyzer/scripts/shared')
import db

r = db.get_messages_by_date('2026-03-03', 'openclaw', page=1, limit=2)
print(f"Messages today: {len(r.get('messages', []))}")

# Check all dates
all_messages = []
for date in ['2026-02-27', '2026-02-28', '2026-03-01', '2026-03-03']:
    r = db.get_messages_by_date(date, 'openclaw', page=1, limit=10)
    count = len(r.get('messages', []))
    print(f"  {date}: {count} messages")
