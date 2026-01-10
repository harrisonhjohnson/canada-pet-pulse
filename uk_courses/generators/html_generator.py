"""
HTML Generator for UK Course Reports.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from models import CourseReport

logger = logging.getLogger(__name__)


class HTMLGenerator:
    """Generate HTML pages from course reports."""

    def __init__(self, template_dir: Path, output_dir: Path):
        """
        Initialize generator.

        Args:
            template_dir: Path to Jinja2 templates
            output_dir: Path to output directory
        """
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )

        # Add custom filters
        self.env.filters['format_datetime'] = self._format_datetime
        self.env.filters['truncate_text'] = self._truncate_text

    def _format_datetime(self, value: datetime, fmt: str = "%B %d, %Y at %I:%M %p UTC") -> str:
        """Format datetime for display."""
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value.strftime(fmt)

    def _truncate_text(self, text: Optional[str], length: int = 200) -> str:
        """Truncate text with ellipsis."""
        if not text:
            return ""
        if len(text) <= length:
            return text
        return text[:length].rsplit(' ', 1)[0] + "..."

    def generate_index(self, report: CourseReport) -> Path:
        """
        Generate the main index page.

        Args:
            report: CourseReport object

        Returns:
            Path to generated file
        """
        template = self.env.get_template("index.html")

        # Sort courses: successful scrapes first, then by code
        sorted_courses = sorted(
            report.courses,
            key=lambda c: (not c.has_catalog_data, c.code)
        )

        html = template.render(
            report=report,
            courses=sorted_courses,
            generated_at=report.generated_at,
            success_rate=round(report.successfully_scraped / report.total_courses * 100, 1) if report.total_courses > 0 else 0
        )

        output_path = self.output_dir / "index.html"
        with open(output_path, 'w') as f:
            f.write(html)

        logger.info(f"Generated index page: {output_path}")
        return output_path

    def generate_course_pages(self, report: CourseReport) -> list:
        """
        Generate individual course pages.

        Args:
            report: CourseReport object

        Returns:
            List of paths to generated files
        """
        template = self.env.get_template("course.html")
        pages = []

        courses_dir = self.output_dir / "courses"
        courses_dir.mkdir(exist_ok=True)

        for course in report.courses:
            if not course.has_catalog_data:
                continue

            # Create filename from course code
            filename = course.code.replace(" ", "_").lower() + ".html"
            output_path = courses_dir / filename

            html = template.render(
                course=course,
                generated_at=report.generated_at
            )

            with open(output_path, 'w') as f:
                f.write(html)

            pages.append(output_path)

        logger.info(f"Generated {len(pages)} course pages")
        return pages

    def generate_json_export(self, report: CourseReport) -> Path:
        """
        Generate JSON export for API/programmatic access.

        Args:
            report: CourseReport object

        Returns:
            Path to generated file
        """
        output_path = self.output_dir / "data.json"

        # Build simplified export
        export_data = {
            "program": report.program,
            "generated_at": report.generated_at.isoformat(),
            "stats": {
                "total": report.total_courses,
                "with_catalog_data": report.successfully_scraped,
                "missing_data": report.failed_scrapes
            },
            "courses": []
        }

        for course in report.courses:
            course_data = {
                "code": course.code,
                "name": course.name,
                "notes": course.notes,
                "has_catalog_data": course.has_catalog_data
            }

            if course.catalog_info:
                course_data.update({
                    "title": course.catalog_info.title,
                    "credits": course.catalog_info.credits,
                    "description": course.catalog_info.description,
                    "prerequisites": course.catalog_info.prerequisites,
                    "corequisites": course.catalog_info.corequisites,
                    "crosslisted": course.catalog_info.crosslisted,
                    "offered": course.catalog_info.offered,
                    "catalog_url": course.catalog_info.catalog_url
                })

            export_data["courses"].append(course_data)

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Generated JSON export: {output_path}")
        return output_path

    def generate_all(self, report: CourseReport) -> dict:
        """
        Generate all output files.

        Args:
            report: CourseReport object

        Returns:
            Dict with paths to generated files
        """
        return {
            "index": self.generate_index(report),
            "courses": self.generate_course_pages(report),
            "json": self.generate_json_export(report)
        }

    def copy_static_assets(self) -> None:
        """Copy CSS and other static files."""
        # Generate inline CSS in template for simplicity
        pass
