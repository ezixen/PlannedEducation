#!/usr/bin/env python3
"""
Pytest plugin for test tracking - only runs tests for modified files.
"""

import pytest
import os
import hashlib
from pathlib import Path
from test_tracker import tracker, TestResult

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "tracked: mark test as tracked for incremental runs")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip unchanged tests."""
    # Check if we're in incremental mode
    if not config.getoption("--incremental", default=False):
        return
    
    skipped_items = []
    remaining_items = []
    
    for item in items:
        test_file = str(item.fspath)
        test_name = item.name
        
        if tracker.should_run_test(test_file, test_name):
            remaining_items.append(item)
        else:
            # Mark as skipped
            skipped_items.append(item)
            print(f"SKIPPED (unchanged): {test_file}::{test_name}")
    
    # Update items list
    items[:] = remaining_items
    
    if skipped_items:
        print(f"\nSkipped {len(skipped_items)} unchanged tests. Use --no-incremental to run all.")

def pytest_runtest_logreport(report):
    """Track test results."""
    if report.when == "call":
        test_file = str(report.location[0])
        test_name = report.location[2]
        
        if report.passed:
            tracker.record_result(test_file, test_name, "passed", report.duration)
        elif report.failed:
            tracker.record_result(test_file, test_name, "failed", report.duration, str(report.longrepr))
        elif report.skipped:
            tracker.record_result(test_file, test_name, "skipped", 0)

def pytest_sessionfinish(session, exitstatus):
    """Print summary at end of test session."""
    if session.config.getoption("--incremental", default=False):
        tracker.print_summary()

def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption(
        "--incremental",
        action="store_true",
        default=False,
        help="Only run tests for modified files (incremental mode)"
    )
    parser.addoption(
        "--no-incremental",
        action="store_true",
        default=False,
        help="Run all tests (disable incremental mode)"
    )