#!/usr/bin/env python3
"""
Comprehensive Test Runner for AI Token Analyzer

Runs all test suites and generates a unified report.
"""

import os
import sys
import subprocess
import json
from datetime import datetime

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
TESTS = [
    {
        'name': 'Database Layer',
        'script': 'test_database.py',
        'description': 'Tests for database functions (DB-01 to DB-13)',
        'tests': 55
    },
    {
        'name': 'Backend APIs',
        'script': 'test_api.py',
        'description': 'Tests for API endpoints (API-01 to API-25)',
        'tests': 41
    },
    {
        'name': 'Integration',
        'script': 'test_integration.py',
        'description': 'End-to-end scenarios (INT-01 to INT-05)',
        'tests': 20
    },
    {
        'name': 'Security',
        'script': 'test_security.py',
        'description': 'Security vulnerability tests (SEC-01 to SEC-06)',
        'tests': 25
    },
    {
        'name': 'UI',
        'script': 'test_ui.py',
        'description': 'Frontend UI tests (UI-01 to UI-19)',
        'tests': 25
    }
]

test_results = {
    'timestamp': datetime.now().isoformat(),
    'server_running': False,
    'total_tests': 0,
    'total_passed': 0,
    'total_failed': 0,
    'total_skipped': 0,
    'categories': {}
}


def check_server():
    """Check if Flask server is running."""
    try:
        import requests
        response = requests.get("http://localhost:5001/", timeout=5)
        test_results['server_running'] = True
        return True
    except:
        test_results['server_running'] = False
        return False


def run_test(test_info):
    """Run a single test suite."""
    script_path = os.path.join(BASE_DIR, 'scripts', test_info['script'])

    if not os.path.exists(script_path):
        print(f"  [SKIP] {test_info['name']}: Script not found")
        test_results['categories'][test_info['name']] = {
            'tests': test_info['tests'],
            'passed': 0,
            'failed': test_info['tests'],
            'status': 'skipped',
            'error': 'Script not found'
        }
        test_results['total_skipped'] += test_info['tests']
        return

    print(f"\n{'='*60}")
    print(f"Running: {test_info['name']}")
    print(f"Description: {test_info['description']}")
    print('='*60)

    try:
        result = subprocess.run(
            ['python3', script_path],
            capture_output=True,
            text=True,
            timeout=300
        )

        # Parse output for test counts
        output = result.stdout + result.stderr

        # Extract test results from summary
        passed = 0
        failed = 0

        for line in output.split('\n'):
            if 'Passed:' in line:
                parts = line.split('|')
                for part in parts:
                    if 'Passed:' in part:
                        try:
                            passed = int(part.replace('Passed:', '').strip().split()[0])
                        except:
                            pass
                    if 'Failed:' in part:
                        try:
                            failed = int(part.replace('Failed:', '').strip().split()[0])
                        except:
                            pass

        test_results['categories'][test_info['name']] = {
            'tests': test_info['tests'],
            'passed': passed,
            'failed': failed,
            'status': 'passed' if failed == 0 else 'failed',
            'output': output
        }

        test_results['total_passed'] += passed
        test_results['total_failed'] += failed

        print(f"  Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
        print(f"  Status: {'PASSED' if failed == 0 else 'FAILED'}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] Test suite timed out")
        test_results['categories'][test_info['name']] = {
            'tests': test_info['tests'],
            'passed': 0,
            'failed': test_info['tests'],
            'status': 'timeout',
            'error': 'Test timed out'
        }
        test_results['total_skipped'] += test_info['tests']
        return False
    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        test_results['categories'][test_info['name']] = {
            'tests': test_info['tests'],
            'passed': 0,
            'failed': test_info['tests'],
            'status': 'error',
            'error': str(e)
        }
        test_results['total_skipped'] += test_info['tests']
        return False


def generate_report():
    """Generate test report."""
    print("\n" + "=" * 70)
    print(" " * 15 + "AI TOKEN ANALYZER - TEST REPORT")
    print("=" * 70)

    print(f"\nTimestamp: {test_results['timestamp']}")
    print(f"Server Running: {test_results['server_running']}")
    print(f"Server Port: 5001")

    print("\n" + "-" * 70)
    print("TEST SUMMARY")
    print("-" * 70)

    total_tests = sum(c['tests'] for c in test_results['categories'].values())
    total_passed = test_results['total_passed']
    total_failed = test_results['total_failed']
    total_skipped = test_results['total_skipped']

    test_results['total_tests'] = total_tests
    test_results['total_passed'] = total_passed
    test_results['total_failed'] = total_failed
    test_results['total_skipped'] = total_skipped

    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"\n  Total Tests:   {total_tests}")
    print(f"  Passed:        {total_passed} ({success_rate:.1f}%)")
    print(f"  Failed:        {total_failed}")
    print(f"  Skipped:       {total_skipped}")

    print("\n" + "-" * 70)
    print("CATEGORY BREAKDOWN")
    print("-" * 70)

    for name, stats in test_results['categories'].items():
        status_symbol = "✓" if stats['status'] == 'passed' else "✗"
        print(f"\n  {status_symbol} {name}")
        print(f"    Tests: {stats['tests']} | Passed: {stats['passed']} | Failed: {stats['failed']}")

    # Failed test details
    print("\n" + "-" * 70)
    print("FAILED TEST DETAILS")
    print("-" * 70)

    has_failures = False
    for name, stats in test_results['categories'].items():
        if stats['status'] == 'failed' and 'output' in stats:
            # Extract failed tests from output
            output_lines = stats['output'].split('\n')
            for i, line in enumerate(output_lines):
                if '[FAIL]' in line:
                    has_failures = True
                    # Get the failed test details
                    print(f"\n  [{name}] {line.strip()}")
                    # Print context if available
                    for j in range(1, 3):
                        if i + j < len(output_lines):
                            print(f"     {output_lines[i+j]}")

    if not has_failures:
        print("\n  No failed tests details available.")

    # Environment info
    print("\n" + "=" * 70)
    print("ENVIRONMENT")
    print("=" * 70)
    import sys
    print(f"\n  Python Version: {sys.version}")
    try:
        import requests
        print(f"  Requests: {requests.__version__}")
    except:
        print("  Requests: Not installed")
    try:
        import flask
        print(f"  Flask: {flask.__version__}")
    except:
        print("  Flask: Not installed")
    try:
        import playwright
        print(f"  Playwright: Available")
    except:
        print("  Playwright: Not installed")

    # Final verdict
    print("\n" + "=" * 70)
    print("FINAL VERDICT")
    print("=" * 70)

    if total_failed == 0 and total_skipped == 0:
        print("\n  ✓ ALL TESTS PASSED")
        print("\n  The AI Token Analyzer is ready for production.")
    elif total_failed == 0:
        print("\n  ✓ NO FAILURES (some tests skipped)")
    else:
        print(f"\n  ✗ {total_failed} TEST(S) FAILED")
        print("\n  Please review the failed tests above.")

    print("\n" + "=" * 70)


def main():
    """Main entry point."""
    print("=" * 70)
    print(" " * 15 + "AI TOKEN ANALYZER - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    # Check server
    print("\n[Setup] Checking if server is running...")
    if not check_server():
        print("  Server is not running. Please run 'python3 web.py' first.")
        print("  Tests will be skipped or may fail.")

    # Run tests
    print("\n" + "=" * 70)
    print("INITIALIZING TESTS")
    print("=" * 70)

    for test_info in TESTS:
        run_test(test_info)

    # Generate report
    generate_report()

    # Exit with appropriate code
    if test_results['total_failed'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
