"""Pytest configuration for E2E tests. Uses pytest-playwright (page fixture)."""

import pytest


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Run browser in headed mode by default for local debugging; set HEADLESS=1 for CI."""
    import os
    if os.environ.get("HEADLESS", "").strip() == "1":
        return {"headless": True}
    return {"headless": False}
