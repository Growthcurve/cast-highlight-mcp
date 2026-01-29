"""Configuration for CAST Highlight MCP Server."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    """CAST Highlight API configuration."""

    base_url: str
    access_token: str
    company_id: int
    timeout: int = 30


def load_config() -> Config:
    """Load configuration from environment variables."""
    load_dotenv()

    base_url = os.getenv("HIGHLIGHT_BASE_URL")
    access_token = os.getenv("HIGHLIGHT_ACCESS_TOKEN")
    company_id = os.getenv("HIGHLIGHT_COMPANY_ID")
    timeout = int(os.getenv("HIGHLIGHT_TIMEOUT", "30"))

    if not base_url:
        raise ValueError("HIGHLIGHT_BASE_URL environment variable is required")
    if not access_token:
        raise ValueError("HIGHLIGHT_ACCESS_TOKEN environment variable is required")
    if not company_id:
        raise ValueError("HIGHLIGHT_COMPANY_ID environment variable is required")

    return Config(
        base_url=base_url,
        access_token=access_token,
        company_id=int(company_id),
        timeout=timeout,
    )
