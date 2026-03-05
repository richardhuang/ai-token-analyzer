#!/usr/bin/env python3
"""Check database content."""
import sqlite3
import sys
import os

# Add shared directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
shared_dir = os.path.join(script_dir)
if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

from shared.config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('SELECT * FROM daily_usage LIMIT 5')
print("Usage:", c.fetchall())
c.execute('SELECT * FROM daily_messages LIMIT 5')
print("Messages:", c.fetchall())
conn.close()
