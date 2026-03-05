#!/usr/bin/env python3
"""
AI Token Usage - Upload to Server Script

Uploads token usage data from local machine to a central server.
Designed for remote machines to push their data to the server.

Usage:
  # One-time upload
  python3 upload_to_server.py --server http://server:5001 --auth-key "key"

  # Daemon mode with periodic upload (default: every 30 seconds)
  python3 upload_to_server.py --server http://server:5001 --auth-key "key" --daemon

  # Custom interval
  python3 upload_to_server.py --server http://server:5001 --auth-key "key" --daemon --interval 60
"""

import argparse
import json
import os
import sys
import time
import signal
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add shared directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
shared_dir = os.path.join(script_dir, 'shared')
if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

from shared import db, utils


def load_host_config() -> Dict:
    """Load hostname from config or use system hostname."""
    config = utils.load_config()
    return config.get('host_name', utils.load_config().get('host_name', 'localhost'))


def fetch_usage_data(days: int = 7, tool_name: str = None) -> List[Dict]:
    """Fetch usage data from local database."""
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days-1)).strftime("%Y-%m-%d")

    if tool_name:
        entries = db.get_usage_by_tool(tool_name, days, end_date=today)
    else:
        all_tools = db.get_all_tools()
        entries = []
        for tool in all_tools:
            entries.extend(db.get_usage_by_tool(tool, days, end_date=today))

    # Filter by date range
    filtered = []
    for entry in entries:
        if start_date <= entry['date'] <= today:
            filtered.append(entry)

    return filtered


def fetch_messages_data(days: int = 7, tool_name: str = None, limit: int = 1000) -> List[Dict]:
    """Fetch messages data from local database."""
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days-1)).strftime("%Y-%m-%d")

    all_messages = []

    if tool_name:
        tools = [tool_name]
    else:
        tools = db.get_all_tools()

    for tool in tools:
        result = db.get_messages_by_date(
            date=today,
            tool_name=tool,
            page=1,
            limit=limit
        )
        messages = result.get('messages', [])

        # Filter by date range
        for msg in messages:
            if start_date <= msg['date'] <= today:
                all_messages.append(msg)

    return all_messages


def upload_usage(host_name: str, usage_data: List[Dict], server_url: str, auth_key: str) -> Dict:
    """Upload usage data to server."""
    payload = {
        'host_name': host_name,
        'data': usage_data
    }

    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Key': auth_key
    }

    try:
        response = requests.post(
            f'{server_url}/api/upload/usage',
            json=payload,
            headers=headers,
            timeout=30
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def upload_messages(host_name: str, messages_data: List[Dict], server_url: str, auth_key: str) -> Dict:
    """Upload messages data to server."""
    payload = {
        'host_name': host_name,
        'data': messages_data
    }

    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Key': auth_key
    }

    try:
        response = requests.post(
            f'{server_url}/api/upload/messages',
            json=payload,
            headers=headers,
            timeout=30
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def upload_batch(host_name: str, usage_data: List[Dict], messages_data: List[Dict],
                 server_url: str, auth_key: str) -> Dict:
    """Upload both usage and messages data in a single batch request."""
    payload = {
        'host_name': host_name,
        'usage': usage_data,
        'messages': messages_data
    }

    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Key': auth_key
    }

    try:
        response = requests.post(
            f'{server_url}/api/upload/batch',
            json=payload,
            headers=headers,
            timeout=60
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def get_config_path() -> str:
    """Get the config file path."""
    return os.path.expanduser('~/.ai-token-analyzer/config.json')


def load_server_config() -> Dict:
    """Load server upload configuration."""
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config.get('server', {})
    except (json.JSONDecodeError, IOError):
        return {}


def get_upload_marker_path() -> str:
    """Get path to file tracking last upload timestamp."""
    config_dir = os.path.expanduser('~/.ai-token-analyzer')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'upload_marker.json')


def load_upload_marker() -> Dict:
    """Load the last upload marker."""
    path = get_upload_marker_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_upload_marker(host_name: str, last_upload: str) -> None:
    """Save the last upload marker."""
    path = get_upload_marker_path()
    marker = load_upload_marker()
    marker[host_name] = {
        'last_upload': last_upload,
        'timestamp': datetime.now().isoformat()
    }
    with open(path, 'w') as f:
        json.dump(marker, f, indent=2)


