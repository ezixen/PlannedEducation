#!/usr/bin/env python3
"""
Smart Test Runner - Runs tests incrementally based on file changes.
Uses the test tracker to avoid re-running tests for unmodified files.
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path
from test_tracker import tracker

# Use the venv python
VENV_PYTHON = r"C:\.venv\Scripts\python.exe"

def get_modified_files_since_last_run() -> list:
    """Get list of files modified since last successful test run."""
    # This is a simple implementation - in practice you'd use git or file timestamps
    return []

def run_pytest_with_tracking(test_path: str = "tests/", incremental: bool = True, extra_args: list = None):
    """Run pytest with incremental tracking."""
    cmd = [VENV_PYTHON, "-m", "pytest"]
    
    if incremental:
        cmd.extend(["-p", "conftest_tracker", "--incremental"])
    else:
        cmd.extend(["--no-incremental"])
    
    cmd.append(test_path)
    
    if extra_args:
        cmd.extend(extra_args)
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    return result.returncode

def run_ui_tests(incremental: bool = True):
    """Run UI tests with tracking."""
    test_file = "test_ui_full.py"
    
    if incremental and not tracker.should_run_test(test_file, "test_ui_full"):
        print(f"SKIPPED (unchanged): {test_file}")
        return 0
    
    cmd = [VENV_PYTHON, test_file]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    
    if result.returncode == 0:
        tracker.record_result(test_file, "test_ui_full", "passed", 0)
    else:
        tracker.record_result(test_file, "test_ui_full", "failed", 0, "UI test failed")
    
    return result.returncode

def main():
    parser = argparse.ArgumentParser(description="Smart Test Runner")
    parser.add_argument("--no-incremental", action="store_true", help="Run all tests")
    parser.add_argument("--ui-only", action="store_true", help="Run only UI tests")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--summary", action="store_true", help="Show test summary")
    parser.add_argument("test_path", nargs="?", default="tests/", help="Test path to run")
    parser.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra pytest arguments")
    
    args = parser.parse_args()
    
    if args.summary:
        tracker.print_summary()
        return 0
    
    incremental = not args.no_incremental
    
    if args.ui_only:
        return run_ui_tests(incremental)
    
    if args.unit_only:
        return run_pytest_with_tracking(args.test_path, incremental, args.extra_args)
    
    # Run both unit and UI tests
    unit_result = run_pytest_with_tracking(args.test_path, incremental, args.extra_args)
    ui_result = run_ui_tests(incremental)
    
    tracker.print_summary()
    
    return max(unit_result, ui_result)

if __name__ == "__main__":
    sys.exit(main())