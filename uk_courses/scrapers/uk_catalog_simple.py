"""
Simple UK Catalog Scraper using requests.

This is a fallback scraper that works without JavaScript rendering.
It uses the direct course search and preview endpoints.
"""
import logging
import re
import time
from datetime import datetime
from typing import Optional, List, Tuple, Dict
import requests
from bs4 import BeautifulSoup

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from models import ScrapedCourseInfo

logger = logging.getLogger(__name__)


class UKCatalogSimpleScraper:
    """
    Simple scraper for UK course catalog using requests.

    Uses direct HTTP requests to the catalog API endpoints.
    """

    BASE_URL = "https://catalog.uky.edu"
    # Current catalog ID - check https://catalog.uky.edu for current value
    CATALOG_ID = 75

    # Direct course search API endpoint
    SEARCH_URL = "https://catalog.uky.edu/search_advanced.php"

    # Headers to mimic browser
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    def __init__(self, timeout: int = 30, retry_count: int = 3):
        """
        Initialize scraper.

        Args:
            timeout: Request timeout in seconds
            retry_count: Number of retries on failure
        """
        self.timeout = timeout
        self.retry_count = retry_count
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _parse_course_code(self, code: str) -> Tuple[str, str]:
        """Parse course code into prefix and number."""
        parts = code.strip().split()
        if len(parts) >= 2:
            return parts[0].upper(), parts[1]
        match = re.match(r'([A-Za-z]+)\s*(\d+)', code)
        if match:
            return match.group(1).upper(), match.group(2)
        return code.upper(), ""

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
        """Make a request with retry logic."""
        for attempt in range(self.retry_count):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        return None

    def search_course(self, course_code: str) -> Optional[str]:
        """
        Search for a course and return the detail page URL.

        Args:
            course_code: Course code like "ANT 337"

        Returns:
            URL to course detail page or None
        """
        prefix, number = self._parse_course_code(course_code)
        search_term = f"{prefix} {number}"

        params = {
            "cur_cat_oid": self.CATALOG_ID,
            "search_database": "Search",
            "search_db": "Search",
            "cpage": 1,
            "ecpage": 1,
            "ppage": 1,
            "spage": 1,
            "tpage": 1,
            "location": 3,
            "filter[keyword]": search_term,
        }

        logger.info(f"Searching for course: {course_code}")

        response = self._make_request(self.SEARCH_URL, params)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for course links - they typically contain "preview_course" in href
        # or have onclick handlers with showCourse
        target_pattern = rf'{prefix}\s*{number}'

        # Try finding links with preview_course
        for link in soup.find_all('a', href=re.compile(r'preview_course')):
            text = link.get_text()
            if re.search(target_pattern, text, re.IGNORECASE):
                href = link.get('href')
                if href:
                    if href.startswith('http'):
                        return href
                    return f"{self.BASE_URL}/{href.lstrip('/')}"

        # Try finding links with onclick handlers
        for link in soup.find_all('a', onclick=re.compile(r'showCourse')):
            text = link.get_text()
            if re.search(target_pattern, text, re.IGNORECASE):
                onclick = link.get('onclick')
                # Parse showCourse('75', '123456') pattern
                match = re.search(r"showCourse\s*\(\s*'(\d+)'\s*,\s*'(\d+)'", onclick)
                if match:
                    cat_oid, coid = match.groups()
                    return f"{self.BASE_URL}/preview_course_nopop.php?catoid={cat_oid}&coid={coid}"

        # Try a more permissive search - look in the whole page for course patterns
        for link in soup.find_all('a'):
            text = link.get_text()
            href = link.get('href', '')
            if re.search(target_pattern, text, re.IGNORECASE) and 'preview' in href.lower():
                if href.startswith('http'):
                    return href
                return f"{self.BASE_URL}/{href.lstrip('/')}"

        logger.warning(f"Course not found in search results: {course_code}")
        return None

    def scrape_course_detail(self, detail_url: str, course_code: str) -> ScrapedCourseInfo:
        """
        Scrape course details from the detail page.

        Args:
            detail_url: URL to course detail page
            course_code: Original course code

        Returns:
            ScrapedCourseInfo with course data
        """
        prefix, number = self._parse_course_code(course_code)

        response = self._make_request(detail_url)
        if not response:
            return ScrapedCourseInfo(
                code=course_code,
                prefix=prefix,
                number=number,
                title=course_code,
                scraped_at=datetime.utcnow(),
                scrape_successful=False,
                error_message="Failed to fetch course detail page"
            )

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract course title
        title = ""
        # Try various selectors for title
        for selector in ['h1', 'h2', 'h3', '.course_title', '#course_preview_title', 'td.block_content_popup h1']:
            elem = soup.select_one(selector)
            if elem:
                title_text = elem.get_text(strip=True)
                # Extract just the title part after course code
                match = re.search(rf'{prefix}\s*{number}\s*[-–:]\s*(.+)', title_text, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    break
                elif title_text:
                    title = title_text
                    break

        # Get the main body content
        body_text = ""
        for selector in ['.courseblock', '.block_content', '#course_preview_body', 'td.block_content_popup', '.course-content']:
            elem = soup.select_one(selector)
            if elem:
                body_text = elem.get_text(separator='\n', strip=True)
                break

        if not body_text:
            # Fallback - get all text from body
            body = soup.find('body')
            if body:
                body_text = body.get_text(separator='\n', strip=True)

        # Parse fields
        description = self._extract_description(body_text)
        credits = self._extract_field(body_text, r'(?:Credits?|Credit Hours?|Hours?):\s*([\d\-\s]+)', r'(\d+(?:\s*-\s*\d+)?)\s*(?:credit|hour)')
        prerequisites = self._extract_field(body_text, r'Prereq(?:uisite)?s?:\s*([^\n]+)')
        corequisites = self._extract_field(body_text, r'Coreq(?:uisite)?s?:\s*([^\n]+)')
        crosslisted = self._extract_field(body_text, r'Cross[- ]?listed?\s*(?:as|with)?:?\s*([^\n]+)', r'Same\s+as:?\s*([^\n]+)')
        offered = self._extract_field(body_text, r'(?:Typically\s+)?Offered:\s*([^\n]+)')
        grading = self._extract_field(body_text, r'Grading(?:\s+Basis)?:\s*([^\n]+)')
        repeatable = bool(re.search(r'may\s+be\s+repeated', body_text, re.IGNORECASE))

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

    def _extract_description(self, text: str) -> Optional[str]:
        """Extract course description from body text."""
        if not text:
            return None

        lines = text.split('\n')
        description_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Stop at labeled fields
            if re.match(r'^(Prereq|Coreq|Credit|Hour|Offered|Cross|Same as|Grading|Repeat|Lecture|May be|Course|Typically)', line, re.IGNORECASE):
                break
            # Skip the course title line
            if re.match(r'^[A-Z]{2,4}\s+\d{3}', line):
                continue
            description_lines.append(line)

        description = ' '.join(description_lines).strip()
        description = re.sub(r'\s+', ' ', description)
        return description if len(description) > 20 else None

    def _extract_field(self, text: str, *patterns: str) -> Optional[str]:
        """Extract a field using regex patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                value = re.sub(r'\s+', ' ', value)
                value = value.rstrip('.')
                if value and len(value) > 1:
                    return value
        return None

    def scrape_course(self, course_code: str) -> ScrapedCourseInfo:
        """
        Scrape a single course by its code.

        Args:
            course_code: Course code like "ANT 337"

        Returns:
            ScrapedCourseInfo with course data
        """
        prefix, number = self._parse_course_code(course_code)

        # Search for the course
        detail_url = self.search_course(course_code)

        if detail_url:
            return self.scrape_course_detail(detail_url, course_code)
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

    def scrape_courses(self, course_codes: List[str], delay_between: float = 2.0) -> List[ScrapedCourseInfo]:
        """
        Scrape multiple courses.

        Args:
            course_codes: List of course codes
            delay_between: Delay between requests in seconds

        Returns:
            List of ScrapedCourseInfo objects
        """
        results = []

        for i, code in enumerate(course_codes):
            logger.info(f"Scraping course {i+1}/{len(course_codes)}: {code}")
            result = self.scrape_course(code)
            results.append(result)

            # Rate limiting
            if i < len(course_codes) - 1:
                time.sleep(delay_between)

        return results


def main():
    """Test the simple scraper."""
    logging.basicConfig(level=logging.INFO)

    test_courses = ["ANT 337", "BSC 301", "CED 515"]
    scraper = UKCatalogSimpleScraper()

    for code in test_courses:
        print(f"\n{'='*60}")
        result = scraper.scrape_course(code)
        print(f"Course: {result.code}")
        print(f"Title: {result.title}")
        print(f"Credits: {result.credits}")
        print(f"Description: {result.description[:200] if result.description else 'N/A'}...")
        print(f"Prerequisites: {result.prerequisites}")
        print(f"Success: {result.scrape_successful}")
        if result.error_message:
            print(f"Error: {result.error_message}")
        time.sleep(2)


if __name__ == "__main__":
    main()
