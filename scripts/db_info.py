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

# Check tools in database
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('SELECT DISTINCT tool_name FROM daily_usage')
tools = c.fetchall()
print("Tools:", [t[0] for t in tools])

# Check dates
c.execute('SELECT DISTINCT date FROM daily_usage ORDER BY date')
dates = c.fetchall()
print("Dates:", [d[0] for d in dates])

# Check host_names
c.execute('SELECT DISTINCT host_name FROM daily_usage')
hosts = c.fetchall()
print("Hosts:", [h[0] for h in hosts])

conn.close()
