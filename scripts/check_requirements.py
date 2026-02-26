#!/usr/bin/env python3
"""
AI Token Usage - Requirements check script
"""

import subprocess
import sys

required_packages = [
    "websockets",
    "aiohttp",
]

def check_package(pkg):
    """Check if a package is installed."""
    try:
        __import__(pkg.replace('-', '_'))
        return True
    except ImportError:
        return False

def main():
    missing = []
    for pkg in required_packages:
        if not check_package(pkg):
            missing.append(pkg)

    if missing:
        print("Missing packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        return 1
    else:
        print("All required packages are installed")
        return 0

if __name__ == "__main__":
    sys.exit(main())
