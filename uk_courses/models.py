"""
Pydantic models for UK Course data.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl


class ElectiveCourse(BaseModel):
    """Input course from the elective list."""
    code: str = Field(..., description="Course code (e.g., 'ANT 337')")
    name: str = Field(..., description="Course name from elective list")
    notes: Optional[str] = Field(None, description="Any special notes about the course")


class ScrapedCourseInfo(BaseModel):
    """Scraped course information from UK catalog."""
    code: str = Field(..., description="Course code")
    prefix: str = Field(..., description="Course prefix (e.g., 'ANT')")
    number: str = Field(..., description="Course number (e.g., '337')")
    title: str = Field(..., description="Official course title")
    credits: Optional[str] = Field(None, description="Credit hours")
    description: Optional[str] = Field(None, description="Course description")
    prerequisites: Optional[str] = Field(None, description="Prerequisites")
    corequisites: Optional[str] = Field(None, description="Corequisites")
    crosslisted: Optional[str] = Field(None, description="Cross-listed courses")
    offered: Optional[str] = Field(None, description="When the course is offered")
    grading: Optional[str] = Field(None, description="Grading basis")
    repeatable: Optional[bool] = Field(None, description="Whether course is repeatable")
    catalog_url: Optional[str] = Field(None, description="URL to catalog page")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    scrape_successful: bool = Field(True, description="Whether scraping succeeded")
    error_message: Optional[str] = Field(None, description="Error message if scraping failed")


class EnrichedCourse(BaseModel):
    """Combined elective info with scraped catalog data."""
    code: str
    name: str
    notes: Optional[str]
    catalog_info: Optional[ScrapedCourseInfo]

    @property
    def has_catalog_data(self) -> bool:
        return self.catalog_info is not None and self.catalog_info.scrape_successful


class CourseReport(BaseModel):
    """Full report of all courses."""
    program: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    total_courses: int
    successfully_scraped: int
    failed_scrapes: int
    courses: List[EnrichedCourse]
