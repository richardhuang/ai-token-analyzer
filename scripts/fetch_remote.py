#!/usr/bin/env python3
"""
AI Token Usage - Remote Fetch Script

Fetch token usage data from a remote machine via SSH.
The fetch scripts are run on the remote machine, then the database is copied locally.
"""

import argparse
import subprocess
import sys
import os
import sqlite3
import shutil
import tempfile

# Add shared directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
shared_dir = os.path.join(script_dir)
if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

from shared.config import REMOTE_USER


def main():
    parser = argparse.ArgumentParser(description='Fetch token usage from remote machine')
    parser.add_argument('host', help='Remote machine IP or hostname')
    parser.add_argument('--user', default=REMOTE_USER, help=f'Remote user (default: {REMOTE_USER})')
    parser.add_argument('--hostname', help='Hostname to use in database (default: remote hostname)')
    parser.add_argument('--days', type=int, default=7, help='Number of days to fetch (default: 7)')
    args = parser.parse_args()

    print(f"=== Fetching data from {args.host} ===\n")

    # Step 1: Check SSH connection
    print(f"1. Testing SSH connection to {args.user}@{args.host}...")
    result = subprocess.run(
        ["ssh", f"{args.user}@{args.host}", "echo 'Connection OK'"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error: Cannot connect to {args.host}: {result.stderr}")
        sys.exit(1)
    print("✓ SSH connection successful")

    # Step 2: Get remote hostname if not specified
    if not args.hostname:
        result = subprocess.run(
            ["ssh", f"{args.user}@{args.host}", "hostname"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            args.hostname = result.stdout.strip()
            print(f"✓ Remote hostname: {args.hostname}")
        else:
            args.hostname = args.host
            print(f"Using {args.host} as hostname")

    # Step 3: Check if ai-token-analyzer is available on remote
    print(f"\n2. Checking for ai-token-analyzer on remote machine...")
    result = subprocess.run(
        ["ssh", f"{args.user}@{args.host}", "ls -la /opt/ai-token-analyzer/ 2>/dev/null || echo 'not found'"],
        capture_output=True, text=True
    )

    if "not found" in result.stdout:
        print("Error: ai-token-analyzer not found at /opt/ai-token-analyzer/")
        print("Please install it on the remote machine first.")
        print("\nTo install on remote machine:")
        print("  1. Copy this project to /opt/ai-token-analyzer/")
        print("  2. Run: python3 -m pip install flask")
        sys.exit(1)
    print("✓ ai-token-analyzer found")

    # Step 4: Run fetch scripts on remote machine
    print(f"\n3. Running fetch scripts on remote machine...")
    print(f"   Fetching last {args.days} days of data...")

    # Create a Python script to run on remote
    remote_script = f'''
import sys
sys.path.insert(0, "/opt/ai-token-analyzer/scripts/shared")
from fetch_openclaw_messages import fetch_and_save as fetch_oc
from fetch_claude import fetch_and_save as fetch_cl
from fetch_qwen import fetch_and_save as fetch_qw

print("Fetching OpenClaw data...")
fetch_oc(days={args.days}, hostname="{args.hostname}")

print("Fetching Claude data...")
fetch_cl(days={args.days}, hostname="{args.hostname}")

print("Fetching Qwen data...")
fetch_qw(days={args.days}, hostname="{args.hostname}")

print("Done!")
'''

    # Write remote script to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(remote_script)
        temp_file = f.name

    try:
        # Copy script to remote
        ssh_copy = subprocess.run([
            "scp", temp_file, f"{args.user}@{args.host}:/tmp/run_fetch.py"
        ], capture_output=True, text=True)
        if ssh_copy.returncode != 0:
            print(f"Error copying script: {ssh_copy.stderr}")
            sys.exit(1)

        # Run the script remotely
        ssh_run = subprocess.run([
            "ssh", f"{args.user}@{args.host}", "python3 /tmp/run_fetch.py"
        ], capture_output=True, text=True)

        print(ssh_run.stdout)
        if ssh_run.returncode != 0:
            print(f"Fetch error on remote: {ssh_run.stderr}")
            sys.exit(1)

    finally:
        os.unlink(temp_file)
        subprocess.run([
            "ssh", f"{args.user}@{args.host}", "rm -f /tmp/run_fetch.py"
        ], capture_output=True)

    # Step 5: Copy remote database to local
    print(f"\n4. Copying database from remote machine...")
    remote_db = f"{args.user}@{args.host}:/home/{args.user}/.ai-token-analyzer/usage.db"
    local_db_tmp = "/tmp/remote_usage.db"

    # Get the database path - check common locations
    db_path_check = subprocess.run([
        "ssh", f"{args.user}@{args.host}",
        f"ls -la ~/.ai-token-analyzer/usage.db /opt/ai_token_usage/usage.db 2>/dev/null | head -1"
    ], capture_output=True, text=True)

    if db_path_check.returncode == 0:
        db_path = db_path_check.stdout.strip().split()[-1] if db_path_check.stdout.strip() else None
    else:
        db_path = None

    if not db_path:
        # Try to find it
        find_result = subprocess.run([
            "ssh", f"{args.user}@{args.host}",
            "find /home -name 'usage.db' 2>/dev/null | head -1"
        ], capture_output=True, text=True)
        if find_result.returncode == 0 and find_result.stdout.strip():
            db_path = find_result.stdout.strip()
        else:
            print("Error: Could not find usage.db on remote machine")
            sys.exit(1)

    print(f"   Database path on remote: {db_path}")

    # Copy database using sshfs or scp
    # First try to copy with scp (may fail if user doesn't have read access)
    copy_result = subprocess.run([
        "scp", f"{args.user}@{args.host}:{db_path}", local_db_tmp
    ], capture_output=True, text=True)

    if copy_result.returncode != 0:
        print(f"   Copy failed (checking permissions): {copy_result.stderr.strip()}")
        # Try using cat over ssh
        print("   Trying alternative method...")
        with open(local_db_tmp, 'wb') as f:
            ssh_cat = subprocess.Popen([
                "ssh", f"{args.user}@{args.host}", f"cat {db_path}"
            ], stdout=subprocess.PIPE)
            f.write(ssh_cat.stdout.read())
            ssh_cat.wait()

    print("✓ Database copied successfully")

    # Step 6: Import data into local database
    print(f"\n5. Importing data into local database...")
    from shared.config import DB_PATH
    local_db = DB_PATH

    # Connect to remote db (temp file)
    conn_remote = sqlite3.connect(local_db_tmp)
    conn_remote.row_factory = sqlite3.Row
    cursor_remote = conn_remote.cursor()

    # Connect to local db
    conn_local = sqlite3.connect(local_db)
    conn_local.row_factory = sqlite3.Row
    cursor_local = conn_local.cursor()

    # Import usage data
    cursor_remote.execute('''
        SELECT date, tool_name, host_name, tokens_used, input_tokens, output_tokens,
        cache_tokens, request_count, models_used
        FROM daily_usage WHERE host_name = 'localhost' OR host_name IS NULL
    ''')

    usage_imported = 0
    for row in cursor_remote.fetchall():
        models_used = row['models_used']
        if models_used:
            import json
            try:
                models_used = json.loads(models_used)
            except:
                models_used = None

        cursor_local.execute('''
            INSERT OR REPLACE INTO daily_usage
            (date, tool_name, host_name, tokens_used, input_tokens, output_tokens,
            cache_tokens, request_count, models_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['date'], row['tool_name'], args.hostname,
            row['tokens_used'], row['input_tokens'], row['output_tokens'],
            row['cache_tokens'], row['request_count'], models_used
        ))
        usage_imported += 1

    conn_local.commit()

    # Import message data
    cursor_remote.execute('''
        SELECT date, tool_name, message_id, parent_id, role, content,
        tokens_used, input_tokens, output_tokens, model, timestamp
        FROM daily_messages WHERE host_name = 'localhost' OR host_name IS NULL
        LIMIT 1000
    ''')

    message_imported = 0
    for row in cursor_remote.fetchall():
        cursor_local.execute('''
            INSERT OR REPLACE INTO daily_messages
            (date, tool_name, host_name, message_id, parent_id, role, content,
            tokens_used, input_tokens, output_tokens, model, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['date'], row['tool_name'], args.hostname,
            row['message_id'], row['parent_id'], row['role'], row['content'],
            row['tokens_used'], row['input_tokens'], row['output_tokens'],
            row['model'], row['timestamp']
        ))
        message_imported += 1

    conn_local.commit()
    conn_remote.close()
    conn_local.close()

    # Cleanup temp file
    os.unlink(local_db_tmp)

    print(f"   Usage records: {usage_imported}")
    print(f"   Message records: {message_imported}")

    print(f"\n=== Summary ===")
    print(f"✓ Data from {args.host} imported with hostname '{args.hostname}'")
    print(f"  - Usage records: {usage_imported}")
    print(f"  - Message records: {message_imported}")


if __name__ == "__main__":
    main()
