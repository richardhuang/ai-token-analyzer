#!/usr/bin/env python3
"""Fix created_at timestamps in database."""
import sys
import sqlite3
import os
from datetime import datetime, timedelta

# Add shared directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
shared_dir = os.path.join(script_dir)
if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

from shared.config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Calculate time difference (remote was 8 hours fast)
# The created_at timestamps are 8 hours ahead of actual
# We need to subtract 8 hours from them

# Get current max created_at to determine the offset
cursor.execute('SELECT MAX(created_at) FROM daily_usage')
max_created = cursor.fetchone()[0]
print(f"Max created_at: {max_created}")

if max_created:
    try:
        # Parse the timestamp
        dt = datetime.fromisoformat(max_created.replace('Z', '+00:00').replace('+00:00', ''))
        now = datetime.now()

        # If created_at is in the future (relative to now), it's wrong
        # Remote time was 8 hours fast, so we need to subtract 8 hours
        diff = (dt.utctimetuple().tm_hour + 8) % 24

        # Update all created_at timestamps
        # The issue is that when the script ran, system time was 8 hours ahead
        # So we need to subtract 8 hours from created_at
        cursor.execute('''
            UPDATE daily_usage
            SET created_at = datetime(created_at, '-8 hours')
        ''')
        conn.commit()
        print(f"Fixed {cursor.rowcount} created_at records in daily_usage")

        cursor.execute('''
            UPDATE daily_messages
            SET created_at = datetime(created_at, '-8 hours')
        ''')
        conn.commit()
        print(f"Fixed {cursor.rowcount} created_at records in daily_messages")

    except Exception as e:
        print(f"Error: {e}")

conn.close()
print("Timestamp fix complete")
