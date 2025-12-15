# backend/tests/utils/call_counter.py
"""
Call Counter Utility for Loop Consolidation Tests

Used to instrument and count function calls during testing,
ensuring healing loops don't exceed their budget limits.
"""


class CallCounter:
    """Thread-safe call counter for testing loop invariants."""
    
    def __init__(self):
        self.calls = {}

    def inc(self, name: str):
        """Increment call count for a named operation."""
        self.calls[name] = self.calls.get(name, 0) + 1

    def count(self, name: str) -> int:
        """Get current call count for a named operation."""
        return self.calls.get(name, 0)

    def reset(self):
        """Reset all counters."""
        self.calls = {}

    def assert_max(self, name: str, max_calls: int):
        """
        Assert that a named operation was called at most max_calls times.
        
        Raises:
            AssertionError with descriptive message if exceeded
        """
        actual = self.count(name)
        assert actual <= max_calls, (
            f"LOOP REGRESSION: {name} called {actual} times (max allowed: {max_calls}). "
            f"Someone reintroduced a retry loop!"
        )

    def assert_exact(self, name: str, expected: int):
        """Assert exact number of calls."""
        actual = self.count(name)
        assert actual == expected, (
            f"{name} called {actual} times (expected exactly: {expected})"
        )

    def get_all(self) -> dict:
        """Get all call counts."""
        return dict(self.calls)
