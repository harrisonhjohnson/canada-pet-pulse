#!/usr/bin/env python3
"""
Main orchestration script for UK Course Scraper.

Usage:
    python scripts/generate_site.py [--skip-scrape] [--output-dir OUTPUT_DIR] [--use-simple]

This script:
1. Loads the elective course list
2. Scrapes the UK catalog for each course (using Playwright or simple requests)
3. Combines the data
4. Generates HTML reports
"""
import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from scrapers.uk_catalog_scraper import UKCatalogScraper
from scrapers.uk_catalog_simple import UKCatalogSimpleScraper
from processors.course_processor import CourseProcessor
from generators.html_generator import HTMLGenerator
from models import EnrichedCourse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_DIR / 'scraper.log')
    ]
)
logger = logging.getLogger(__name__)


async def scrape_all_courses_playwright(processor: CourseProcessor, delay: float = 2.0):
    """
    Scrape all courses using Playwright (JavaScript rendering).

    Args:
        processor: CourseProcessor instance
        delay: Delay between requests in seconds

    Returns:
        List of ScrapedCourseInfo
    """
    course_codes = processor.get_course_codes()
    logger.info(f"Starting Playwright scrape of {len(course_codes)} courses")

    async with UKCatalogScraper(headless=True, slow_mo=100) as scraper:
        results = await scraper.scrape_courses(course_codes, delay_between=delay)

    # Save raw data
    processor.save_raw_scraped_data(results)

    successful = sum(1 for r in results if r.scrape_successful)
    logger.info(f"Scraping complete: {successful}/{len(results)} successful")

    return results


def scrape_all_courses_simple(processor: CourseProcessor, delay: float = 2.0):
    """
    Scrape all courses using simple HTTP requests (no JavaScript rendering).

    Args:
        processor: CourseProcessor instance
        delay: Delay between requests in seconds

    Returns:
        List of ScrapedCourseInfo
    """
    course_codes = processor.get_course_codes()
    logger.info(f"Starting simple scrape of {len(course_codes)} courses")

    scraper = UKCatalogSimpleScraper()
    results = scraper.scrape_courses(course_codes, delay_between=delay)

    # Save raw data
    processor.save_raw_scraped_data(results)

    successful = sum(1 for r in results if r.scrape_successful)
    logger.info(f"Scraping complete: {successful}/{len(results)} successful")

    return results


def generate_site(processor: CourseProcessor, output_dir: Path, skip_scrape: bool = False,
                  use_simple: bool = False, delay: float = 2.0):
    """
    Generate the static site.

    Args:
        processor: CourseProcessor instance
        output_dir: Output directory for generated files
        skip_scrape: If True, use previously scraped data
        use_simple: If True, use simple HTTP scraper instead of Playwright
        delay: Delay between requests in seconds
    """
    # Load elective courses
    electives = processor.load_elective_courses()

    if skip_scrape:
        # Load existing scraped data
        try:
            scraped = processor.load_raw_scraped_data()
            logger.info("Using previously scraped data")
        except FileNotFoundError:
            logger.error("No previously scraped data found. Run without --skip-scrape first.")
            sys.exit(1)
    else:
        # Scrape fresh data
        if use_simple:
            scraped = scrape_all_courses_simple(processor, delay)
        else:
            try:
                scraped = asyncio.run(scrape_all_courses_playwright(processor, delay))
            except Exception as e:
                logger.warning(f"Playwright scraper failed: {e}")
                logger.info("Falling back to simple scraper...")
                scraped = scrape_all_courses_simple(processor, delay)

    # Enrich courses with catalog data
    enriched = processor.enrich_courses(electives, scraped)

    # Generate report
    report = processor.generate_report(enriched)
    processor.save_report(report)

    # Generate HTML
    template_dir = PROJECT_DIR / "templates"
    generator = HTMLGenerator(template_dir, output_dir)

    generated_files = generator.generate_all(report)

    logger.info(f"Generated files:")
    logger.info(f"  - Index: {generated_files['index']}")
    logger.info(f"  - Course pages: {len(generated_files['courses'])}")
    logger.info(f"  - JSON export: {generated_files['json']}")

    # Print summary
    print("\n" + "=" * 60)
    print("UK COURSE SCRAPER - GENERATION COMPLETE")
    print("=" * 60)
    print(f"Total courses: {report.total_courses}")
    print(f"Successfully scraped: {report.successfully_scraped}")
    print(f"Failed scrapes: {report.failed_scrapes}")
    print(f"Success rate: {report.successfully_scraped / report.total_courses * 100:.1f}%")
    print(f"\nOutput directory: {output_dir}")
    print("=" * 60)

    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="UK Course Scraper and Site Generator")
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip scraping and use previously scraped data"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_DIR / "docs",
        help="Output directory for generated site (default: docs)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--use-simple",
        action="store_true",
        help="Use simple HTTP scraper instead of Playwright (no JS rendering)"
    )

    args = parser.parse_args()

    # Initialize processor
    data_dir = PROJECT_DIR / "data"
    processor = CourseProcessor(data_dir)

    # Generate site
    generate_site(processor, args.output_dir, args.skip_scrape, args.use_simple, args.delay)


if __name__ == "__main__":
    main()
