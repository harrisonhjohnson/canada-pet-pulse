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

Write a 2-3 sentence summary that tells readers WHAT pet stories are trending today. Focus on the actual topics and stories (lost dogs, rescues, training questions, adoption events, etc.), mentioning the city for context. Make it clear what each story is about so readers can decide if it's relevant to them.

Example style: "Winnipeg pet owners are organizing flight angels to rescue dogs and cats before the holiday embargo, while Saskatoon residents are sharing stories of dogs getting stuck on frozen rivers during winter walks."

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

        # Build story-focused mentions (top 3 posts)
        story_mentions = []
        for post in posts[:3]:
            city = post.get('subreddit', 'Unknown').capitalize()
            title = post.get('title', '')

            # Extract key topic from title (lowercase for pattern matching)
            title_lower = title.lower()

            # Try to extract meaningful summary
            if 'lost' in title_lower or 'found' in title_lower:
                topic = "has lost/found pet reports"
            elif 'rescue' in title_lower or 'adoption' in title_lower or 'adopt' in title_lower:
                topic = f"features {title[:50]}"
            elif 'training' in title_lower:
                topic = "discusses pet training questions"
            elif 'stuck' in title_lower or 'help' in title_lower:
                topic = f"shares {title[:45]}"
            else:
                # Default: use first part of title
                topic = f"discusses {title[:50]}"

            story_mentions.append(f"{city} {topic}")

        if len(story_mentions) == 1:
            return f"Today's top Canadian pet story: {story_mentions[0]}."
        elif len(story_mentions) == 2:
            return f"Trending today: {story_mentions[0]}, while {story_mentions[1]}."
        elif len(story_mentions) >= 3:
            return f"Trending today: {story_mentions[0]}, {story_mentions[1]}, and {story_mentions[2]}."
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
