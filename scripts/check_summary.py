#!/usr/bin/env python3
"""Check database summary."""
import sys
sys.path.insert(0, '/opt/ai-token-analyzer/scripts/shared')
from db import get_summary_by_tool

print("Summary:", get_summary_by_tool())
