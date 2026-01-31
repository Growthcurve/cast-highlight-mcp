#!/usr/bin/env python3
"""Test CAST Highlight API connection."""

import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cast_highlight_mcp.client import HighlightClient
from cast_highlight_mcp.config import load_config


async def main():
    print("Testing CAST Highlight API connection...\n")

    config = load_config()
    client = HighlightClient(config)

    try:
        # Test company
        company = await client.get_company()
        print(f"✓ Connected to: {company['name']}")
        print(f"  Domains: {company['domains']}")
        print(f"  Applications: {company['applications']}")
        print(f"  Status: {company['status']}")

        # Test benchmark
        bench = await client.get_benchmark()
        print("\n✓ Benchmark data available")
        print(f"  Sample size: {bench['sampleSize']} applications")

        print("\n✓ All API tests passed!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
