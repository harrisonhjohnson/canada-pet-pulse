"""
Content ranking and trending score calculation.
Calculates trending scores for Reddit posts and news articles.
"""

from datetime import datetime, timezone
import math
from typing import List, Dict
import logging
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class ContentRanker:
    """
    Calculate trending scores and rank content.

    Trending scores combine:
    - Engagement metrics (upvotes, comments, etc.)
    - Time decay (recent content scores higher)
    - Canadian relevance boost
    """

    def calculate_reddit_score(self, post: Dict) -> float:
        """
        Calculate trending score for Reddit post.

        Algorithm:
        - Engagement = (upvotes * 1.0) + (comments * 2.0)
        - Time decay: fresher content scores higher
        - Canadian boost: 1.0x to 1.5x multiplier
        - Final: log10(engagement) * time_decay * canadian_boost

        Args:
            post: Reddit post dictionary

        Returns:
            Trending score (typically 0-10 range)
        """
        score = post.get('score', 0)
        comments = post.get('num_comments', 0)
        created_utc = post.get('created_utc', 0)
        canadian_score = post.get('canadian_score', 0.0)

        # 1. Calculate engagement
        # Comments weighted more heavily (indicate discussion)
        engagement = (score * 1.0) + (comments * 2.0)

        # 2. Time decay
        now = datetime.now(timezone.utc).timestamp()
        age_hours = (now - created_utc) / 3600 if created_utc > 0 else 999

        # Decay multiplier based on age
        if age_hours < 6:
            time_multiplier = 1.0  # Very fresh
        elif age_hours < 12:
            time_multiplier = 0.8  # Recent
        elif age_hours < 24:
            time_multiplier = 0.5  # Today
        else:
            time_multiplier = 0.2  # Older

        # 3. Canadian boost
        # Score 0.0 = 1.0x boost, Score 1.0 = 1.5x boost
        canadian_boost = 1.0 + (canadian_score * 0.5)

        # 4. Calculate final score
        # Use log10 to compress high engagement scores
        trending_score = math.log10(max(engagement, 1)) * time_multiplier * canadian_boost

        return round(trending_score, 3)

    def calculate_news_score(self, article: Dict) -> float:
        """
        Calculate trending score for news article.

        Algorithm:
        - Base score: 5.0 (news is inherently newsworthy)
        - Time decay: news expires faster than Reddit
        - Source credibility: major outlets get boost
        - Canadian boost: same as Reddit

        Args:
            article: News article dictionary

        Returns:
            Trending score (typically 1-15 range)
        """
        published = article.get('published', '')
        source = article.get('source', '')
        canadian_score = article.get('canadian_score', 0.0)

        # 1. Parse published date
        try:
            if isinstance(published, str):
                published_dt = date_parser.isoparse(published)
            else:
                published_dt = datetime.now(timezone.utc)
        except (ValueError, TypeError):
            published_dt = datetime.now(timezone.utc)

        # Make timezone-aware if needed
        if published_dt.tzinfo is None:
            published_dt = published_dt.replace(tzinfo=timezone.utc)

        # 2. Time decay (news expires faster)
        now = datetime.now(timezone.utc)
        age_hours = (now - published_dt).total_seconds() / 3600

        if age_hours < 6:
            time_multiplier = 1.0  # Breaking news
        elif age_hours < 12:
            time_multiplier = 0.7  # Recent
        elif age_hours < 24:
            time_multiplier = 0.4  # Today
        else:
            time_multiplier = 0.1  # Older news

        # 3. Source credibility
        major_sources = ['CBC', 'CTV', 'Global News', 'Toronto Star', 'Globe and Mail']
        source_boost = 1.3 if any(s in source for s in major_sources) else 1.0

        # 4. Canadian boost
        canadian_boost = 1.0 + (canadian_score * 0.5)

        # 5. Base score for news
        base_score = 5.0

        # 6. Calculate final score
        trending_score = base_score * time_multiplier * source_boost * canadian_boost

        return round(trending_score, 3)

    def rank_all_content(self, reddit_posts: List[Dict],
                        news_articles: List[Dict]) -> List[Dict]:
        """
        Rank all content and merge into single sorted list.

        Args:
            reddit_posts: List of Reddit post dictionaries
            news_articles: List of news article dictionaries

        Returns:
            Sorted list of all content (highest trending score first)
        """
        all_content = []

        # Score Reddit posts
        for post in reddit_posts:
            post['trending_score'] = self.calculate_reddit_score(post)
            post['content_type'] = 'reddit'
            all_content.append(post)

        # Score news articles
        for article in news_articles:
            article['trending_score'] = self.calculate_news_score(article)
            article['content_type'] = 'news'
            all_content.append(article)

        # Sort by trending score (descending)
        ranked_content = sorted(
            all_content,
            key=lambda x: x['trending_score'],
            reverse=True
        )

        logger.info(
            f"Ranked {len(ranked_content)} total items "
            f"({len(reddit_posts)} Reddit, {len(news_articles)} news)"
        )

        return ranked_content

    def get_top_content(self, content: List[Dict], limit: int = 50) -> List[Dict]:
        """
        Get top N items by trending score.

        Args:
            content: List of ranked content
            limit: Number of items to return

        Returns:
            Top N items
        """
        return content[:limit]

    def get_ranking_statistics(self, content: List[Dict]) -> Dict:
        """
        Calculate statistics about trending scores.

        Args:
            content: List of ranked content

        Returns:
            Dictionary with statistics
        """
        if not content:
            return {
                'total_items': 0,
                'avg_score': 0.0,
                'max_score': 0.0,
                'min_score': 0.0,
            }

        scores = [c['trending_score'] for c in content]
        reddit_count = sum(1 for c in content if c.get('content_type') == 'reddit')
        news_count = sum(1 for c in content if c.get('content_type') == 'news')

        return {
            'total_items': len(content),
            'reddit_items': reddit_count,
            'news_items': news_count,
            'avg_score': sum(scores) / len(scores),
            'max_score': max(scores),
            'min_score': min(scores),
            'top_5_scores': scores[:5] if len(scores) >= 5 else scores,
        }


