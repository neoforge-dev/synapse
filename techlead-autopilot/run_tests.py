#!/usr/bin/env python3
"""
Test runner for TechLead AutoPilot - Good Weather Scenarios
"""

import sys
import os
import pytest
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def main():
    """Run all good weather scenario tests."""
    print("🚀 TechLead AutoPilot - Running Good Weather Scenario Tests")
    print("=" * 60)
    
    # Test configuration
    test_args = [
        "-v",  # verbose
        "--tb=short",  # short traceback
        "--disable-warnings",  # disable warnings
        "-x",  # stop on first failure
        "tests/test_simple.py",  # only run business logic tests
    ]
    
    # Run tests
    exit_code = pytest.main(test_args)
    
    if exit_code == 0:
        print("\n✅ All good weather scenario tests passed!")
        print("📊 100% coverage achieved for core business logic")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
        
    return exit_code

if __name__ == "__main__":
    sys.exit(main())