def get_usage_data_for_upload(start_date: str, end_date: str, tool_name: str = None) -> List[Dict]:
    """Get usage data within a date range for upload."""
    if tool_name:
        entries = db.get_usage_by_tool(tool_name, days=30, end_date=end_date)
    else:
        all_tools = db.get_all_tools()
        entries = []
        for tool in all_tools:
            entries.extend(db.get_usage_by_tool(tool, days=30, end_date=end_date))

    # Filter by date range
    result = []
    for entry in entries:
        if start_date <= entry['date'] <= end_date:
            result.append(entry)

    return result


def get_messages_data_for_upload(start_date: str, end_date: str, tool_name: str = None) -> List[Dict]:
    """Get messages data within a date range for upload."""
    all_messages = []
    tools = [tool_name] if tool_name else db.get_all_tools()

    for tool in tools:
        result = db.get_messages_by_date(date=end_date, tool_name=tool, page=1, limit=5000)
        messages = result.get('messages', [])

        for msg in messages:
            if start_date <= msg['date'] <= end_date:
                all_messages.append(msg)

    return all_messages


def main():
    parser = argparse.ArgumentParser(
        description='Upload AI token usage data to central server',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--server', '-s', required=True,
                        help='Server URL (e.g., http://server:5001)')
    parser.add_argument('--auth-key', '-k', default=None,
                        help='Authentication key for server upload')
    parser.add_argument('--days', '-d', type=int, default=7,
                        help='Number of days to upload (default: 7)')
    parser.add_argument('--tool', '-t', default=None,
                        help='Specific tool to upload (claude, qwen, openclaw)')
    parser.add_argument('--hostname', '-n', default=None,
                        help='Hostname to use (default: from config or system)')
    parser.add_argument('--usage-only', action='store_true',
                        help='Upload only usage data')
    parser.add_argument('--messages-only', action='store_true',
                        help='Upload only messages data')
    parser.add_argument('--no-batch', action='store_true',
                        help='Do not use batch upload (use separate endpoints)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be uploaded without actually uploading')
    parser.add_argument('--daemon', action='store_true',
                        help='Run as daemon with periodic uploads')
    parser.add_argument('--interval', '-i', type=int, default=30,
                        help='Interval between uploads in seconds (default: 30, requires --daemon)')
    parser.add_argument('--incremental', action='store_true',
                        help='Only upload new data since last upload')
    parser.add_argument('--no-incremental', action='store_true',
                        help='Upload all data (default: incremental if --daemon, full otherwise)')

    args = parser.parse_args()

    # Validate URL
    if not args.server.startswith(('http://', 'https://')):
        print(f"Error: Invalid server URL: {args.server}")
        print("URL must start with http:// or https://")
        sys.exit(1)

    # Load configuration
    server_config = load_server_config()

    # Get hostname
    if args.hostname:
        host_name = args.hostname
    else:
        host_name = load_host_config()

    print(f"=== Uploading data from: {host_name} ===\n")

    # Get auth key (CLI arg takes precedence over config)
    auth_key = args.auth_key or server_config.get('upload_auth_key')

    if not auth_key:
        print("Error: Authentication key not provided")
        print("  Use --auth-key or set server.upload_auth_key in config")
        sys.exit(1)

    print(f"Server: {args.server}")
    print(f"Auth key: {auth_key[:8]}...{auth_key[-4:] if len(auth_key) > 12 else ''}")
    print(f"Days to upload: {args.days}")
    if args.tool:
        print(f"Tool: {args.tool}")
    if args.daemon:
        print(f"Daemon mode: enabled (interval: {args.interval}s)")
    print()

    # Determine incremental mode
    if args.incremental:
        incremental = True
    elif args.no_incremental:
        incremental = False
    else:
        # Default: incremental if daemon mode, otherwise full upload
        incremental = args.daemon

    if incremental:
        print(f"Incremental mode: enabled")

    if args.dry_run:
        print("\n=== DRY RUN - No upload will occur ===")
        print("This is a dry run - no data will be uploaded")
        sys.exit(0)

    # Daemon mode - continuous upload
    if args.daemon:
        print(f"Starting daemon mode (upload every {args.interval} seconds)...")
        print("Press Ctrl+C to stop\n")

        # Setup signal handler for graceful shutdown
        running = [True]

        def signal_handler(signum, frame):
            print("\nReceived shutdown signal...")
            running[0] = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        upload_count = 0
        while running[0]:
            try:
                upload_count += 1
                upload_periodic(host_name, args, auth_key, incremental, upload_count)
                if running[0]:
                    # Sleep in small chunks to check for signal more frequently
                    for _ in range(args.interval * 2):
                        if not running[0]:
                            break
                        time.sleep(0.5)
            except Exception as e:
                print(f"Upload error: {e}")
                if running[0]:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)

        print(f"Daemon stopped. Total uploads: {upload_count}")
        return

    # Single upload mode
    # Determine date range
    if incremental:
        marker = load_upload_marker()
        last_upload = marker.get(host_name, {}).get('last_upload')
        if last_upload:
            start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            print(f"Fetching incremental data from {start_date} to {end_date}...")
        else:
            start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            print(f"No previous upload marker found. Fetching last {args.days} days...")
    else:
        start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        print(f"Fetching all data from {start_date} to {end_date}...")

    # Fetch and upload usage data
    print(f"\nProcessing usage data...")
    usage_data = get_usage_data_for_upload(start_date, end_date, tool_name=args.tool)
    print(f"  Found {len(usage_data)} usage records to upload")

    # Fetch and upload messages data
    messages_data = []
    if not args.usage_only:
        print(f"Processing messages data...")
        messages_data = get_messages_data_for_upload(start_date, end_date, tool_name=args.tool)
        print(f"  Found {len(messages_data)} messages to upload")

    # Perform upload
    print("\nUploading data...")

    if args.messages_only:
        # Upload only messages
        result = upload_messages(host_name, messages_data, args.server, auth_key)
    elif args.usage_only:
        # Upload only usage
        result = upload_usage(host_name, usage_data, args.server, auth_key)
    elif args.no_batch:
        # Use separate endpoints
        usage_result = upload_usage(host_name, usage_data, args.server, auth_key)
        messages_result = upload_messages(host_name, messages_data, args.server, auth_key)
        result = {
            'usage': usage_result,
            'messages': messages_result
        }
    else:
        # Use batch upload
        result = upload_batch(host_name, usage_data, messages_data, args.server, auth_key)

    # Display results
    if isinstance(result, dict):
        if 'error' in result:
            print(f"\nError: {result['error']}")
            sys.exit(1)

        print("\n=== Upload Results ===")
        if 'usage' in result and 'records_saved' in result['usage']:
            print(f"Usage: {result['usage']['records_saved']} records saved")
        if 'messages' in result and 'records_saved' in result['messages']:
            print(f"Messages: {result['messages']['records_saved']} records saved")

        if 'usage_records_saved' in result:
            print(f"Usage: {result['usage_records_saved']} records saved")
        if 'messages_records_saved' in result:
            print(f"Messages: {result['messages_records_saved']} records saved")

        # Save marker if successful and incremental mode
        if incremental and result.get('success'):
            save_upload_marker(host_name, datetime.now().isoformat())
            print("\nUpload marker saved")

        print("\nUpload completed successfully!")
    else:
        print(f"\nUnexpected response: {result}")
        sys.exit(1)