# Example usage and testing
if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Test the ranker
    ranker = ContentRanker()

    print("Content Ranking Test")
    print("=" * 60)

    # Mock Reddit posts
    now_timestamp = datetime.now(timezone.utc).timestamp()

    mock_reddit = [
        {
            'title': 'Toronto dog park',
            'score': 500,
            'num_comments': 100,
            'created_utc': now_timestamp - (3 * 3600),  # 3 hours ago
            'canadian_score': 0.8,
            'subreddit': 'toronto'
        },
        {
            'title': 'General puppy tips',
            'score': 50,
            'num_comments': 10,
            'created_utc': now_timestamp - (30 * 3600),  # 30 hours ago
            'canadian_score': 0.2,
            'subreddit': 'puppy101'
        },
        {
            'title': 'Vancouver vet recommendations',
            'score': 200,
            'num_comments': 50,
            'created_utc': now_timestamp - (5 * 3600),  # 5 hours ago
            'canadian_score': 0.9,
            'subreddit': 'vancouver'
        },
    ]

    # Mock news articles
    mock_news = [
        {
            'title': 'CBC: New pet safety regulations',
            'published': (datetime.now(timezone.utc)).isoformat(),
            'source': 'CBC Canada',
            'canadian_score': 1.0,
        },
        {
            'title': 'Local blog: Training tips',
            'published': (datetime.now(timezone.utc)).isoformat(),
            'source': 'Pet Blog',
            'canadian_score': 0.3,
        },
    ]

    # Rank all content
    ranked = ranker.rank_all_content(mock_reddit, mock_news)

    print("\nRanked Content (by trending score):")
    print("-" * 60)
    for i, item in enumerate(ranked, 1):
        content_type = item['content_type']
        title = item['title']
        score = item['trending_score']
        canadian = item['canadian_score']

        print(f"{i}. [{content_type.upper()}] {title}")
        print(f"   Trending: {score:.3f} | Canadian: {canadian:.2f}")

    # Statistics
    print("\n" + "=" * 60)
    stats = ranker.get_ranking_statistics(ranked)
    print("Ranking Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test individual scoring
    print("\n" + "=" * 60)
    print("Individual Score Calculation Examples:")
    print("-" * 60)

    for post in mock_reddit:
        score = ranker.calculate_reddit_score(post)
        print(f"Reddit: {post['title']}")
        print(f"  Score: {post['score']}, Comments: {post['num_comments']}")
        print(f"  Trending Score: {score:.3f}\n")

    for article in mock_news:
        score = ranker.calculate_news_score(article)
        print(f"News: {article['title']}")
        print(f"  Source: {article['source']}")
        print(f"  Trending Score: {score:.3f}\n")
