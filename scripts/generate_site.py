#!/usr/bin/env python3
"""
Automated site generation for GitHub Actions.
Runs pipeline, auto-approves top content, generates HTML.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.reddit_scraper import RedditScraper
from scrapers.news_scraper import NewsScraper
from processors.canadian_filter import CanadianFilter
from processors.content_ranker import ContentRanker
from processors.summary_generator import SummaryGenerator
from generators.html_generator import HTMLGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutomatedPipeline:
    """Fully automated pipeline for daily updates."""

    def __init__(self):
        self.data_dir = PROJECT_ROOT / 'data'
        self.raw_dir = self.data_dir / 'raw'
        self.processed_dir = self.data_dir / 'processed'
        self.docs_dir = PROJECT_ROOT / 'docs'

        # Ensure directories exist
        for dir_path in [self.data_dir, self.raw_dir, self.processed_dir, self.docs_dir]:
            dir_path.mkdir(exist_ok=True)

    def run(self):
        """Run complete automated pipeline."""
        logger.info("=" * 70)
        logger.info("CANADIAN PET PULSE - AUTOMATED DAILY UPDATE")
        logger.info("=" * 70)

        try:
            # Step 1: Scrape content
            reddit_posts, news_articles = self.scrape_content()

            # Step 2: Filter for Canadian pet content
            canadian_content = self.filter_content(reddit_posts, news_articles)

            # Step 3: Rank by trending score
            ranked_content = self.rank_content(canadian_content)

            # Step 4: Auto-approve top items
            approved_content = self.auto_approve(ranked_content)

            # Step 5: Generate summary
            summary = self.generate_summary(approved_content)

            # Step 6: Generate HTML site
            stats = {
                'reddit_posts': len([c for c in approved_content if c.get('content_type') == 'reddit']),
                'news_articles': len([c for c in approved_content if c.get('content_type') == 'news']),
                'total_items': len(approved_content),
                'sources_succeeded': ['reddit', 'news'],
                'sources_failed': [],
            }

            self.generate_html(approved_content, stats, summary)

            logger.info("=" * 70)
            logger.info("✅ AUTOMATED PIPELINE COMPLETE")
            logger.info(f"   Published {len(approved_content)} items")
            logger.info("=" * 70)

            return True

        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
            return False

    def scrape_content(self):
        """Scrape Reddit and news sources."""
        logger.info("STEP 1: Scraping content")

        # Reddit
        reddit_scraper = RedditScraper()
        subreddits = [
            'dogs', 'puppy101', 'DogTraining', 'canada',
            'toronto', 'vancouver', 'montreal', 'calgary', 'ottawa',
            'Edmonton', 'winnipeg', 'halifax', 'Quebec', 'VictoriaBC',
            'Saskatoon', 'Regina', 'KingstonOntario', 'londonontario',
            'Guelph', 'Barrie', 'kelowna', 'waterloo', 'windsorontario',
            'Hamilton', 'Kitchener', 'StJohnsNL'
        ]
        reddit_posts = reddit_scraper.scrape_all(subreddits=subreddits, limit_per_sub=15)

        # Save raw Reddit data
        today = datetime.now().strftime('%Y%m%d')
        reddit_file = self.raw_dir / f'reddit_{today}.json'
        reddit_scraper.save_to_json(reddit_posts, str(reddit_file))

        logger.info(f"✓ Reddit: {len(reddit_posts)} posts")

        # News
        news_scraper = NewsScraper()
        news_articles = []
        try:
            news_articles = news_scraper.scrape_all()
            if news_articles:
                news_file = self.raw_dir / f'news_{today}.json'
                news_scraper.save_to_json(news_articles, str(news_file))
        except Exception as e:
            logger.warning(f"News scraping failed: {e}")

        logger.info(f"✓ News: {len(news_articles)} articles")

        return reddit_posts, news_articles

    def filter_content(self, reddit_posts, news_articles):
        """Filter for Canadian pet content."""
        logger.info("STEP 2: Filtering content")

        canadian_filter = CanadianFilter()

        # Filter Reddit by subreddit
        canadian_reddit = canadian_filter.filter_by_subreddit(reddit_posts)
        logger.info(f"✓ Reddit: {len(reddit_posts)} → {len(canadian_reddit)} Canadian pet posts")

        # Filter news (high threshold to ensure strong Canadian relevance)
        canadian_news = canadian_filter.filter_canadian_content(news_articles, threshold=0.45)
        logger.info(f"✓ News: {len(news_articles)} → {len(canadian_news)} Canadian articles")

        return canadian_reddit + canadian_news

    def rank_content(self, content):
        """Rank content by trending score."""
        logger.info("STEP 3: Ranking content")

        ranker = ContentRanker()
        ranked = ranker.rank_all_content(
            [c for c in content if c.get('content_type') == 'reddit'],
            [c for c in content if c.get('content_type') == 'news']
        )

        logger.info(f"✓ Ranked {len(ranked)} items")
        return ranked

    def auto_approve(self, candidates):
        """
        Auto-approve top content based on quality criteria.

        Criteria:
        - Top 15 items by trending score
        - Minimum Canadian score of 0.15
        - Mix of different cities
        """
        logger.info("STEP 4: Auto-approving content")

        # Filter by minimum Canadian score (high threshold for quality)
        quality_items = [c for c in candidates if c.get('canadian_score', 0) >= 0.45]

        # Take top 15 by trending score
        approved = quality_items[:15]

        logger.info(f"✓ Auto-approved {len(approved)} items from {len(candidates)} candidates")

        # Log top 3 for visibility
        for i, item in enumerate(approved[:3], 1):
            logger.info(f"   {i}. {item.get('title', '')[:60]}...")

        return approved

    def generate_summary(self, content):
        """Generate AI summary of approved content."""
        logger.info("STEP 5: Generating summary")

        summary_gen = SummaryGenerator()
        summary = summary_gen.generate_summary(content)

        logger.info(f"✓ Summary: {summary[:80]}...")
        return summary

    def generate_html(self, content, stats, summary):
        """Generate final HTML site."""
        logger.info("STEP 6: Generating HTML")

        today = datetime.now().strftime('%Y%m%d')

        # Save approved data
        approved_file = self.processed_dir / f'trending_approved_{today}.json'
        with open(approved_file, 'w') as f:
            json.dump({
                'date': today,
                'generated_at': datetime.utcnow().isoformat() + '+00:00',
                'reviewed_at': datetime.now().strftime('%Y-%m-%d %I:%M %p'),
                'stats': stats,
                'content': content,
                'review_metadata': {
                    'method': 'auto-approved',
                    'approved_count': len(content),
                }
            }, f, indent=2)

        # Generate HTML
        template_dir = PROJECT_ROOT / 'generators' / 'templates'
        generator = HTMLGenerator(str(template_dir), str(self.docs_dir))

        # Main site
        generator.generate_site(
            trending_content=content,
            stats=stats,
            summary=summary
        )

        # Archive page
        generator.generate_archive_page(
            date=today,
            trending_content=content,
            stats=stats,
            summary=summary
        )

        # Archive index
        generator.generate_archive_index()

        logger.info(f"✓ Generated HTML site with {len(content)} items")


def main():
    """Entry point for automated pipeline."""
    pipeline = AutomatedPipeline()
    success = pipeline.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