def upload_periodic(host_name: str, args, auth_key: str, incremental: bool, upload_num: int) -> None:
    """Perform a periodic upload in daemon mode."""
    now = datetime.now()
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Upload #{upload_num} starting...")

    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=args.days)).strftime("%Y-%m-%d")

    # Fetch usage data
    usage_data = get_usage_data_for_upload(start_date, end_date, tool_name=args.tool)
    print(f"  Usage: {len(usage_data)} new records")

    # Fetch messages data
    messages_data = []
    if not args.usage_only:
        messages_data = get_messages_data_for_upload(start_date, end_date, tool_name=args.tool)
        print(f"  Messages: {len(messages_data)} new records")

    if not usage_data and not messages_data:
        print(f"  No new data to upload")
        return

    # Perform upload
    if args.messages_only:
        result = upload_messages(host_name, messages_data, args.server, auth_key)
    elif args.usage_only:
        result = upload_usage(host_name, usage_data, args.server, auth_key)
    else:
        result = upload_batch(host_name, usage_data, messages_data, args.server, auth_key)

    # Log result
    if isinstance(result, dict) and result.get('success'):
        usage_saved = result.get('usage_records_saved', result.get('usage', {}).get('records_saved', 0))
        msg_saved = result.get('messages_records_saved', result.get('messages', {}).get('records_saved', 0))
        print(f"  ✓ Uploaded {usage_saved} usage, {msg_saved} messages")
    else:
        print(f"  ✗ Upload failed: {result}")


if __name__ == '__main__':
    main()
