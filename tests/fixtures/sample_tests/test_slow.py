"""Slow test fixture for timeout testing.

This test takes several seconds to complete, allowing timeout testing.
"""

import time


def test_slow_execution() -> None:
    """A test that takes several seconds to complete."""
    time.sleep(5)  # Sleep for 5 seconds
    assert True
