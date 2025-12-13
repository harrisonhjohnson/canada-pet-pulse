"""
Canadian relevance filter and scoring algorithm.
Detects and scores content for Canadian relevance based on geographic indicators.
"""

import re
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class CanadianFilter:
    """
    Filter and score content for Canadian relevance.

    Scoring algorithm:
    - City mentions: 0.3 points each (max 0.5)
    - Province mentions: 0.2 points each (max 0.3)
    - Canadian keywords: 0.15 points each (max 0.3)
    - Postal code: 0.2 points

    Score range: 0.0 to 1.0
    """

    # Major Canadian cities
    CITIES = [
        'toronto', 'vancouver', 'montreal', 'calgary', 'ottawa',
        'edmonton', 'winnipeg', 'quebec city', 'hamilton', 'kitchener',
        'london', 'victoria', 'halifax', 'oshawa', 'windsor',
        'saskatoon', 'regina', 'kelowna', 'barrie', 'sherbrooke',
        'guelph', 'kanata', 'abbotsford', 'kingston', 'trois-rivières',
    ]

    # Canadian provinces and territories
    PROVINCES = [
        'ontario', 'quebec', 'british columbia', 'alberta', 'manitoba',
        'saskatchewan', 'nova scotia', 'new brunswick',
        'newfoundland and labrador', 'newfoundland', 'labrador',
        'prince edward island', 'pei',
        'northwest territories', 'nunavut', 'yukon',
    ]

    # Province abbreviations
    PROVINCE_CODES = [
        'on', 'qc', 'bc', 'ab', 'mb', 'sk', 'ns', 'nb', 'nl', 'pe', 'nt', 'nu', 'yt',
    ]

    # Canadian-specific keywords
    KEYWORDS = [
        'canada', 'canadian', 'canuck', 'canadians',
        # Canadian institutions
        'cra', 'rcmp', 'cbsa', 'health canada',
        # Canadian brands/terms
        'tim hortons', 'timmies', 'loblaws', 'canadian tire',
        'shoppers drug mart', 'sobeys',
    ]

    # Canadian postal code pattern: A1A 1A1 or A1A1A1
    POSTAL_CODE_PATTERN = r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b'

    def __init__(self):
        """Initialize Canadian filter with compiled regex patterns."""
        # Compile postal code regex for efficiency
        self.postal_code_regex = re.compile(self.POSTAL_CODE_PATTERN, re.IGNORECASE)

        # Compile word boundary patterns for cities
        self.city_patterns = [
            re.compile(r'\b' + re.escape(city) + r'\b', re.IGNORECASE)
            for city in self.CITIES
        ]

        # Compile patterns for provinces
        self.province_patterns = [
            re.compile(r'\b' + re.escape(prov) + r'\b', re.IGNORECASE)
            for prov in self.PROVINCES
        ]

        # Special patterns for province codes (need word boundaries)
        self.province_code_patterns = [
            re.compile(r'\b' + code + r'\b', re.IGNORECASE)
            for code in self.PROVINCE_CODES
        ]

    def calculate_canadian_score(self, text: str) -> float:
        """
        Calculate Canadian relevance score (0.0 to 1.0).

        Args:
            text: Text to analyze

        Returns:
            Score from 0.0 (not Canadian) to 1.0 (highly Canadian)

        Example:
            >>> filter = CanadianFilter()
            >>> filter.calculate_canadian_score("Toronto dog park")
            0.3
            >>> filter.calculate_canadian_score("Vancouver BC pet rescue")
            0.5
        """
        if not text:
            return 0.0

        score = 0.0
        text_lower = text.lower()

        # 1. City mentions (0.3 points each, max 0.5)
        city_matches = sum(
            1 for pattern in self.city_patterns
            if pattern.search(text)
        )
        score += min(city_matches * 0.3, 0.5)

        # 2. Province mentions (0.2 points each, max 0.3)
        province_matches = sum(
            1 for pattern in self.province_patterns
            if pattern.search(text)
        )
        # Also check province codes
        province_code_matches = sum(
            1 for pattern in self.province_code_patterns
            if pattern.search(text)
        )
        total_province_matches = province_matches + province_code_matches
        score += min(total_province_matches * 0.2, 0.3)

        # 3. Canadian keywords (0.15 points each, max 0.3)
        keyword_matches = sum(
            1 for keyword in self.KEYWORDS
            if keyword in text_lower
        )
        score += min(keyword_matches * 0.15, 0.3)

        # 4. Postal code (0.2 points)
        if self.postal_code_regex.search(text):
            score += 0.2

        # Cap at 1.0
        return min(score, 1.0)

    def is_canadian(self, content: Dict, threshold: float = 0.2) -> bool:
        """
        Determine if content is Canadian-relevant.

        Args:
            content: Content dictionary with 'title' and optional text fields
            threshold: Minimum score to be considered Canadian (0.0-1.0)

        Returns:
            True if content exceeds threshold
        """
        # Combine all searchable text
        searchable_text = content.get('title', '')

        # Add body text if available (Reddit)
        if 'selftext' in content:
            searchable_text += ' ' + content.get('selftext', '')

        # Add summary if available (News)
        if 'summary' in content:
            searchable_text += ' ' + content.get('summary', '')

        # Calculate score
        score = self.calculate_canadian_score(searchable_text)

        # Attach score to content for later use
        content['canadian_score'] = score

        return score >= threshold

    def filter_canadian_content(self, content_list: List[Dict],
                                threshold: float = 0.2) -> List[Dict]:
        """
        Filter list of content for Canadian relevance.

        Args:
            content_list: List of content dictionaries
            threshold: Minimum Canadian score

        Returns:
            Filtered list with only Canadian-relevant content
        """
        canadian_content = [
            content for content in content_list
            if self.is_canadian(content, threshold)
        ]

        logger.info(
            f"Filtered {len(content_list)} items -> {len(canadian_content)} "
            f"Canadian items (threshold: {threshold})"
        )

        return canadian_content

    def filter_by_subreddit(self, posts: List[Dict]) -> List[Dict]:
        """
        Special handling for Reddit posts with subreddit-aware filtering.

        - Posts from Canadian subreddits are auto-included
        - Posts from pet subreddits need Canadian score check
        - Other subreddits need strong Canadian signal

        Args:
            posts: List of Reddit post dictionaries

        Returns:
            Filtered list of Canadian-relevant posts
        """
        canadian_subreddits = {
            'canada', 'toronto', 'vancouver', 'montreal', 'calgary',
            'ottawa', 'edmonton', 'winnipeg', 'onguardforthee',
            'britishcolumbia', 'ontario', 'quebec', 'alberta',
        }

        pet_subreddits = {
            'dogs', 'puppy101', 'dogtraining', 'cats', 'catadvice',
            'pets', 'aww',
        }

        filtered_posts = []

        for post in posts:
            subreddit = post.get('subreddit', '').lower()

            # Auto-include Canadian subreddits
            if subreddit in canadian_subreddits:
                post['canadian_score'] = 1.0  # Max score
                filtered_posts.append(post)
                logger.debug(f"Auto-included r/{subreddit}: {post['title'][:50]}")

            # Check pet subreddits for Canadian mentions (lower threshold)
            elif subreddit in pet_subreddits:
                if self.is_canadian(post, threshold=0.15):
                    filtered_posts.append(post)
                    logger.debug(
                        f"Canadian pet post r/{subreddit} "
                        f"(score: {post['canadian_score']:.2f}): {post['title'][:50]}"
                    )

            # Other subreddits need strong Canadian signal
            else:
                if self.is_canadian(post, threshold=0.3):
                    filtered_posts.append(post)
                    logger.debug(
                        f"Canadian post r/{subreddit} "
                        f"(score: {post['canadian_score']:.2f}): {post['title'][:50]}"
                    )

        logger.info(
            f"Reddit filter: {len(posts)} posts -> {len(filtered_posts)} Canadian posts"
        )

        return filtered_posts

    def get_filter_statistics(self, content_list: List[Dict]) -> Dict:
        """
        Calculate statistics about Canadian scores.

        Args:
            content_list: List of content with canadian_score field

        Returns:
            Dictionary with statistics
        """
        if not content_list:
            return {
                'total_items': 0,
                'avg_score': 0.0,
                'min_score': 0.0,
                'max_score': 0.0,
            }

        scores = [c.get('canadian_score', 0.0) for c in content_list]

        return {
            'total_items': len(content_list),
            'avg_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'high_relevance': sum(1 for s in scores if s >= 0.7),
            'medium_relevance': sum(1 for s in scores if 0.3 <= s < 0.7),
            'low_relevance': sum(1 for s in scores if s < 0.3),
        }


