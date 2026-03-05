#!/usr/bin/env python3
"""Initialize database on remote machine."""

import sqlite3
import os
import sys

# Add shared directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
shared_dir = os.path.join(script_dir)
if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

from shared.config import DB_DIR, DB_PATH

# Ensure directory exists
os.makedirs(DB_DIR, exist_ok=True)

# Create database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        host_name TEXT NOT NULL DEFAULT 'localhost',
        tokens_used INTEGER DEFAULT 0,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cache_tokens INTEGER DEFAULT 0,
        request_count INTEGER DEFAULT 0,
        models_used TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, tool_name, host_name)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        host_name TEXT NOT NULL DEFAULT 'localhost',
        message_id TEXT NOT NULL,
        parent_id TEXT,
        role TEXT NOT NULL,
        content TEXT,
        full_entry TEXT,
        tokens_used INTEGER DEFAULT 0,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        model TEXT,
        timestamp TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, tool_name, message_id, host_name)
    )
''')

conn.commit()
conn.close()
print(f"Database created at {DB_PATH}")
