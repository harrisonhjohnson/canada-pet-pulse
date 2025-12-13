#!/usr/bin/env python3
"""
Production pipeline for Canadian Pet Pulse.
Handles failures gracefully and ensures site generation even if some sources fail.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import json
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.reddit_scraper import RedditScraper
from scrapers.news_scraper import NewsScraper
from processors.canadian_filter import CanadianFilter
from processors.content_ranker import ContentRanker
from generators.html_generator import HTMLGenerator


# Configuration
class Config:
    """Pipeline configuration"""

    # Directories
    DATA_DIR = PROJECT_ROOT / 'data'
    RAW_DIR = DATA_DIR / 'raw'
    PROCESSED_DIR = DATA_DIR / 'processed'
    TEMPLATE_DIR = PROJECT_ROOT / 'generators' / 'templates'
    OUTPUT_DIR = PROJECT_ROOT / 'docs'

    # Scraping
    REDDIT_SUBREDDITS = [
        # Pet-focused subreddits
        'dogs', 'puppy101', 'DogTraining',

        # National
        'canada',

        # Major cities (original)
        'toronto', 'vancouver', 'montreal', 'calgary', 'ottawa', 'Edmonton', 'winnipeg',

        # Additional Canadian cities (15 more)
        'halifax', 'Quebec', 'VictoriaBC', 'Saskatoon', 'Regina',
        'KingstonOntario', 'londonontario', 'Guelph', 'Barrie', 'kelowna',
        'waterloo', 'windsorontario', 'Hamilton', 'Kitchener', 'StJohnsNL'
    ]
    REDDIT_LIMIT_PER_SUB = 15

    # Quality thresholds
    MIN_TOTAL_ITEMS = 10  # Minimum items needed to generate site
    MIN_SOURCES_SUCCESS = 1  # Minimum 1 of 2 source types (Reddit or News)

    # News scraping (optional - graceful degradation)
    ENABLE_NEWS_SCRAPING = True
    NEWS_TIMEOUT = 15  # Timeout for news sources (seconds)


def setup_logging():
    """Configure logging for pipeline."""
    # Create logs directory
    log_dir = PROJECT_ROOT / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Log file with timestamp
    log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


def ensure_directories():
    """Ensure all required directories exist."""
    Config.DATA_DIR.mkdir(exist_ok=True)
    Config.RAW_DIR.mkdir(exist_ok=True)
    Config.PROCESSED_DIR.mkdir(exist_ok=True)
    Config.OUTPUT_DIR.mkdir(exist_ok=True)


def scrape_reddit(logger) -> tuple[list, bool]:
    """
    Scrape Reddit posts.

    Returns:
        (posts, success) tuple
    """
    logger.info("=" * 70)
    logger.info("STEP 1: Scraping Reddit")
    logger.info("=" * 70)

    try:
        scraper = RedditScraper()
        posts = scraper.scrape_all(
            subreddits=Config.REDDIT_SUBREDDITS,
            limit_per_sub=Config.REDDIT_LIMIT_PER_SUB
        )

        # Save raw data
        today = datetime.now().strftime('%Y%m%d')
        raw_file = Config.RAW_DIR / f'reddit_{today}.json'
        scraper.save_to_json(posts, str(raw_file))

        logger.info(f"✓ Reddit: {len(posts)} posts scraped and saved to {raw_file}")
        return posts, True

    except Exception as e:
        logger.error(f"✗ Reddit scraping failed: {e}", exc_info=True)
        return [], False


def scrape_news(logger) -> tuple[list, bool]:
    """
    Scrape news articles (with timeout protection).

    Returns:
        (articles, success) tuple
    """
    logger.info("=" * 70)
    logger.info("STEP 2: Scraping News (Optional)")
    logger.info("=" * 70)

    if not Config.ENABLE_NEWS_SCRAPING:
        logger.info("News scraping disabled in config")
        return [], False

    try:
        # Try with shorter timeout
        import socket
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(Config.NEWS_TIMEOUT)

        scraper = NewsScraper()

        # Try one source at a time with individual error handling
        all_articles = []
        sources_tried = 0
        sources_succeeded = 0

        for source_name, feed_url in scraper.RSS_FEEDS.items():
            sources_tried += 1
            try:
                logger.info(f"Trying {source_name}...")
                articles = scraper.scrape_rss_feed(feed_url, source_name)
                if articles:
                    all_articles.extend(articles)
                    sources_succeeded += 1
                    logger.info(f"✓ {source_name}: {len(articles)} articles")
                else:
                    logger.warning(f"⚠ {source_name}: No articles found")
            except Exception as e:
                logger.warning(f"✗ {source_name} failed: {e}")
                continue

        # Restore original timeout
        socket.setdefaulttimeout(original_timeout)

        if all_articles:
            # Save raw data
            today = datetime.now().strftime('%Y%m%d')
            raw_file = Config.RAW_DIR / f'news_{today}.json'
            scraper.save_to_json(all_articles, str(raw_file))

            logger.info(f"✓ News: {len(all_articles)} articles from {sources_succeeded}/{sources_tried} sources")
            logger.info(f"  Saved to {raw_file}")
            return all_articles, True
        else:
            logger.warning("⚠ News scraping failed - no articles retrieved")
            return [], False

    except Exception as e:
        logger.error(f"✗ News scraping failed: {e}")
        return [], False


def filter_content(reddit_posts, news_articles, logger) -> tuple[list, list]:
    """
    Filter content for Canadian relevance.

    Returns:
        (canadian_reddit, canadian_news) tuple
    """
    logger.info("=" * 70)
    logger.info("STEP 3: Filtering for Canadian Relevance")
    logger.info("=" * 70)

    canadian_filter = CanadianFilter()

    # Filter Reddit
    canadian_reddit = canadian_filter.filter_by_subreddit(reddit_posts)
    logger.info(f"Reddit: {len(reddit_posts)} → {len(canadian_reddit)} Canadian posts")

    # Filter News
    canadian_news = canadian_filter.filter_canadian_content(news_articles, threshold=0.2)
    logger.info(f"News: {len(news_articles)} → {len(canadian_news)} Canadian articles")

    total_canadian = len(canadian_reddit) + len(canadian_news)
    logger.info(f"Total Canadian content: {total_canadian} items")

    return canadian_reddit, canadian_news


def rank_content(canadian_reddit, canadian_news, logger) -> list:
    """
    Rank content by trending score.

    Returns:
        Ranked content list
    """
    logger.info("=" * 70)
    logger.info("STEP 4: Ranking Content")
    logger.info("=" * 70)

    ranker = ContentRanker()
    ranked = ranker.rank_all_content(canadian_reddit, canadian_news)

    if ranked:
        logger.info(f"Ranked {len(ranked)} items")
        logger.info(f"  Top score: {ranked[0]['trending_score']:.3f}")
        logger.info(f"  Bottom score: {ranked[-1]['trending_score']:.3f}")

        # Show top 5
        logger.info("\nTop 5 Trending:")
        for i, item in enumerate(ranked[:5], 1):
            ctype = item['content_type'].upper()
            title = item['title'][:50]
            score = item['trending_score']
            can_score = item['canadian_score']
            logger.info(f"  {i}. [{ctype}] {title}... (trending: {score:.2f}, canadian: {can_score:.2f})")
    else:
        logger.warning("No content to rank!")

    return ranked


def save_candidates(ranked_content, stats, logger) -> bool:
    """
    Save trending candidates for editorial review.
    Does NOT generate HTML - that's done after review.

    Returns:
        Success boolean
    """
    logger.info("=" * 70)
    logger.info("STEP 5: Saving Candidates for Review")
    logger.info("=" * 70)

    try:
        # Save candidates data
        today = datetime.now().strftime('%Y%m%d')
        candidates_file = Config.PROCESSED_DIR / f'trending_candidates_{today}.json'

        with open(candidates_file, 'w', encoding='utf-8') as f:
            json.dump({
                'date': today,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'stats': stats,
                'content': ranked_content  # All candidates (not just top 100)
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Saved {len(ranked_content)} candidates: {candidates_file}")

        return True

    except Exception as e:
        logger.error(f"✗ Failed to save candidates: {e}", exc_info=True)
        return False


def main():
    """Run complete production pipeline."""

    # Setup
    logger = setup_logging()
    ensure_directories()

    start_time = datetime.now()

    logger.info("*" * 70)
    logger.info("CANADIAN PET PULSE - PRODUCTION PIPELINE")
    logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("*" * 70)

    # Track successes
    sources_succeeded = []
    sources_failed = []

    # Step 1: Scrape Reddit
    reddit_posts, reddit_success = scrape_reddit(logger)
    if reddit_success:
        sources_succeeded.append('reddit')
    else:
        sources_failed.append('reddit')

    # Step 2: Scrape News (optional)
    news_articles, news_success = scrape_news(logger)
    if news_success:
        sources_succeeded.append('news')
    else:
        sources_failed.append('news')

    # Quality Check: Do we have enough data?
    total_scraped = len(reddit_posts) + len(news_articles)

    if len(sources_succeeded) < Config.MIN_SOURCES_SUCCESS:
        logger.error(f"✗ PIPELINE FAILED: Too few sources succeeded ({len(sources_succeeded)}/{Config.MIN_SOURCES_SUCCESS} required)")
        logger.error(f"  Succeeded: {sources_succeeded}")
        logger.error(f"  Failed: {sources_failed}")
        return False

    logger.info(f"\nData collection summary:")
    logger.info(f"  Reddit: {len(reddit_posts)} posts")
    logger.info(f"  News: {len(news_articles)} articles")
    logger.info(f"  Total: {total_scraped} items")
    logger.info(f"  Sources succeeded: {sources_succeeded}")
    logger.info(f"  Sources failed: {sources_failed}")

    # Step 3: Filter
    canadian_reddit, canadian_news = filter_content(reddit_posts, news_articles, logger)

    total_canadian = len(canadian_reddit) + len(canadian_news)

    if total_canadian < Config.MIN_TOTAL_ITEMS:
        logger.error(f"✗ PIPELINE FAILED: Too few Canadian items ({total_canadian}/{Config.MIN_TOTAL_ITEMS} required)")
        return False

    # Step 4: Rank
    ranked_content = rank_content(canadian_reddit, canadian_news, logger)

    if not ranked_content:
        logger.error("✗ PIPELINE FAILED: No content to display")
        return False

    # Step 5: Save candidates for review
    stats = {
        'reddit_posts': len(canadian_reddit),
        'news_articles': len(canadian_news),
        'total_items': len(ranked_content),
        'sources_succeeded': sources_succeeded,
        'sources_failed': sources_failed,
    }

    save_success = save_candidates(ranked_content, stats, logger)

    if not save_success:
        logger.error("✗ PIPELINE FAILED: Failed to save candidates")
        return False

    # Success!
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETE - CANDIDATES READY FOR REVIEW")
    logger.info("=" * 70)
    logger.info(f"Duration: {duration:.1f} seconds")
    logger.info(f"Candidates generated: {len(ranked_content)}")
    logger.info(f"Canadian items: {total_canadian}")
    logger.info(f"Sources succeeded: {', '.join(sources_succeeded)}")
    if sources_failed:
        logger.info(f"Sources failed: {', '.join(sources_failed)}")
    logger.info("")
    logger.info("NEXT STEP: Editorial review")
    logger.info("Run: python scripts/review_content.py")
    logger.info("This will let you review and approve items before publishing.")
    logger.info("=" * 70)

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Pipeline crashed: {e}", exc_info=True)
        sys.exit(1)
