#!/usr/bin/env python3
"""
Integration test for processors: Canadian filter + Content ranker.
Tests the complete processing pipeline with real scraped data.
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


def test_integrated_pipeline():
    """Test complete pipeline: scrape -> filter -> rank"""

    print("=" * 70)
    print("CANADIAN PET PULSE - PROCESSOR INTEGRATION TEST")
    print("=" * 70)

    # Step 1: Scrape sample data
    print("\n[1/5] Scraping Sample Data...")
    print("-" * 70)

    reddit_scraper = RedditScraper()
    news_scraper = NewsScraper()

    # Scrape a few subreddits
    test_subreddits = ['dogs', 'toronto']
    reddit_posts = []

    for sub in test_subreddits:
        try:
            posts = reddit_scraper.scrape_subreddit(sub, limit=5)
            reddit_posts.extend(posts)
            print(f"✓ r/{sub}: {len(posts)} posts")
        except Exception as e:
            print(f"✗ r/{sub}: {e}")

    # Scrape one news source
    try:
        news_articles = news_scraper.scrape_rss_feed(
            'https://globalnews.ca/feed/',
            'Global News'
        )
        print(f"✓ Global News: {len(news_articles)} pet articles")
    except Exception as e:
        print(f"✗ Global News: {e}")
        news_articles = []

    print(f"\nTotal collected: {len(reddit_posts)} Reddit + {len(news_articles)} News")

    # Step 2: Filter for Canadian relevance
    print("\n[2/5] Filtering for Canadian Relevance...")
    print("-" * 70)

    canadian_filter = CanadianFilter()

    canadian_reddit = canadian_filter.filter_by_subreddit(reddit_posts)
    canadian_news = canadian_filter.filter_canadian_content(news_articles, threshold=0.2)

    print(f"Reddit: {len(reddit_posts)} -> {len(canadian_reddit)} Canadian posts")
    print(f"News: {len(news_articles)} -> {len(canadian_news)} Canadian articles")

    # Show some examples
    if canadian_reddit:
        print(f"\nSample Canadian Reddit posts:")
        for post in canadian_reddit[:3]:
            print(f"  [{post['canadian_score']:.2f}] r/{post['subreddit']}: {post['title'][:60]}...")

    if canadian_news:
        print(f"\nSample Canadian news articles:")
        for article in canadian_news[:3]:
            print(f"  [{article['canadian_score']:.2f}] {article['source']}: {article['title'][:60]}...")

    # Step 3: Calculate trending scores
    print("\n[3/5] Calculating Trending Scores...")
    print("-" * 70)

    content_ranker = ContentRanker()

    ranked_content = content_ranker.rank_all_content(canadian_reddit, canadian_news)

    print(f"Ranked {len(ranked_content)} total items")

    if ranked_content:
        print(f"\nTrending score range: {ranked_content[-1]['trending_score']:.3f} to {ranked_content[0]['trending_score']:.3f}")

    # Step 4: Display top trending content
    print("\n[4/5] Top Trending Content:")
    print("-" * 70)

    top_content = content_ranker.get_top_content(ranked_content, limit=10)

    for i, item in enumerate(top_content, 1):
        content_type = item['content_type'].upper()
        title = item['title'][:60]
        trending = item['trending_score']
        canadian = item['canadian_score']

        if content_type == 'REDDIT':
            source = f"r/{item['subreddit']}"
            engagement = f"{item['score']}↑ {item['num_comments']}💬"
        else:
            source = item['source']
            engagement = ""

        print(f"{i:2d}. [{content_type:6s}] {title}...")
        print(f"    Source: {source:20s} | Trending: {trending:5.3f} | Canadian: {canadian:.2f} | {engagement}")

    # Step 5: Statistics
    print("\n[5/5] Pipeline Statistics:")
    print("-" * 70)

    filter_stats = canadian_filter.get_filter_statistics(ranked_content)
    ranking_stats = content_ranker.get_ranking_statistics(ranked_content)

    print("Canadian Filter Stats:")
    print(f"  High relevance (≥0.7): {filter_stats.get('high_relevance', 0)}")
    print(f"  Medium relevance (0.3-0.7): {filter_stats.get('medium_relevance', 0)}")
    print(f"  Low relevance (<0.3): {filter_stats.get('low_relevance', 0)}")
    print(f"  Average Canadian score: {filter_stats.get('avg_score', 0):.3f}")

    print(f"\nRanking Stats:")
    print(f"  Reddit items: {ranking_stats['reddit_items']}")
    print(f"  News items: {ranking_stats['news_items']}")
    print(f"  Average trending score: {ranking_stats['avg_score']:.3f}")
    print(f"  Max trending score: {ranking_stats['max_score']:.3f}")

    # Summary
    print("\n" + "=" * 70)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 70)

    total_scraped = len(reddit_posts) + len(news_articles)
    total_canadian = len(canadian_reddit) + len(canadian_news)
    success_rate = (total_canadian / total_scraped * 100) if total_scraped > 0 else 0

    print(f"✓ Scraped: {total_scraped} items")
    print(f"✓ Canadian-relevant: {total_canadian} items ({success_rate:.1f}%)")
    print(f"✓ Ranked: {len(ranked_content)} items")
    print(f"✓ Top trending score: {ranked_content[0]['trending_score']:.3f}" if ranked_content else "✗ No content")

    if total_canadian >= 5:
        print("\n🎉 Integration test PASSED! Pipeline is working correctly.")
        return True
    else:
        print("\n⚠️  Warning: Low Canadian content count. May need to adjust filters.")
        return False


if __name__ == '__main__':
    success = test_integrated_pipeline()
    sys.exit(0 if success else 1)
