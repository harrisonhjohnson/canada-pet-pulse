#!/usr/bin/env python3
"""
Quick site generation using Reddit data only.
Skips news sources to avoid network timeout issues.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.reddit_scraper import RedditScraper
from processors.canadian_filter import CanadianFilter
from processors.content_ranker import ContentRanker
from generators.html_generator import HTMLGenerator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Generate site with Reddit data only."""

    print("=" * 70)
    print("CANADIAN PET PULSE - SITE GENERATION")
    print("=" * 70)

    # Setup paths
    template_dir = PROJECT_ROOT / 'generators' / 'templates'
    output_dir = PROJECT_ROOT / 'docs'

    # Step 1: Scrape Reddit
    print("\n[1/4] Scraping Reddit...")
    print("-" * 70)

    reddit_scraper = RedditScraper()
    subreddits = ['dogs', 'puppy101', 'toronto', 'vancouver', 'canada', 'montreal', 'calgary']

    reddit_posts = reddit_scraper.scrape_all(
        subreddits=subreddits,
        limit_per_sub=15
    )

    print(f"✓ Scraped {len(reddit_posts)} Reddit posts")

    # Step 2: Filter
    print("\n[2/4] Filtering for Canadian Relevance...")
    print("-" * 70)

    canadian_filter = CanadianFilter()
    canadian_posts = canadian_filter.filter_by_subreddit(reddit_posts)

    print(f"✓ Filtered to {len(canadian_posts)} Canadian-relevant posts")

    if len(canadian_posts) == 0:
        print("\n⚠️  No Canadian content found!")
        return False

    # Step 3: Rank
    print("\n[3/4] Ranking Content...")
    print("-" * 70)

    content_ranker = ContentRanker()
    ranked_content = content_ranker.rank_all_content(canadian_posts, [])

    print(f"✓ Ranked {len(ranked_content)} items")
    print(f"  Top score: {ranked_content[0]['trending_score']:.3f}")
    print(f"  Bottom score: {ranked_content[-1]['trending_score']:.3f}")

    # Show top 3
    print("\nTop 3 Trending:")
    for i, item in enumerate(ranked_content[:3], 1):
        print(f"  {i}. [{item['canadian_score']:.2f}] r/{item['subreddit']}: {item['title'][:50]}...")

    # Step 4: Generate HTML
    print("\n[4/4] Generating HTML...")
    print("-" * 70)

    stats = {
        'reddit_posts': len(canadian_posts),
        'news_articles': 0,
        'total_items': len(ranked_content)
    }

    html_generator = HTMLGenerator(str(template_dir), str(output_dir))
    html_generator.generate_site(ranked_content, stats)

    print(f"✓ Generated {output_dir / 'index.html'}")
    print(f"✓ Generated {output_dir / 'data.json'}")
    print(f"✓ Copied {output_dir / 'styles.css'}")

    # Summary
    print("\n" + "=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print(f"Generated site with {len(ranked_content)} trending items")
    print(f"\nTo view:")
    print(f"  open {output_dir / 'index.html'}")

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)
