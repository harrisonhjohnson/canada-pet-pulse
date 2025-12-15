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

        prompt = f"""You are a marketing manager for Fi, a GPS dog collar company. Create 5 marketing tactics for the Canadian market based on today's trending pet stories.

BRAND VOICE (Fi Canada Style Guide):
- Voice: "We bring pets and pet owners closer through our technology"
- Tone: Witty, never cutesy. NO "doggo", "pupper", "fur baby"
- Style: Confident brevity. Short, punchy headlines. Active voice.

TODAY'S TRENDING STORIES:
{chr(10).join(posts_text)}

For EACH tactic below, select the BEST trending story from the list above that fits that specific marketing channel. Different tactics can use different stories. Then create:

1. 📸 INSTAGRAM POST
   - Headline (max 50 chars)
   - Body copy (max 100 chars)
   - CTA (max 8 chars)
   - Tie to the specific story, witty tone

2. 📧 PROSPECT EMAIL
   - Subject line (max 50 chars)
   - Preview text (max 100 chars)
   - Connect story to why they need Fi GPS

3. 📱 IN-APP REFERRAL CARD
   - Headline (max 37 chars)
   - Body copy (max 45 chars)
   - Reference the trending story

4. 📧 CUSTOMER EMAIL
   - Subject line (max 50 chars)
   - Preview text (max 100 chars)
   - Helpful tip based on the story

5. 🤝 PARTNERSHIP PITCH
   - One compelling sentence (max 100 chars)
   - Pitch to Canadian pet orgs/media

Format response exactly like this:
📸 Instagram
Headline: [text]
Copy: [text]
CTA: [text]

📧 Prospects
Subject: [text]
Preview: [text]

📱 Refer Friend
Headline: [text]
Copy: [text]

📧 Customers
Subject: [text]
Preview: [text]

🤝 Partners
[pitch text]"""

        # Call Claude API
        client = anthropic.Anthropic(api_key=self.api_key)

        message = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Fast and cost-effective
            max_tokens=750,  # Increased for 5 marketing tactics with different stories
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
            return """📸 Instagram
Headline: GPS tracking keeps Canadian pets safe
Copy: Real-time location tracking. AI health insights. Peace of mind.
CTA: Learn more

📧 Prospects
Subject: Never lose your dog in Canada
Preview: Fi brings you closer to your pet with GPS tracking & AI-analyzed behavior insights.

📱 Refer Friend
Headline: Share Fi with your friends
Copy: Help keep more Canadian pets safe

📧 Customers
Subject: Track your adventures together
Preview: See where your dog explored today with Fi's GPS tracking.

🤝 Partners
Canadian pet parents need better safety tools — Fi's GPS tracking is seeing strong engagement nationwide."""

        # Get top story for context
        top_post = posts[0]
        city = top_post.get('subreddit', 'Canada').capitalize()
        title = top_post.get('title', '')
        title_short = title[:40] if len(title) > 40 else title

        return f"""📸 Instagram
Headline: {city} pet parents are talking
Copy: "{title_short}" — this is why GPS tracking matters.
CTA: Get Fi

📧 Prospects
Subject: {city}: {title_short}
Preview: Stories like this show why Canadian pet parents trust Fi's GPS tracking.

📱 Refer Friend
Headline: Trending in {city}
Copy: Share Fi with friends who need GPS tracking

📧 Customers
Subject: Trending in {city} pet communities
Preview: {title_short} — see what's happening in your area.

🤝 Partners
{city} pet parents are discussing {title_short[:50]} — Fi's GPS tracking addresses real safety concerns."""


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
