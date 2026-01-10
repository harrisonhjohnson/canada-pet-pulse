"""
Course Processor - Combines elective list with scraped catalog data.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from models import ElectiveCourse, ScrapedCourseInfo, EnrichedCourse, CourseReport

logger = logging.getLogger(__name__)


class CourseProcessor:
    """Process and combine course data from different sources."""

    def __init__(self, data_dir: Path):
        """
        Initialize processor.

        Args:
            data_dir: Path to data directory
        """
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"

        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def load_elective_courses(self) -> List[ElectiveCourse]:
        """Load the elective course list."""
        electives_file = self.data_dir / "elective_courses.json"

        if not electives_file.exists():
            raise FileNotFoundError(f"Elective courses file not found: {electives_file}")

        with open(electives_file, 'r') as f:
            data = json.load(f)

        courses = []
        for course_data in data.get("courses", []):
            courses.append(ElectiveCourse(**course_data))

        logger.info(f"Loaded {len(courses)} elective courses")
        return courses

    def save_raw_scraped_data(self, scraped_data: List[ScrapedCourseInfo], date_str: Optional[str] = None) -> Path:
        """
        Save raw scraped data to file.

        Args:
            scraped_data: List of scraped course info
            date_str: Date string for filename (defaults to today)

        Returns:
            Path to saved file
        """
        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y%m%d")

        filename = self.raw_dir / f"scraped_courses_{date_str}.json"

        data = {
            "scraped_at": datetime.utcnow().isoformat(),
            "course_count": len(scraped_data),
            "successful": sum(1 for c in scraped_data if c.scrape_successful),
            "failed": sum(1 for c in scraped_data if not c.scrape_successful),
            "courses": [c.model_dump() for c in scraped_data]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved raw scraped data to {filename}")
        return filename

    def load_raw_scraped_data(self, date_str: Optional[str] = None) -> List[ScrapedCourseInfo]:
        """
        Load previously scraped data.

        Args:
            date_str: Date string for filename (defaults to most recent)

        Returns:
            List of scraped course info
        """
        if date_str:
            filename = self.raw_dir / f"scraped_courses_{date_str}.json"
        else:
            # Find most recent
            files = sorted(self.raw_dir.glob("scraped_courses_*.json"), reverse=True)
            if not files:
                raise FileNotFoundError("No scraped data files found")
            filename = files[0]

        with open(filename, 'r') as f:
            data = json.load(f)

        courses = []
        for course_data in data.get("courses", []):
            # Handle datetime serialization
            if isinstance(course_data.get('scraped_at'), str):
                course_data['scraped_at'] = datetime.fromisoformat(course_data['scraped_at'].replace('Z', '+00:00'))
            courses.append(ScrapedCourseInfo(**course_data))

        logger.info(f"Loaded {len(courses)} scraped courses from {filename}")
        return courses

    def enrich_courses(
        self,
        electives: List[ElectiveCourse],
        scraped: List[ScrapedCourseInfo]
    ) -> List[EnrichedCourse]:
        """
        Combine elective list with scraped catalog data.

        Args:
            electives: List of elective courses
            scraped: List of scraped course info

        Returns:
            List of enriched courses
        """
        # Build lookup by code
        scraped_lookup: Dict[str, ScrapedCourseInfo] = {}
        for course in scraped:
            # Normalize code for lookup
            code_normalized = course.code.upper().replace(" ", "")
            scraped_lookup[code_normalized] = course

        enriched = []
        for elective in electives:
            code_normalized = elective.code.upper().replace(" ", "")
            catalog_info = scraped_lookup.get(code_normalized)

            enriched_course = EnrichedCourse(
                code=elective.code,
                name=elective.name,
                notes=elective.notes,
                catalog_info=catalog_info
            )
            enriched.append(enriched_course)

        logger.info(f"Enriched {len(enriched)} courses, {sum(1 for c in enriched if c.has_catalog_data)} with catalog data")
        return enriched

    def generate_report(self, enriched_courses: List[EnrichedCourse]) -> CourseReport:
        """
        Generate a full course report.

        Args:
            enriched_courses: List of enriched courses

        Returns:
            CourseReport object
        """
        successful = sum(1 for c in enriched_courses if c.has_catalog_data)
        failed = len(enriched_courses) - successful

        report = CourseReport(
            program="University of Kentucky Elective Courses",
            generated_at=datetime.utcnow(),
            total_courses=len(enriched_courses),
            successfully_scraped=successful,
            failed_scrapes=failed,
            courses=enriched_courses
        )

        return report

    def save_report(self, report: CourseReport, date_str: Optional[str] = None) -> Path:
        """
        Save the course report.

        Args:
            report: CourseReport object
            date_str: Date string for filename

        Returns:
            Path to saved file
        """
        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y%m%d")

        filename = self.processed_dir / f"course_report_{date_str}.json"

        # Custom serialization for nested models
        def serialize_course(course: EnrichedCourse) -> dict:
            result = {
                "code": course.code,
                "name": course.name,
                "notes": course.notes,
                "has_catalog_data": course.has_catalog_data,
            }
            if course.catalog_info:
                result["catalog_info"] = course.catalog_info.model_dump()
            else:
                result["catalog_info"] = None
            return result

        data = {
            "program": report.program,
            "generated_at": report.generated_at.isoformat(),
            "total_courses": report.total_courses,
            "successfully_scraped": report.successfully_scraped,
            "failed_scrapes": report.failed_scrapes,
            "courses": [serialize_course(c) for c in report.courses]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved course report to {filename}")
        return filename

    def get_course_codes(self) -> List[str]:
        """Get list of course codes from elective list."""
        electives = self.load_elective_courses()
        return [e.code for e in electives]
