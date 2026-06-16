"""
Production test runner.

Usage:
    python test.py
"""

from __future__ import annotations

import sys
import pytest


def main() -> int:
    return pytest.main(
        [
            "tests",
            "-v",
            "--cov=.",
            "--cov-report=term-missing",
            "--tb=short",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())