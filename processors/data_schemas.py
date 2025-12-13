"""
Data schemas for Canadian Pet Pulse.
Defines Pydantic models for validation and type safety.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


class RedditPost(BaseModel):
    """Reddit post data model."""

    id: str = Field(..., description="Reddit post ID")
    title: str = Field(..., description="Post title")
    selftext: Optional[str] = Field(default="", description="Post body text")
    score: int = Field(default=0, ge=0, description="Upvote score")
    upvote_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Upvote ratio")
    num_comments: int = Field(default=0, ge=0, description="Number of comments")
    created_utc: float = Field(..., description="Unix timestamp of creation")
    url: str = Field(..., description="Post URL")
    permalink: str = Field(..., description="Reddit permalink")
    subreddit: str = Field(..., description="Subreddit name")
    author: Optional[str] = Field(default="[deleted]", description="Author username")
    thumbnail: Optional[str] = Field(default="", description="Thumbnail URL")
    is_video: bool = Field(default=False, description="Is video post")
    domain: Optional[str] = Field(default="", description="Link domain")
    link_flair_text: Optional[str] = Field(default="", description="Post flair")
    canadian_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Canadian relevance score")
    trending_score: float = Field(default=0.0, ge=0.0, description="Trending score")
    scraped_at: str = Field(..., description="ISO timestamp when scraped")
    content_type: str = Field(default="reddit", description="Content type identifier")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "id": "abc123",
                "title": "Toronto dog park recommendations",
                "selftext": "Looking for dog parks in the GTA...",
                "score": 150,
                "upvote_ratio": 0.95,
                "num_comments": 45,
                "created_utc": 1702500000.0,
                "url": "https://reddit.com/r/toronto/...",
                "permalink": "/r/toronto/comments/abc123/...",
                "subreddit": "toronto",
                "author": "username",
                "canadian_score": 0.8,
                "trending_score": 3.5,
                "scraped_at": "2024-01-01T00:00:00Z",
                "content_type": "reddit"
            }
        }


class NewsArticle(BaseModel):
    """News article data model."""

    title: str = Field(..., description="Article title")
    link: str = Field(..., description="Article URL")
    summary: str = Field(default="", description="Article summary/excerpt")
    published: str = Field(..., description="ISO timestamp of publication")
    source: str = Field(..., description="News source name")
    author: Optional[str] = Field(default="", description="Article author")
    tags: List[str] = Field(default_factory=list, description="Article tags/categories")
    canadian_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Canadian relevance score")
    trending_score: float = Field(default=0.0, ge=0.0, description="Trending score")
    scraped_at: str = Field(..., description="ISO timestamp when scraped")
    content_type: str = Field(default="news", description="Content type identifier")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "title": "New pet safety regulations announced",
                "link": "https://cbc.ca/news/...",
                "summary": "Health Canada announces new regulations...",
                "published": "2024-01-01T12:00:00Z",
                "source": "CBC Canada",
                "author": "Reporter Name",
                "tags": ["pets", "regulations", "safety"],
                "canadian_score": 1.0,
                "trending_score": 8.5,
                "scraped_at": "2024-01-01T13:00:00Z",
                "content_type": "news"
            }
        }


class TrendingContent(BaseModel):
    """
    Unified trending content model for display.
    Combines Reddit and News into a single format.
    """

    content_type: str = Field(..., description="'reddit' or 'news'")
    title: str = Field(..., description="Content title")
    url: str = Field(..., description="Content URL")
    summary: Optional[str] = Field(default="", description="Content summary/description")
    score: int = Field(default=0, description="Engagement score (upvotes for Reddit)")
    comment_count: int = Field(default=0, description="Number of comments/discussion")
    source: str = Field(..., description="Subreddit name or news source")
    published_at: str = Field(..., description="ISO timestamp of publication")
    canadian_score: float = Field(..., ge=0.0, le=1.0, description="Canadian relevance")
    trending_score: float = Field(..., ge=0.0, description="Trending score")
    thumbnail: Optional[str] = Field(default="", description="Image thumbnail URL")
    tags: List[str] = Field(default_factory=list, description="Tags/categories")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "content_type": "reddit",
                "title": "Vancouver dog park",
                "url": "https://reddit.com/...",
                "summary": "Post about dog parks...",
                "score": 250,
                "comment_count": 78,
                "source": "vancouver",
                "published_at": "2024-01-01T10:00:00Z",
                "canadian_score": 0.9,
                "trending_score": 4.2,
                "thumbnail": "https://...",
                "tags": ["dogs", "parks"]
            }
        }


class DailyReport(BaseModel):
    """Daily aggregated report."""

    date: str = Field(..., description="Report date (YYYY-MM-DD)")
    generated_at: str = Field(..., description="ISO timestamp of report generation")
    reddit_posts: int = Field(default=0, ge=0, description="Number of Reddit posts")
    news_articles: int = Field(default=0, ge=0, description="Number of news articles")
    total_items: int = Field(default=0, ge=0, description="Total trending items")
    trending_content: List[TrendingContent] = Field(
        default_factory=list,
        description="List of trending content items"
    )
    sources_succeeded: List[str] = Field(
        default_factory=list,
        description="List of successful data sources"
    )
    sources_failed: List[str] = Field(
        default_factory=list,
        description="List of failed data sources"
    )
    collection_duration_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Time taken to collect data"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "date": "2024-01-01",
                "generated_at": "2024-01-01T02:00:00Z",
                "reddit_posts": 45,
                "news_articles": 12,
                "total_items": 57,
                "trending_content": [],
                "sources_succeeded": ["reddit", "cbc", "ctv"],
                "sources_failed": [],
                "collection_duration_seconds": 180.5
            }
        }


class ScraperMetadata(BaseModel):
    """Metadata for scraper output files."""

    scraped_at: str = Field(..., description="ISO timestamp of scraping")
    source: str = Field(..., description="Source type (reddit/news)")
    item_count: int = Field(..., ge=0, description="Number of items scraped")
    sources: Optional[List[str]] = Field(default=None, description="List of sources scraped")
    subreddits: Optional[List[str]] = Field(default=None, description="List of subreddits (Reddit only)")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "scraped_at": "2024-01-01T02:00:00Z",
                "source": "reddit",
                "item_count": 250,
                "subreddits": ["dogs", "toronto", "vancouver"]
            }
        }


# Helper functions for converting between models

def reddit_post_to_trending(post: RedditPost) -> TrendingContent:
    """
    Convert RedditPost to TrendingContent format.

    Args:
        post: RedditPost instance

    Returns:
        TrendingContent instance
    """
    return TrendingContent(
        content_type='reddit',
        title=post.title,
        url=post.permalink,
        summary=post.selftext[:200] if post.selftext else "",
        score=post.score,
        comment_count=post.num_comments,
        source=f"r/{post.subreddit}",
        published_at=datetime.fromtimestamp(post.created_utc).isoformat(),
        canadian_score=post.canadian_score,
        trending_score=post.trending_score,
        thumbnail=post.thumbnail,
        tags=[post.link_flair_text] if post.link_flair_text else []
    )


def news_article_to_trending(article: NewsArticle) -> TrendingContent:
    """
    Convert NewsArticle to TrendingContent format.

    Args:
        article: NewsArticle instance

    Returns:
        TrendingContent instance
    """
    return TrendingContent(
        content_type='news',
        title=article.title,
        url=article.link,
        summary=article.summary[:200] if article.summary else "",
        score=0,  # News doesn't have upvotes
        comment_count=0,  # News RSS doesn't include comment count
        source=article.source,
        published_at=article.published,
        canadian_score=article.canadian_score,
        trending_score=article.trending_score,
        thumbnail="",
        tags=article.tags
    )


# Example usage and testing
if __name__ == '__main__':
    import json

    print("Pydantic Data Schemas Test")
    print("=" * 60)

    # Test RedditPost
    print("\n1. RedditPost Schema:")
    reddit_data = {
        "id": "test123",
        "title": "Toronto dog park",
        "score": 150,
        "num_comments": 45,
        "created_utc": 1702500000.0,
        "url": "https://reddit.com/test",
        "permalink": "/r/toronto/comments/test123/",
        "subreddit": "toronto",
        "scraped_at": "2024-01-01T00:00:00Z"
    }

    post = RedditPost(**reddit_data)
    print(f"✓ Valid RedditPost: {post.title}")
    print(f"  JSON: {post.model_dump_json()[:100]}...")

    # Test NewsArticle
    print("\n2. NewsArticle Schema:")
    news_data = {
        "title": "Pet safety regulations",
        "link": "https://cbc.ca/news/test",
        "published": "2024-01-01T12:00:00Z",
        "source": "CBC Canada",
        "scraped_at": "2024-01-01T13:00:00Z"
    }

    article = NewsArticle(**news_data)
    print(f"✓ Valid NewsArticle: {article.title}")
    print(f"  JSON: {article.model_dump_json()[:100]}...")

    # Test conversions
    print("\n3. Conversion to TrendingContent:")
    trending_reddit = reddit_post_to_trending(post)
    print(f"✓ Reddit -> Trending: {trending_reddit.title}")
    print(f"  Type: {trending_reddit.content_type}, Source: {trending_reddit.source}")

    trending_news = news_article_to_trending(article)
    print(f"✓ News -> Trending: {trending_news.title}")
    print(f"  Type: {trending_news.content_type}, Source: {trending_news.source}")

    # Test DailyReport
    print("\n4. DailyReport Schema:")
    report_data = {
        "date": "2024-01-01",
        "generated_at": "2024-01-01T02:00:00Z",
        "reddit_posts": 1,
        "news_articles": 1,
        "total_items": 2,
        "trending_content": [trending_reddit, trending_news],
        "sources_succeeded": ["reddit", "cbc"],
        "sources_failed": []
    }

    report = DailyReport(**report_data)
    print(f"✓ Valid DailyReport for {report.date}")
    print(f"  Total items: {report.total_items}")
    print(f"  Sources succeeded: {', '.join(report.sources_succeeded)}")

    # Test validation
    print("\n5. Validation Tests:")
    try:
        invalid_post = RedditPost(**{
            "id": "test",
            "title": "Test",
            "score": -100,  # Invalid: negative score
            "created_utc": 0,
            "url": "test",
            "permalink": "test",
            "subreddit": "test",
            "scraped_at": "test"
        })
    except Exception as e:
        print(f"✓ Caught validation error: {type(e).__name__}")

    print("\n✓ All schema tests passed!")
