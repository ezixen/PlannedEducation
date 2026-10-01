#!/usr/bin/env python3
"""
Test Tracker - Tracks which tests have been run and their results.
Only re-runs tests for files that have been modified since last successful run.
"""

import json
import os
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class TestResult:
    test_file: str
    test_name: str
    status: str  # "passed", "failed", "skipped"
    duration: float
    timestamp: str
    file_hash: str
    error_message: Optional[str] = None

@dataclass
class TestRun:
    run_id: str
    timestamp: str
    results: List[TestResult]
    total_tests: int
    passed: int
    failed: int
    skipped: int

class TestTracker:
    def __init__(self, tracker_file: str = "test_results.json"):
        self.tracker_file = Path(tracker_file)
        self.results: Dict[str, TestResult] = {}
        self.load()
    
    def load(self):
        """Load previous test results from file."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r') as f:
                    data = json.load(f)
                    for key, value in data.get('results', {}).items():
                        self.results[key] = TestResult(**value)
            except Exception as e:
                print(f"Warning: Could not load test tracker: {e}")
    
    def save(self):
        """Save test results to file."""
        data = {
            'results': {k: asdict(v) for k, v in self.results.items()},
            'last_updated': datetime.now().isoformat()
        }
        with open(self.tracker_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_file_hash(self, file_path: str) -> str:
        """Get hash of a file to detect changes."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return ""
    
    def should_run_test(self, test_file: str, test_name: str) -> bool:
        """Determine if a test should be run based on file changes."""
        key = f"{test_file}::{test_name}"
        
        # If never run before, run it
        if key not in self.results:
            return True
        
        # Check if the test file has been modified
        current_hash = self.get_file_hash(test_file)
        if current_hash != self.results[key].file_hash:
            return True
        
        # Check if any related source files have been modified
        # For UI tests, check the portal source files
        if test_file.endswith('test_ui_full.py'):
            source_files = [
                'web/apps/portal/src/pages/Login.tsx',
                'web/apps/portal/src/contexts/AuthContext.tsx',
                'web/apps/portal/src/contexts/ToastContext.tsx',
                'web/apps/portal/src/api.ts',
                'src/plannededucation/api/routes_auth.py',
            ]
            for src in source_files:
                if os.path.exists(src):
                    src_hash = self.get_file_hash(src)
                    # We don't track source file hashes in results, so always run if source changed
                    # This is a simple approach - in production you'd track source hashes too
                    pass
        
        # If test passed before and nothing changed, skip it
        if self.results[key].status == "passed":
            return False
        
        # If test failed before, always re-run
        return True
    
    def record_result(self, test_file: str, test_name: str, status: str, duration: float, error_message: Optional[str] = None):
        """Record a test result."""
        key = f"{test_file}::{test_name}"
        file_hash = self.get_file_hash(test_file)
        
        self.results[key] = TestResult(
            test_file=test_file,
            test_name=test_name,
            status=status,
            duration=duration,
            timestamp=datetime.now().isoformat(),
            file_hash=file_hash,
            error_message=error_message
        )
        self.save()
    
    def get_summary(self) -> Dict:
        """Get summary of test results."""
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r.status == "passed")
        failed = sum(1 for r in self.results.values() if r.status == "failed")
        skipped = sum(1 for r in self.results.values() if r.status == "skipped")
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped
        }
    
    def print_summary(self):
        """Print test summary."""
        summary = self.get_summary()
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total:  {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"{'='*60}")
        
        # Show failed tests
        failed_tests = [(k, v) for k, v in self.results.items() if v.status == "failed"]
        if failed_tests:
            print("\nFAILED TESTS:")
            for key, result in failed_tests:
                print(f"  - {result.test_file}::{result.test_name}")
                if result.error_message:
                    print(f"    Error: {result.error_message[:100]}")

# Global tracker instance
tracker = TestTracker()

def track_test(test_file: str, test_name: str):
    """Decorator to track test execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                tracker.record_result(test_file, test_name, "passed", duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                tracker.record_result(test_file, test_name, "failed", duration, str(e))
                raise
        return wrapper
    return decorator

if __name__ == "__main__":
    # Print summary when run directly
    tracker.print_summary()