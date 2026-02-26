#!/usr/bin/env python3
"""
AI Token Usage - OpenClaw Fetcher

Fetches daily token usage from OpenClaw gateway using WebSocket API.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    import websockets
except ImportError:
    print("Error: websockets module not installed")
    print("Install with: pip install websockets")
    sys.exit(1)

# Add parent directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from shared import db


async def get_openclaw_usage(
    gateway_url: str,
    token: str,
    days: int = 7
) -> Optional[Dict[str, int]]:
    """
    Fetch daily usage data from OpenClaw gateway.

    Returns a dict mapping dates to token counts, or None on error.
    """
    # Calculate date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days-1)).strftime("%Y-%m-%d")

    print(f"Fetching {days} days of OpenClaw usage data...")
    print(f"Date range: {start_date} to {end_date}")

    # Parse gateway URL for WebSocket connection
    if gateway_url.startswith("https://"):
        ws_scheme = "wss://"
        gateway_host = gateway_url[8:]
    elif gateway_url.startswith("http://"):
        ws_scheme = "ws://"
        gateway_host = gateway_url[7:]
    else:
        ws_scheme = "ws://"
        gateway_host = gateway_url

    ws_url = f"{ws_scheme}{gateway_host}/gateway"
    print(f"Connecting to WebSocket: {ws_url}")

    extra_headers = {
        "Authorization": f"Bearer {token}",
        "Origin": gateway_url,
    }

    try:
        async with websockets.connect(ws_url, additional_headers=extra_headers) as websocket:
            # Wait for connect.challenge
            message = await asyncio.wait_for(websocket.recv(), timeout=10)
            response = json.loads(message)

            if response.get("type") != "event" or response.get("event") != "connect.challenge":
                print(f"Unexpected initial message: {response}")
                return None

            nonce = response.get("payload", {}).get("nonce")

            # Connect with openclaw-control-ui client
            connect_params = {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "openclaw-control-ui",
                    "displayName": "AI Token Usage Getter",
                    "version": "1.0.0",
                    "platform": "web",
                    "mode": "ui",
                },
                "role": "operator",
                "scopes": ["operator.admin", "operator.read", "operator.write"],
                "auth": {
                    "token": token,
                },
                "userAgent": "AI-Token-Usage-Getter/1.0",
                "locale": "en-US",
            }

            connect_request = {
                "type": "req",
                "id": str(uuid.uuid4()),
                "method": "connect",
                "params": connect_params
            }

            await websocket.send(json.dumps(connect_request))

            # Wait for hello-ok response
            hello = await asyncio.wait_for(websocket.recv(), timeout=10)
            hello_resp = json.loads(hello)

            if hello_resp.get("type") != "res" or not hello_resp.get("ok"):
                error = hello_resp.get("error", {})
                print(f"Connect failed: {error.get('code', 'Unknown')}: {error.get('message', '')}")
                return None

            print("Connection established successfully!")

            # Send usage.cost request
            usage_request = {
                "type": "req",
                "id": str(uuid.uuid4()),
                "method": "usage.cost",
                "params": {
                    "startDate": start_date,
                    "endDate": end_date,
                    "days": days,
                    "mode": "utc"
                }
            }

            await websocket.send(json.dumps(usage_request))

            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            response = json.loads(response)

            if response.get("type") == "res" and response.get("ok"):
                return parse_usage_response(response)
            else:
                print(f"Usage request failed: {response}")
                return None

    except websockets.exceptions.ConnectionClosed as e:
        print(f"WebSocket connection closed: {e.code} {e.reason}")
        return None
    except asyncio.TimeoutError:
        print("Timeout waiting for response")
        return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_usage_response(response: dict) -> Dict[str, int]:
    """Parse the usage cost response and extract daily token usage."""
    result = response.get("payload", {})

    daily_usage = {}
    daily_array = result.get("daily", [])

    for day_entry in daily_array:
        if isinstance(day_entry, dict):
            date = day_entry.get("date")
            tokens = day_entry.get("tokens") or day_entry.get("totalTokens")
            if date and tokens is not None:
                daily_usage[date] = int(tokens)

    return daily_usage


async def fetch_and_save(
    token_env: str = "OPENCLAW_TOKEN",
    gateway_url: str = "http://127.0.0.1:18789",
    days: int = 7
) -> bool:
    """
    Fetch OpenClaw usage and save to database.

    Args:
        token_env: Environment variable name for the token
        gateway_url: OpenClaw gateway URL
        days: Number of days to fetch

    Returns:
        True if successful, False otherwise
    """
    token = os.getenv(token_env)
    if not token:
        print(f"Error: {token_env} not set")
        return False

    result = await get_openclaw_usage(gateway_url, token, days)

    if result:
        saved = 0
        for date, tokens in result.items():
            if db.save_usage(
                date=date,
                tool_name="openclaw",
                tokens_used=tokens
            ):
                saved += 1

        print(f"\nSaved {saved} days of OpenClaw usage data")
        return True
    else:
        print("Failed to retrieve usage data")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fetch OpenClaw token usage')
    parser.add_argument('--days', type=int, default=7, help='Number of days')
    parser.add_argument('--url', default='http://127.0.0.1:18789', help='Gateway URL')
    parser.add_argument('--token', help='OpenClaw token (overrides env)')
    args = parser.parse_args()

    if args.token:
        os.environ['OPENCLAW_TOKEN'] = args.token

    # Initialize database
    db.init_database()

    # Run the fetcher
    success = asyncio.run(fetch_and_save(days=args.days, gateway_url=args.url))

    sys.exit(0 if success else 1)
