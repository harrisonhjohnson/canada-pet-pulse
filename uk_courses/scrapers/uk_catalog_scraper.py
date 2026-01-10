"""
University of Kentucky Course Catalog Scraper.

Uses Playwright for JavaScript rendering since UK's catalog requires it.
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, List, Tuple
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from models import ScrapedCourseInfo

logger = logging.getLogger(__name__)


class UKCatalogScraper:
    """
    Scraper for University of Kentucky course catalog.

    The UK catalog is available at:
    https://catalog.uky.edu/content.php?catoid=X&navoid=Y

    Course search URL pattern:
    https://catalog.uky.edu/search_advanced.php?cur_cat_oid=75&search_database=Search&search_db=Search&cpage=1&ecpage=1&ppage=1&spage=1&tpage=1&location=3&filter%5Bkeyword%5D=ANT+337
    """

    BASE_URL = "https://catalog.uky.edu"
    # Current catalog ID - this may need updating each academic year
    CATALOG_ID = 75

    SEARCH_URL_TEMPLATE = (
        "https://catalog.uky.edu/search_advanced.php?"
        "cur_cat_oid={catalog_id}&"
        "search_database=Search&search_db=Search&"
        "cpage=1&ecpage=1&ppage=1&spage=1&tpage=1&"
        "location=3&"
        "filter%5Bkeyword%5D={search_term}"
    )

    def __init__(self, headless: bool = True, slow_mo: int = 100):
        """
        Initialize the scraper.

        Args:
            headless: Run browser in headless mode
            slow_mo: Slow down operations by this many ms (helps avoid detection)
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
        self._playwright = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._playwright = await async_playwright().start()

        # Try to find chromium executable
        import os
        chromium_paths = [
            "/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome",
            os.path.expanduser("~/.cache/ms-playwright/chromium-1194/chrome-linux/chrome"),
        ]
        executable_path = None
        for path in chromium_paths:
            if os.path.exists(path):
                executable_path = path
                break

        launch_options = {
            "headless": self.headless,
            "slow_mo": self.slow_mo,
        }
        if executable_path:
            launch_options["executable_path"] = executable_path

        self.browser = await self._playwright.chromium.launch(**launch_options)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()

    def _parse_course_code(self, code: str) -> Tuple[str, str]:
        """Parse course code into prefix and number."""
        parts = code.strip().split()
        if len(parts) >= 2:
            return parts[0].upper(), parts[1]
        # Try to split by pattern like "ANT337"
        match = re.match(r'([A-Za-z]+)\s*(\d+)', code)
        if match:
            return match.group(1).upper(), match.group(2)
        return code.upper(), ""

    async def search_course(self, page: Page, course_code: str) -> Optional[str]:
        """
        Search for a course and return the detail page URL if found.

        Args:
            page: Playwright page object
            course_code: Course code like "ANT 337"

        Returns:
            URL to course detail page, or None if not found
        """
        search_term = course_code.replace(" ", "+")
        search_url = self.SEARCH_URL_TEMPLATE.format(
            catalog_id=self.CATALOG_ID,
            search_term=search_term
        )

        logger.info(f"Searching for course: {course_code}")

        try:
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)  # Let JS settle

            # Look for course links in search results
            # UK catalog uses JavaScript popups, so we need to find the onclick handlers
            course_links = await page.query_selector_all('a[onclick*="showCourse"]')

            prefix, number = self._parse_course_code(course_code)
            target_pattern = f"{prefix}\\s*{number}"

            for link in course_links:
                text = await link.text_content()
                if text and re.search(target_pattern, text, re.IGNORECASE):
                    # Extract the course URL from onclick
                    onclick = await link.get_attribute('onclick')
                    if onclick:
                        # Parse showCourse('75', '123456') pattern
                        match = re.search(r"showCourse\s*\(\s*'(\d+)'\s*,\s*'(\d+)'", onclick)
                        if match:
                            cat_oid, coid = match.groups()
                            detail_url = f"{self.BASE_URL}/preview_course_nopop.php?catoid={cat_oid}&coid={coid}"
                            logger.info(f"Found course detail URL: {detail_url}")
                            return detail_url

            # Also try finding direct links
            all_links = await page.query_selector_all('a[href*="preview_course"]')
            for link in all_links:
                text = await link.text_content()
                if text and re.search(target_pattern, text, re.IGNORECASE):
                    href = await link.get_attribute('href')
                    if href:
                        if href.startswith('http'):
                            return href
                        return f"{self.BASE_URL}/{href.lstrip('/')}"

            logger.warning(f"Course not found in search results: {course_code}")
            return None

        except PlaywrightTimeout:
            logger.error(f"Timeout searching for course: {course_code}")
            return None
        except Exception as e:
            logger.error(f"Error searching for course {course_code}: {e}")
            return None

    async def scrape_course_detail(self, page: Page, detail_url: str, course_code: str) -> ScrapedCourseInfo:
        """
        Scrape course details from the detail page.

        Args:
            page: Playwright page object
            detail_url: URL to course detail page
            course_code: Original course code

        Returns:
            ScrapedCourseInfo with course data
        """
        prefix, number = self._parse_course_code(course_code)

        try:
            await page.goto(detail_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)

            # Get the main content area
            content = await page.content()

            # Parse course title - usually in format "PREFIX NUMBER - Title"
            title = ""
            title_elem = await page.query_selector('h1, h2, h3, .course_title, #course_preview_title')
            if title_elem:
                title_text = await title_elem.text_content()
                if title_text:
                    # Try to extract just the title part after the course code
                    match = re.search(rf'{prefix}\s*{number}\s*[-:]\s*(.+)', title_text, re.IGNORECASE)
                    if match:
                        title = match.group(1).strip()
                    else:
                        title = title_text.strip()

            # Get the course body content
            body = await page.query_selector('.courseblock, .block_content, #course_preview_body, td.block_content_popup')
            body_text = ""
            if body:
                body_text = await body.inner_text()

            # Parse various fields from body text
            description = self._extract_description(body_text)
            credits = self._extract_field(body_text, r'(?:Credits?|Credit Hours?|Hours?):\s*([\d\-\s]+)', r'(\d+(?:\s*-\s*\d+)?)\s*(?:credit|hour)', r'^\s*\((\d+(?:-\d+)?)\)')
            prerequisites = self._extract_field(body_text, r'Prereq(?:uisite)?s?:\s*([^\n]+)', r'Prerequisites?[:\s]+([^\n]+)')
            corequisites = self._extract_field(body_text, r'Coreq(?:uisite)?s?:\s*([^\n]+)')
            crosslisted = self._extract_field(body_text, r'Cross[- ]?listed?\s*(?:as|with)?:?\s*([^\n]+)', r'Same\s+as:?\s*([^\n]+)')
            offered = self._extract_field(body_text, r'(?:Typically\s+)?Offered:\s*([^\n]+)', r'Offered\s+in:?\s*([^\n]+)')
            grading = self._extract_field(body_text, r'Grading(?:\s+Basis)?:\s*([^\n]+)')
            repeatable = 'repeat' in body_text.lower() and 'may be repeated' in body_text.lower()

            return ScrapedCourseInfo(
                code=course_code,
                prefix=prefix,
                number=number,
                title=title or course_code,
                credits=credits,
                description=description,
                prerequisites=prerequisites,
                corequisites=corequisites,
                crosslisted=crosslisted,
                offered=offered,
                grading=grading,
                repeatable=repeatable,
                catalog_url=detail_url,
                scraped_at=datetime.utcnow(),
                scrape_successful=True
            )

        except Exception as e:
            logger.error(f"Error scraping course detail for {course_code}: {e}")
            return ScrapedCourseInfo(
                code=course_code,
                prefix=prefix,
                number=number,
                title=course_code,
                scraped_at=datetime.utcnow(),
                scrape_successful=False,
                error_message=str(e)
            )

    def _extract_description(self, text: str) -> Optional[str]:
        """Extract course description from body text."""
        if not text:
            return None

        # The description is usually the first paragraph before any labeled fields
        lines = text.split('\n')
        description_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Stop at labeled fields
            if re.match(r'^(Prereq|Coreq|Credit|Hour|Offered|Cross|Same as|Grading|Repeat|Lecture|May be|Course)', line, re.IGNORECASE):
                break
            # Skip the course title line
            if re.match(r'^[A-Z]{2,4}\s+\d{3}', line):
                continue
            description_lines.append(line)

        description = ' '.join(description_lines).strip()
        # Clean up
        description = re.sub(r'\s+', ' ', description)
        return description if len(description) > 20 else None

    def _extract_field(self, text: str, *patterns: str) -> Optional[str]:
        """Extract a field using multiple regex patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                # Clean up common artifacts
                value = re.sub(r'\s+', ' ', value)
                value = value.rstrip('.')
                if value and len(value) > 1:
                    return value
        return None

    async def scrape_course(self, course_code: str) -> ScrapedCourseInfo:
        """
        Scrape a single course by its code.

        Args:
            course_code: Course code like "ANT 337"

        Returns:
            ScrapedCourseInfo with course data
        """
        prefix, number = self._parse_course_code(course_code)

        if not self.browser:
            raise RuntimeError("Scraper must be used as async context manager")

        page = await self.browser.new_page()

        try:
            # Set reasonable viewport and user agent
            await page.set_viewport_size({"width": 1280, "height": 800})

            # Search for the course
            detail_url = await self.search_course(page, course_code)

            if detail_url:
                # Scrape the detail page
                return await self.scrape_course_detail(page, detail_url, course_code)
            else:
                return ScrapedCourseInfo(
                    code=course_code,
                    prefix=prefix,
                    number=number,
                    title=course_code,
                    scraped_at=datetime.utcnow(),
                    scrape_successful=False,
                    error_message="Course not found in catalog search"
                )

        finally:
            await page.close()

    async def scrape_courses(self, course_codes: List[str], delay_between: float = 2.0) -> List[ScrapedCourseInfo]:
        """
        Scrape multiple courses.

        Args:
            course_codes: List of course codes
            delay_between: Delay in seconds between requests

        Returns:
            List of ScrapedCourseInfo objects
        """
        results = []

        for i, code in enumerate(course_codes):
            logger.info(f"Scraping course {i+1}/{len(course_codes)}: {code}")
            result = await self.scrape_course(code)
            results.append(result)

            # Rate limiting
            if i < len(course_codes) - 1:
                await asyncio.sleep(delay_between)

        return results


async def main():
    """Test the scraper."""
    logging.basicConfig(level=logging.INFO)

    test_courses = ["ANT 337", "BSC 301", "CED 515"]

    async with UKCatalogScraper(headless=True) as scraper:
        results = await scraper.scrape_courses(test_courses)

        for result in results:
            print(f"\n{'='*60}")
            print(f"Course: {result.code}")
            print(f"Title: {result.title}")
            print(f"Credits: {result.credits}")
            print(f"Description: {result.description[:200] if result.description else 'N/A'}...")
            print(f"Prerequisites: {result.prerequisites}")
            print(f"Success: {result.scrape_successful}")
            if result.error_message:
                print(f"Error: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(main())