# Example usage and testing
if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Test the filter
    filter = CanadianFilter()

    # Test cases
    test_cases = [
        "My dog loves Toronto parks!",
        "Best vet in Vancouver BC",
        "Puppy training tips",
        "Montreal dog rescue needs help",
        "Canadian pet food regulations",
        "Walking my dog in Calgary",
        "General training advice",
        "Ottawa animal shelter M5V 3A8",
        "Dog park recommendations",
        "Lost dog in Ontario, please help!",
    ]

    print("Canadian Relevance Scoring Test")
    print("=" * 60)

    for text in test_cases:
        score = filter.calculate_canadian_score(text)
        is_can = "✓ Canadian" if score >= 0.2 else "✗ Not Canadian"
        print(f"{is_can} ({score:.2f}): {text}")

    # Test with mock content
    print("\n" + "=" * 60)
    print("Content Filtering Test")
    print("=" * 60)

    mock_posts = [
        {'title': 'Toronto dog park closed', 'subreddit': 'toronto'},
        {'title': 'Best puppy food brands', 'subreddit': 'puppy101'},
        {'title': 'Vancouver hiking trails for dogs', 'subreddit': 'dogs'},
        {'title': 'General training tips', 'subreddit': 'dogs'},
    ]

    filtered = filter.filter_by_subreddit(mock_posts)

    print(f"\nFiltered {len(mock_posts)} posts -> {len(filtered)} Canadian posts")
    for post in filtered:
        print(f"  - [{post['canadian_score']:.2f}] {post['title']}")

    # Statistics
    stats = filter.get_filter_statistics(filtered)
    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
