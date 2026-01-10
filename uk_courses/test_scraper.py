#!/usr/bin/env python3
"""Quick test of the UK catalog scraper."""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scrapers.uk_catalog_scraper import UKCatalogScraper

logging.basicConfig(level=logging.INFO)


async def test_single_course():
    """Test scraping a single course."""
    # Test with one course that should exist
    test_code = "ANT 337"

    print(f"\nTesting scraper with course: {test_code}")
    print("=" * 60)

    async with UKCatalogScraper(headless=True, slow_mo=200) as scraper:
        result = await scraper.scrape_course(test_code)

        print(f"\nResults for {test_code}:")
        print(f"  Success: {result.scrape_successful}")
        print(f"  Title: {result.title}")
        print(f"  Credits: {result.credits}")
        print(f"  Description: {result.description[:150] if result.description else 'N/A'}...")
        print(f"  Prerequisites: {result.prerequisites}")
        print(f"  Catalog URL: {result.catalog_url}")

        if result.error_message:
            print(f"  Error: {result.error_message}")

    return result


if __name__ == "__main__":
    result = asyncio.run(test_single_course())
    sys.exit(0 if result.scrape_successful else 1)
