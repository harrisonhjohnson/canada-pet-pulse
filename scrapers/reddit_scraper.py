"""
Reddit scraper using public JSON endpoints.
Collects trending posts from pet and Canadian subreddits.
"""

import requests
import time
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging

from scrapers.base_scraper import retry_on_failure, BaseScraper

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    """
    Scrapes Reddit using public JSON endpoints (no authentication required).
    """

    BASE_URL = "https://www.reddit.com"
    USER_AGENT = "CanadianPetPulse/0.1.0 (Educational Project; Pet Content Aggregator)"
    RATE_LIMIT_DELAY = 2  # seconds between requests

    # Target subreddits
    SUBREDDITS = [
        # Pet-focused
        'dogs',
        'puppy101',
        'DogTraining',
        'cats',
        'CatAdvice',

        # Canadian city subreddits
        'toronto',
        'vancouver',
        'montreal',
        'calgary',
        'ottawa',
        'Edmonton',
        'winnipeg',

        # Canadian general
        'canada',
        'onguardforthee',
    ]

    def __init__(self, rate_limit_delay: float = None):
        """
        Initialize Reddit scraper.

        Args:
            rate_limit_delay: Seconds to wait between requests (default: 2)
        """
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.USER_AGENT})

        if rate_limit_delay is not None:
            self.RATE_LIMIT_DELAY = rate_limit_delay

    @retry_on_failure(max_retries=3, delay=5.0)
    def scrape_subreddit(self, subreddit: str, time_filter: str = 'day',
                         limit: int = 25) -> List[Dict]:
        """
        Scrape top posts from a single subreddit.

        Args:
            subreddit: Subreddit name without r/ prefix
            time_filter: Time period - 'hour', 'day', 'week', 'month', 'year', 'all'
            limit: Number of posts to retrieve (max 100)

        Returns:
            List of post dictionaries

        Raises:
            requests.RequestException: If request fails after retries
        """
        url = f"{self.BASE_URL}/r/{subreddit}/top.json"
        params = {
            't': time_filter,
            'limit': min(limit, 100)  # Reddit API limit
        }

        logger.info(f"Scraping r/{subreddit} (limit={limit}, time={time_filter})")

        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Extract posts from Reddit API response
        posts = []
        children = self.safe_get(data, 'data', 'children', default=[])

        for child in children:
            post_data = child.get('data', {})
            if post_data:
                posts.append(self._extract_post_data(post_data, subreddit))

        logger.info(f"Retrieved {len(posts)} posts from r/{subreddit}")
        return posts

    def _extract_post_data(self, post: Dict, subreddit: str) -> Dict:
        """
        Extract relevant fields from Reddit post.

        Args:
            post: Raw Reddit post data from API
            subreddit: Subreddit name (for validation)

        Returns:
            Dictionary with cleaned post data
        """
        return {
            'id': post.get('id', ''),
            'title': self.clean_whitespace(post.get('title', '')),
            'selftext': self.clean_whitespace(post.get('selftext', '')),
            'score': post.get('score', 0),
            'upvote_ratio': post.get('upvote_ratio', 0.0),
            'num_comments': post.get('num_comments', 0),
            'created_utc': post.get('created_utc', 0),
            'url': post.get('url', ''),
            'permalink': f"{self.BASE_URL}{post.get('permalink', '')}",
            'subreddit': subreddit,
            'author': post.get('author', '[deleted]'),
            'thumbnail': post.get('thumbnail', ''),
            'is_video': post.get('is_video', False),
            'domain': post.get('domain', ''),
            'link_flair_text': post.get('link_flair_text', ''),
            'scraped_at': datetime.now(timezone.utc).isoformat(),
        }

    def scrape_all(self, subreddits: Optional[List[str]] = None,
                   time_filter: str = 'day', limit_per_sub: int = 25) -> List[Dict]:
        """
        Scrape all configured subreddits with rate limiting.

        Args:
            subreddits: List of subreddit names (uses default if None)
            time_filter: Time period for top posts
            limit_per_sub: Posts to retrieve per subreddit

        Returns:
            List of all posts from all subreddits
        """
        if subreddits is None:
            subreddits = self.SUBREDDITS

        all_posts = []
        failed_subreddits = []

        logger.info(f"Starting scrape of {len(subreddits)} subreddits")

        for i, subreddit in enumerate(subreddits, 1):
            try:
                posts = self.scrape_subreddit(
                    subreddit,
                    time_filter=time_filter,
                    limit=limit_per_sub
                )
                all_posts.extend(posts)

                logger.info(f"[{i}/{len(subreddits)}] r/{subreddit}: {len(posts)} posts")

            except Exception as e:
                logger.error(f"Failed to scrape r/{subreddit}: {e}")
                failed_subreddits.append(subreddit)

            # Rate limiting - wait between requests (except after last one)
            if i < len(subreddits):
                time.sleep(self.RATE_LIMIT_DELAY)

        # Summary
        success_count = len(subreddits) - len(failed_subreddits)
        logger.info(
            f"Scraping complete: {success_count}/{len(subreddits)} subreddits, "
            f"{len(all_posts)} total posts"
        )

        if failed_subreddits:
            logger.warning(f"Failed subreddits: {', '.join(failed_subreddits)}")

        return all_posts

    def save_to_json(self, posts: List[Dict], filepath: str):
        """
        Save posts to JSON file with metadata.

        Args:
            posts: List of post dictionaries
            filepath: Path to output JSON file
        """
        output = {
            'scraped_at': datetime.now(timezone.utc).isoformat(),
            'source': 'reddit',
            'post_count': len(posts),
            'subreddits': list(set(p['subreddit'] for p in posts)),
            'posts': posts
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(posts)} posts to {filepath}")

    def get_post_statistics(self, posts: List[Dict]) -> Dict:
        """
        Calculate statistics about scraped posts.

        Args:
            posts: List of post dictionaries

        Returns:
            Dictionary with statistics
        """
        if not posts:
            return {
                'total_posts': 0,
                'total_score': 0,
                'total_comments': 0,
                'avg_score': 0,
                'avg_comments': 0,
                'subreddits': []
            }

        total_score = sum(p['score'] for p in posts)
        total_comments = sum(p['num_comments'] for p in posts)
        subreddits = list(set(p['subreddit'] for p in posts))

        return {
            'total_posts': len(posts),
            'total_score': total_score,
            'total_comments': total_comments,
            'avg_score': total_score / len(posts),
            'avg_comments': total_comments / len(posts),
            'subreddits': sorted(subreddits),
            'subreddit_count': len(subreddits),
        }


# Example usage
if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test scraper
    scraper = RedditScraper()

    # Test single subreddit
    print("Testing single subreddit scrape...")
    posts = scraper.scrape_subreddit('dogs', limit=10)
    print(f"Retrieved {len(posts)} posts from r/dogs")

    if posts:
        print(f"\nSample post:")
        sample = posts[0]
        print(f"  Title: {sample['title']}")
        print(f"  Score: {sample['score']}")
        print(f"  Comments: {sample['num_comments']}")

    # Test statistics
    stats = scraper.get_post_statistics(posts)
    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
