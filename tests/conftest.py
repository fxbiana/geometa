"""Shared pytest configuration for GeoMeta tests."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "wave2_integration: requires Wave 2 detectors (objects/script); skip when unavailable",
    )
