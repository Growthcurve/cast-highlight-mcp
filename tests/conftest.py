"""Shared test fixtures."""

import pytest

from cast_highlight_mcp.config import Config


@pytest.fixture
def mock_config() -> Config:
    """Create a mock config for testing."""
    return Config(
        base_url="https://app.casthighlight.com/WS2",
        access_token="test-token-12345",
        company_id=1234,
        timeout=30,
    )


@pytest.fixture
def sample_company_response() -> dict:
    """Sample company API response."""
    return {
        "id": 1234,
        "name": "Test Company",
        "profile": "trial",
        "status": "active",
        "domains": 3,
        "applications": 10,
        "applicationsWithResult": 8,
        "maxApplications": 25,
        "features": ["BENCHMARK", "CVE", "CLOUD_READY"],
    }


@pytest.fixture
def sample_domain_response() -> dict:
    """Sample domain API response."""
    return {
        "id": 1234,
        "name": "Test Domain",
        "clientRef": "REF-001",
    }


@pytest.fixture
def sample_application_response() -> dict:
    """Sample application API response."""
    return {
        "id": 5678,
        "name": "Test Application",
        "status": "active",
        "domains": [{"id": 1234, "name": "Test Domain"}],
        "metrics": [
            {
                "softwareHealth": 0.75,
                "softwareAgility": 0.70,
                "softwareElegance": 0.65,
                "softwareResiliency": 0.80,
                "technicalDebt": 10000.0,
                "totalLinesOfCode": 50000,
            }
        ],
    }
