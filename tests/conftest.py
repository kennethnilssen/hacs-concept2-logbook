"""Shared pytest fixtures for Concept2 Logbook tests."""

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make custom_components discoverable by Home Assistant's test harness."""
    yield
