"""
AI-powered summary generator for Canadian Pet Pulse.
Generates daily summaries focusing on Canadian pet headlines.
"""

import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """Generate AI summaries of daily pet content."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize summary generator.

        Args:
            api_key: Anthropic API key (optional, reads from ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')

    def filter_for_summary(self, content: List[Dict]) -> List[Dict]:
        """
        Filter content for summary generation.
        Focus on Canadian subreddit posts that mention cats or dogs in title.

        Args:
            content: List of approved content items

        Returns:
            Filtered list suitable for summarization
        """
        canadian_subreddits = {
            'canada', 'onguardforthee',
            'toronto', 'vancouver', 'montreal', 'calgary', 'ottawa',
            'edmonton', 'winnipeg', 'halifax', 'victoriabc', 'saskatoon',
            'regina', 'kingstonontario', 'londonontario', 'guelph',
            'barrie', 'kelowna', 'waterloo', 'windsorontario', 'hamilton',
            'kitchener', 'stjohnsnl', 'quebec', 'britishcolumbia',
            'ontario', 'alberta'
        }

        pet_keywords = ['dog', 'dogs', 'puppy', 'puppies', 'cat', 'cats', 'kitten', 'kittens', 'pet', 'pets']

        filtered = []
        for item in content:
            # Only Reddit posts from Canadian subreddits
            if item.get('content_type') != 'reddit':
                continue

            subreddit = item.get('subreddit', '').lower()
            if subreddit not in canadian_subreddits:
                continue

            # Must mention cat or dog in title
            title = item.get('title', '').lower()
            if any(keyword in title for keyword in pet_keywords):
                filtered.append(item)

        return filtered

    def generate_summary(self, content: List[Dict]) -> str:
        """
        Generate AI summary of daily content.

        Args:
            content: List of approved content items

        Returns:
            Generated summary text
        """
        # Filter to relevant posts
        relevant_posts = self.filter_for_summary(content)

        if not relevant_posts:
            return self._generate_fallback_summary(content)

        # Try AI generation if API key available
        if self.api_key:
            try:
                return self._generate_ai_summary(relevant_posts)
            except Exception as e:
                logger.warning(f"AI summary generation failed: {e}, using fallback")
                return self._generate_fallback_summary(relevant_posts)
        else:
            logger.info("No API key found, using fallback summary")
            return self._generate_fallback_summary(relevant_posts)

    def _generate_ai_summary(self, posts: List[Dict]) -> str:
        """
        Generate summary using Anthropic Claude API.

        Args:
            posts: Filtered posts for summarization

        Returns:
            AI-generated summary
        """
        try:
            import anthropic
        except ImportError:
            logger.error("anthropic package not installed. Install with: pip install anthropic")
            return self._generate_fallback_summary(posts)

        # Prepare post data for Claude
        posts_text = []
        for i, post in enumerate(posts[:10], 1):  # Limit to top 10
            city = post.get('subreddit', 'Unknown')
            title = post.get('title', '')
            selftext = post.get('selftext', '')[:200]  # First 200 chars
            posts_text.append(f"{i}. r/{city}: {title}")
            if selftext:
                posts_text.append(f"   Context: {selftext}")

        prompt = f"""You are summarizing today's trending pet stories across Canadian cities.

Here are the top pet-related posts from Canadian city subreddits:

{chr(10).join(posts_text)}

Write a 2-3 sentence summary highlighting the key pet stories and trends from across Canada today. Focus on what's happening with cats and dogs in different Canadian cities. Keep it engaging and informative.

Summary:"""

        # Call Claude API
        client = anthropic.Anthropic(api_key=self.api_key)

        message = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Fast and cost-effective
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        summary = message.content[0].text.strip()
        logger.info(f"Generated AI summary: {len(summary)} chars")
        return summary

    def _generate_fallback_summary(self, posts: List[Dict]) -> str:
        """
        Generate simple rule-based summary when AI is unavailable.

        Args:
            posts: Posts to summarize

        Returns:
            Simple summary text
        """
        if not posts:
            return "Today's trending Canadian pet content features stories from across the country."

        # Group by city
        cities = {}
        for post in posts[:10]:
            city = post.get('subreddit', 'Unknown')
            title = post.get('title', '')
            if city not in cities:
                cities[city] = []
            cities[city].append(title)

        # Build summary
        city_mentions = []
        for city, titles in list(cities.items())[:3]:  # Top 3 cities
            city_name = city.capitalize()
            if len(titles) == 1:
                city_mentions.append(f"{city_name} ({titles[0][:40]}...)")
            else:
                city_mentions.append(f"{city_name} ({len(titles)} posts)")

        if city_mentions:
            return f"Today's Canadian pet stories feature discussions from {', '.join(city_mentions[:-1])} and {city_mentions[-1]}."
        else:
            return "Today's trending Canadian pet content features stories from across the country."


# Example usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Mock data
    mock_content = [
        {
            'content_type': 'reddit',
            'subreddit': 'toronto',
            'title': 'Lost dog found in High Park',
            'selftext': 'A golden retriever was reunited with its owner after being found...'
        },
        {
            'content_type': 'reddit',
            'subreddit': 'vancouver',
            'title': 'Best cat cafes in the city?',
            'selftext': 'Looking for recommendations...'
        },
        {
            'content_type': 'reddit',
            'subreddit': 'calgary',
            'title': 'Puppy training classes - where to start?',
            'selftext': 'First time dog owner here...'
        },
    ]

    generator = SummaryGenerator()
    summary = generator.generate_summary(mock_content)
    print(f"\nGenerated Summary:\n{summary}")
