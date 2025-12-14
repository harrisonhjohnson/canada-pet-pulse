"""
News scraper for Canadian news sources.
Uses RSS feeds to collect pet-related articles.
"""

import feedparser
import requests
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging
from bs4 import BeautifulSoup

from scrapers.base_scraper import retry_on_failure, BaseScraper

logger = logging.getLogger(__name__)


class NewsScraper(BaseScraper):
    """
    Scrapes Canadian news sources for pet-related content via RSS feeds.
    """

    USER_AGENT = "CanadianPetPulse/0.1.0 (Educational Project; Pet Content Aggregator)"

    # RSS feed sources
    RSS_FEEDS = {
        # Direct news feeds (reliable, no blocking)
        'Global News': 'https://globalnews.ca/feed/',

        # Google News RSS (aggregates multiple Canadian sources)
        'Google News - Dogs Canada': 'https://news.google.com/rss/search?q=dogs+canada&hl=en-CA&gl=CA&ceid=CA:en',
        'Google News - Cats Canada': 'https://news.google.com/rss/search?q=cats+canada&hl=en-CA&gl=CA&ceid=CA:en',
        'Google News - Pets Canada': 'https://news.google.com/rss/search?q=pets+canada&hl=en-CA&gl=CA&ceid=CA:en',
    }

    # Pet-related keywords for filtering
    PET_KEYWORDS = [
        'dog', 'dogs', 'puppy', 'puppies', 'canine',
        'cat', 'cats', 'kitten', 'kittens', 'feline',
        'pet', 'pets', 'animal', 'animals',
        'veterinary', 'vet', 'veterinarian',
        'rescue', 'shelter', 'adoption',
        'paw', 'tail', 'fur', 'breed',
        'collar', 'leash',
    ]

    def __init__(self):
        """Initialize news scraper."""
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.USER_AGENT})

    @retry_on_failure(max_retries=3, delay=5.0)
    def scrape_rss_feed(self, feed_url: str, source_name: str) -> List[Dict]:
        """
        Scrape and parse an RSS feed, filtering for pet-related content.

        Args:
            feed_url: URL of the RSS feed
            source_name: Display name for the source

        Returns:
            List of pet-related article dictionaries
        """
        logger.info(f"Scraping RSS feed: {source_name}")

        # Parse feed with user agent
        feed = feedparser.parse(feed_url, agent=self.USER_AGENT)

        if not feed.entries:
            logger.warning(f"No entries found in {source_name}")
            return []

        # Filter for pet-related content
        articles = []
        for entry in feed.entries:
            if self._is_pet_related(entry):
                article = self._extract_article_data(entry, source_name)
                articles.append(article)

        logger.info(f"Found {len(articles)} pet-related articles from {source_name}")
        return articles

    def _is_pet_related(self, entry) -> bool:
        """
        Check if RSS entry is pet-related based on keywords.

        Args:
            entry: feedparser entry object

        Returns:
            True if article is pet-related
        """
        # Combine title and summary for searching
        title = entry.get('title', '').lower()
        summary = entry.get('summary', '').lower()

        # Extract tags if available
        tags = ' '.join([tag.get('term', '').lower()
                        for tag in entry.get('tags', [])])

        # Combine all searchable text
        searchable_text = f"{title} {summary} {tags}"

        # Check if any pet keyword appears
        return any(keyword in searchable_text for keyword in self.PET_KEYWORDS)

    def _extract_article_data(self, entry, source_name: str) -> Dict:
        """
        Extract relevant fields from RSS entry.

        Args:
            entry: feedparser entry object
            source_name: Name of the news source

        Returns:
            Dictionary with article data
        """
        # Parse published date
        published_parsed = entry.get('published_parsed')
        if published_parsed:
            try:
                published_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                published_dt = datetime.now(timezone.utc)
        else:
            published_dt = datetime.now(timezone.utc)

        # Clean HTML from summary
        summary = self._clean_html(entry.get('summary', ''))

        return {
            'title': self.clean_whitespace(entry.get('title', '')),
            'link': entry.get('link', ''),
            'summary': self.truncate_text(summary, max_length=500),
            'published': published_dt.isoformat(),
            'source': source_name,
            'author': entry.get('author', ''),
            'tags': [tag.get('term', '') for tag in entry.get('tags', [])],
            'scraped_at': datetime.now(timezone.utc).isoformat(),
        }

    def _clean_html(self, html_text: str) -> str:
        """
        Strip HTML tags and clean text.

        Args:
            html_text: Text with HTML tags

        Returns:
            Plain text without HTML
        """
        if not html_text:
            return ''

        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return self.clean_whitespace(text)
        except Exception as e:
            logger.warning(f"Error cleaning HTML: {e}")
            return html_text

    def scrape_all(self, feeds: Optional[Dict[str, str]] = None) -> List[Dict]:
        """
        Scrape all configured news sources.

        Args:
            feeds: Dictionary of {source_name: feed_url} (uses default if None)

        Returns:
            List of all articles from all sources
        """
        if feeds is None:
            feeds = self.RSS_FEEDS

        all_articles = []
        failed_sources = []

        logger.info(f"Starting scrape of {len(feeds)} news sources")

        for i, (source_name, feed_url) in enumerate(feeds.items(), 1):
            try:
                articles = self.scrape_rss_feed(feed_url, source_name)
                all_articles.extend(articles)

                logger.info(f"[{i}/{len(feeds)}] {source_name}: {len(articles)} articles")

            except Exception as e:
                logger.error(f"Failed to scrape {source_name}: {e}")
                failed_sources.append(source_name)

        # Summary
        success_count = len(feeds) - len(failed_sources)
        logger.info(
            f"Scraping complete: {success_count}/{len(feeds)} sources, "
            f"{len(all_articles)} total articles"
        )

        if failed_sources:
            logger.warning(f"Failed sources: {', '.join(failed_sources)}")

        return all_articles

    def save_to_json(self, articles: List[Dict], filepath: str):
        """
        Save articles to JSON file with metadata.

        Args:
            articles: List of article dictionaries
            filepath: Path to output JSON file
        """
        output = {
            'scraped_at': datetime.now(timezone.utc).isoformat(),
            'source': 'news',
            'article_count': len(articles),
            'sources': list(set(a['source'] for a in articles)),
            'articles': articles
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(articles)} articles to {filepath}")

    def get_article_statistics(self, articles: List[Dict]) -> Dict:
        """
        Calculate statistics about scraped articles.

        Args:
            articles: List of article dictionaries

        Returns:
            Dictionary with statistics
        """
        if not articles:
            return {
                'total_articles': 0,
                'sources': [],
                'source_count': 0,
            }

        sources = list(set(a['source'] for a in articles))

        # Count articles per source
        source_counts = {}
        for article in articles:
            source = article['source']
            source_counts[source] = source_counts.get(source, 0) + 1

        return {
            'total_articles': len(articles),
            'sources': sorted(sources),
            'source_count': len(sources),
            'articles_per_source': source_counts,
        }


# Example usage
if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test scraper
    scraper = NewsScraper()

    # Test single feed
    print("Testing single RSS feed scrape...")
    articles = scraper.scrape_rss_feed(
        'https://www.cbc.ca/webfeed/rss/rss-canada',
        'CBC Canada'
    )
    print(f"Retrieved {len(articles)} pet-related articles from CBC Canada")

    if articles:
        print(f"\nSample article:")
        sample = articles[0]
        print(f"  Title: {sample['title']}")
        print(f"  Source: {sample['source']}")
        print(f"  Published: {sample['published']}")
        print(f"  Summary: {sample['summary'][:100]}...")

    # Test statistics
    stats = scraper.get_article_statistics(articles)
    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
