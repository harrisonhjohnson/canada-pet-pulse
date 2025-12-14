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

        prompt = f"""You are a marketing manager for Fi, a GPS dog collar company. Based on today's trending pet stories in Canada, create 5 specific marketing tactics.

Here are today's top pet-related posts from Canadian city subreddits:

{chr(10).join(posts_text)}

Create these 5 marketing tactics based on the trends you see:

1. **Instagram Post**: A caption for an Instagram post that ties to today's trends (include emoji, keep it engaging, under 150 chars)

2. **Email to Canada Prospects**: Subject line and 1-sentence preview that connects today's pet trends to why they need Fi

3. **In-App Discover Card** (Referral): A short message for Fi app users encouraging them to refer friends, tied to today's trends

4. **Email to Canada Customers**: Subject line and 1-sentence preview with a helpful tip or story based on today's trends

5. **Partnership/PR Email**: A 1-sentence pitch to Canadian pet organizations/media about why today's trends matter

Format your response exactly like this:
📸 Instagram: [caption]
📧 Prospects: [subject] | [preview]
📱 Refer Friend: [message]
📧 Customers: [subject] | [preview]
🤝 Partners: [pitch]"""

        # Call Claude API
        client = anthropic.Anthropic(api_key=self.api_key)

        message = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Fast and cost-effective
            max_tokens=500,  # Increased for 5 marketing tactics
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        summary = message.content[0].text.strip()
        logger.info(f"Generated AI summary: {len(summary)} chars")
        return summary

    def _generate_fallback_summary(self, posts: List[Dict]) -> str:
        """
        Generate simple rule-based marketing tactics when AI is unavailable.

        Args:
            posts: Posts to summarize

        Returns:
            Marketing tactics text
        """
        if not posts:
            return """📸 Instagram: Canadian pet parents are making moves today 🇨🇦🐾
📧 Prospects: Keep your pup safe in Canada's unpredictable conditions | Never lose sight of your dog with Fi's GPS tracking
📱 Refer Friend: Share Fi with your Canadian dog parent friends and help keep more pups safe!
📧 Customers: Tips for winter pet safety in Canada | Based on today's trending stories from pet parents across the country
🤝 Partners: Canadian pet parents are increasingly concerned about pet safety - let's discuss how Fi can help address these trends"""

        # Get top story for context
        top_post = posts[0]
        city = top_post.get('subreddit', 'Canada').capitalize()
        title = top_post.get('title', '')[:60]

        return f"""📸 Instagram: Canadian pet parents in {city} are talking about: {title}... 🇨🇦🐾
📧 Prospects: Never lose your dog in Canada | Fi GPS collars help Canadian pet parents stay connected with their dogs
📱 Refer Friend: See today's trending pet stories? Share Fi with friends who need GPS tracking for their pups!
📧 Customers: What's trending in Canadian pet communities today | {title}...
🤝 Partners: Today's trending pet content shows Canadian pet parents need better safety tools - Fi is seeing strong engagement in markets like {city}"""


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
