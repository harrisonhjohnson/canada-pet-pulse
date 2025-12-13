#!/usr/bin/env python3
"""
Full pipeline test: Scrape → Filter → Rank → Generate HTML
Tests the complete Canadian Pet Pulse workflow end-to-end.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.reddit_scraper import RedditScraper
from scrapers.news_scraper import NewsScraper
from processors.canadian_filter import CanadianFilter
from processors.content_ranker import ContentRanker
from generators.html_generator import HTMLGenerator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run complete pipeline end-to-end."""

    print("=" * 70)
    print("CANADIAN PET PULSE - FULL PIPELINE TEST")
    print("=" * 70)

    # Setup paths
    template_dir = PROJECT_ROOT / 'generators' / 'templates'
    output_dir = PROJECT_ROOT / 'docs'

    # Step 1: Scrape Data
    print("\n[1/5] Scraping Reddit and News...")
    print("-" * 70)

    # Reddit
    reddit_scraper = RedditScraper()
    test_subreddits = ['dogs', 'puppy101', 'toronto', 'vancouver', 'canada']

    reddit_posts = reddit_scraper.scrape_all(
        subreddits=test_subreddits,
        limit_per_sub=10
    )

    print(f"✓ Reddit: {len(reddit_posts)} posts from {len(test_subreddits)} subreddits")

    # News
    news_scraper = NewsScraper()
    news_articles = news_scraper.scrape_all()

    print(f"✓ News: {len(news_articles)} pet-related articles")
    print(f"Total scraped: {len(reddit_posts) + len(news_articles)} items")

    # Step 2: Filter for Canadian Relevance
    print("\n[2/5] Filtering for Canadian Relevance...")
    print("-" * 70)

    canadian_filter = CanadianFilter()

    canadian_reddit = canadian_filter.filter_by_subreddit(reddit_posts)
    canadian_news = canadian_filter.filter_canadian_content(news_articles, threshold=0.2)

    print(f"Reddit: {len(reddit_posts)} → {len(canadian_reddit)} Canadian posts")
    print(f"News: {len(news_articles)} → {len(canadian_news)} Canadian articles")

    total_canadian = len(canadian_reddit) + len(canadian_news)
    print(f"Total Canadian content: {total_canadian} items")

    if total_canadian == 0:
        print("\n⚠️  No Canadian content found. Cannot generate site.")
        return False

    # Step 3: Rank Content
    print("\n[3/5] Calculating Trending Scores...")
    print("-" * 70)

    content_ranker = ContentRanker()
    ranked_content = content_ranker.rank_all_content(canadian_reddit, canadian_news)

    print(f"Ranked {len(ranked_content)} items")

    if ranked_content:
        top_score = ranked_content[0]['trending_score']
        bottom_score = ranked_content[-1]['trending_score']
        print(f"Score range: {bottom_score:.3f} to {top_score:.3f}")

        # Show top 5
        print(f"\nTop 5 Trending Items:")
        for i, item in enumerate(ranked_content[:5], 1):
            content_type = item['content_type'].upper()
            title = item['title'][:60]
            score = item['trending_score']
            print(f"  {i}. [{content_type}] {title}... (score: {score:.3f})")

    # Step 4: Generate HTML
    print("\n[4/5] Generating HTML...")
    print("-" * 70)

    stats = {
        'reddit_posts': len(canadian_reddit),
        'news_articles': len(canadian_news),
        'total_items': len(ranked_content)
    }

    html_generator = HTMLGenerator(str(template_dir), str(output_dir))
    html_generator.generate_site(ranked_content, stats)

    print(f"✓ Generated: {output_dir / 'index.html'}")
    print(f"✓ JSON data: {output_dir / 'data.json'}")
    print(f"✓ Styles: {output_dir / 'styles.css'}")

    # Step 5: Statistics
    print("\n[5/5] Pipeline Statistics:")
    print("-" * 70)

    filter_stats = canadian_filter.get_filter_statistics(ranked_content)
    ranking_stats = content_ranker.get_ranking_statistics(ranked_content)

    print("Canadian Filter:")
    print(f"  High relevance (≥0.7): {filter_stats.get('high_relevance', 0)}")
    print(f"  Medium relevance (0.3-0.7): {filter_stats.get('medium_relevance', 0)}")
    print(f"  Low relevance (<0.3): {filter_stats.get('low_relevance', 0)}")
    print(f"  Avg Canadian score: {filter_stats.get('avg_score', 0):.3f}")

    print(f"\nContent Ranking:")
    print(f"  Reddit posts: {ranking_stats['reddit_items']}")
    print(f"  News articles: {ranking_stats['news_items']}")
    print(f"  Avg trending score: {ranking_stats['avg_score']:.3f}")
    print(f"  Max trending score: {ranking_stats['max_score']:.3f}")

    # Summary
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)

    print(f"✓ Scraped: {len(reddit_posts) + len(news_articles)} total items")
    print(f"✓ Canadian-relevant: {total_canadian} items")
    print(f"✓ Generated site with {len(ranked_content)} trending items")
    print(f"✓ Output: {output_dir / 'index.html'}")

    print(f"\n🎉 SUCCESS! Open {output_dir / 'index.html'} in a browser to view!")
    print(f"\nTo view the site:")
    print(f"  open {output_dir / 'index.html'}")

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)
