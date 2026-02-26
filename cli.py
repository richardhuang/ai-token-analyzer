#!/usr/bin/env python3
"""
AI Token Usage - CLI Tool

A unified command-line interface for querying token usage data.
"""

import argparse
import sys
import os
from typing import Optional

# Add shared directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
shared_dir = os.path.join(script_dir, 'scripts')

if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

from shared import db, utils, email


def cmd_today(tool: Optional[str] = None) -> None:
    """Show usage for today."""
    today = utils.get_today()
    entries = db.get_usage_by_date(today, tool)

    if not entries:
        print(f"No usage data found for {today}")
        if tool:
            print(f"Tool: {tool}")
        return

    print(f"Usage for {today}")
    print("=" * 50)

    for entry in entries:
        tool_name = entry['tool_name']
        tokens = entry['tokens_used']
        input_tok = entry.get('input_tokens', 0)
        output_tok = entry.get('output_tokens', 0)
        cache_tok = entry.get('cache_tokens', 0)

        print(f"\n[{tool_name.upper()}]")
        print(f"  Total:  {utils.format_tokens(tokens)} ({tokens:,})")
        if input_tok > 0 or output_tok > 0:
            print(f"  Input:  {utils.format_tokens(input_tok)} ({input_tok:,})")
            print(f"  Output: {utils.format_tokens(output_tok)} ({output_tok:,})")
        if cache_tok > 0:
            print(f"  Cache:  {utils.format_tokens(cache_tok)} ({cache_tok:,})")
        if entry.get('models_used'):
            print(f"  Models: {', '.join(entry['models_used'])}")


def cmd_query(date: str, tool: Optional[str] = None) -> None:
    """Query usage for a specific date."""
    parsed_date = utils.parse_date(date)
    if not parsed_date:
        print(f"Invalid date format: {date}. Use YYYY-MM-DD")
        return

    entries = db.get_usage_by_date(parsed_date, tool)

    if not entries:
        print(f"No usage data found for {parsed_date}")
        return

    print(f"Usage for {parsed_date}")
    print("=" * 50)

    for entry in entries:
        tool_name = entry['tool_name']
        tokens = entry['tokens_used']

        print(f"\n[{tool_name.upper()}]")
        print(f"  Tokens: {utils.format_tokens(tokens)} ({tokens:,})")
        if entry.get('models_used'):
            print(f"  Models: {', '.join(entry['models_used'])}")


def cmd_top(
    tool: Optional[str] = None,
    days: int = 7
) -> None:
    """Show top usage for the last N days."""
    entries = db.get_usage_by_tool(tool, days) if tool else []

    if tool:
        entries = db.get_usage_by_tool(tool, days)
    else:
        all_tools = db.get_all_tools()
        entries = []
        for t in all_tools:
            entries.extend(db.get_usage_by_tool(t, days))

    if not entries:
        print("No usage data found")
        return

    # Aggregate by tool
    tool_totals = defaultdict(int)
    for entry in entries:
        tool_totals[entry['tool_name']] += entry['tokens_used']

    print(f"Usage for the last {days} days")
    print("=" * 50)

    # Sort by total tokens
    sorted_tools = sorted(tool_totals.items(), key=lambda x: x[1], reverse=True)

    for tool_name, total in sorted_tools:
        print(f"{tool_name.upper()}: {utils.format_tokens(total)} ({total:,})")


def cmd_reportEmail() -> None:
    """Generate and send email report."""
    import email

    config = utils.load_config()

    # Get summary and data
    summary = db.get_summary_by_tool()
    all_tools = db.get_all_tools()

    daily_data = []
    for tool in all_tools:
        daily_data.extend(db.get_usage_by_tool(tool, 7))

    # Format email body
    body = email.format_report_email(summary, daily_data)

    # Check email config
    email_config = config.get('email', {})
    if not email_config:
        print("Error: Email configuration not found")
        print("Please create config.json with email settings")
        return

    to_email = email_config.get('to_email')
    if not to_email:
        print("Error: to_email not configured")
        return

    # Test connection first
    if not email.test_email_config(email_config):
        print("Email server connection failed. Check your configuration.")
        return

    # Send email
    success = email.send_email(
        subject=f"AI Token Usage Report - {utils.get_today()}",
        body=body,
        smtp_config=email_config,
        to_email=to_email
    )

    if success:
        print(f"Report sent to {to_email}")
    else:
        print("Failed to send report")


def cmd_summary() -> None:
    """Show a summary of all data."""
    summary = db.get_summary_by_tool()

    if not summary:
        print("No usage data available")
        return

    print("AI Token Usage Summary")
    print("=" * 60)

    for tool, stats in sorted(summary.items(), key=lambda x: x[1]['total_tokens'], reverse=True):
        print(f"\n{tool.upper()}")
        print(f"  Days tracked:   {stats['days_count']}")
        print(f"  Total tokens:   {utils.format_tokens(stats['total_tokens'])} ({stats['total_tokens']:,})")
        print(f"  Average/day:    {utils.format_tokens(int(stats['avg_tokens']))} ({int(stats['avg_tokens']):,})")
        print(f"  Date range:     {stats['first_date']} to {stats['last_date']}")


def main():
    parser = argparse.ArgumentParser(
        description='AI Token Usage CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # today command
    today_parser = subparsers.add_parser('today', help='Show usage for today')
    today_parser.add_argument('--tool', help='Filter by tool')

    # query command
    query_parser = subparsers.add_parser('query', help='Query usage by date')
    query_parser.add_argument('date', help='Date in YYYY-MM-DD format')
    query_parser.add_argument('--tool', help='Filter by tool')

    # top command
    top_parser = subparsers.add_parser('top', help='Show top usage')
    top_parser.add_argument('--tool', help='Filter by tool')
    top_parser.add_argument('--days', type=int, default=7, help='Number of days')

    # report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('type', choices=['email'], help='Report type')

    # summary command
    subparsers.add_parser('summary', help='Show summary')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize database
    db.init_database()

    if args.command == 'today':
        cmd_today(args.tool)
    elif args.command == 'query':
        cmd_query(args.date, args.tool)
    elif args.command == 'top':
        cmd_top(args.tool, args.days)
    elif args.command == 'report':
        cmd_reportEmail()
    elif args.command == 'summary':
        cmd_summary()


if __name__ == "__main__":
    main()
