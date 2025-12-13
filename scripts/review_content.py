"""
Interactive content review tool for Canadian Pet Pulse.
Allows editorial review of trending candidates before publishing.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from generators.html_generator import HTMLGenerator


class ContentReviewer:
    """Interactive CLI tool for reviewing and approving content."""

    def __init__(self, candidates_file: str):
        """
        Initialize reviewer with candidates file.

        Args:
            candidates_file: Path to trending_candidates.json
        """
        self.candidates_file = candidates_file
        self.candidates_data = None
        self.approved_items = []

    def load_candidates(self) -> bool:
        """Load candidates from JSON file."""
        try:
            with open(self.candidates_file, 'r') as f:
                self.candidates_data = json.load(f)
            return True
        except FileNotFoundError:
            print(f"❌ Candidates file not found: {self.candidates_file}")
            print("Run the pipeline first to generate candidates.")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in candidates file: {e}")
            return False

    def format_item_preview(self, item: Dict, index: int, total: int) -> str:
        """Format item for display in terminal."""
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append(f"ITEM {index + 1} of {total}")
        lines.append("=" * 80)

        # Title
        lines.append(f"\n📰 TITLE: {item['title']}")

        # Source
        content_type = item.get('content_type', 'unknown')
        if content_type == 'reddit':
            source = f"r/{item['subreddit']}"
        else:
            source = item.get('source', 'Unknown')
        lines.append(f"📍 SOURCE: {source}")

        # Scores
        canadian_score = item.get('canadian_score', 0.0)
        trending_score = item.get('trending_score', 0.0)
        lines.append(f"🔥 TRENDING SCORE: {trending_score:.2f}")
        lines.append(f"🍁 CANADIAN SCORE: {canadian_score * 100:.0f}%")

        # Engagement (Reddit only)
        if content_type == 'reddit':
            score = item.get('score', 0)
            comments = item.get('num_comments', 0)
            lines.append(f"⬆️  ENGAGEMENT: {score} upvotes | {comments} comments")

        # Content preview
        preview_text = ""
        if content_type == 'reddit' and item.get('selftext'):
            preview_text = item['selftext'][:200]
        elif content_type == 'news' and item.get('summary'):
            preview_text = item['summary'][:200]

        if preview_text:
            lines.append(f"\n📝 PREVIEW:")
            lines.append(f"   {preview_text}...")

        # Link
        if content_type == 'reddit':
            link = item.get('permalink', '')
            if link and not link.startswith('http'):
                link = f"https://www.reddit.com{link}"
        else:
            link = item.get('link', '')

        if link:
            lines.append(f"\n🔗 LINK: {link}")

        lines.append("\n" + "-" * 80)

        return "\n".join(lines)

    def get_user_decision(self) -> str:
        """
        Prompt user for decision on current item.

        Returns:
            'y' = yes/approve
            'n' = no/reject
            's' = skip to end
            'q' = quit
        """
        while True:
            response = input("\n👉 Include this item? (y=yes, n=no, s=skip to end, q=quit): ").lower().strip()

            if response in ['y', 'n', 's', 'q']:
                return response

            print("❌ Invalid input. Please enter 'y', 'n', 's', or 'q'.")

    def review_interactive(self) -> List[Dict]:
        """
        Interactive review of all candidates.

        Returns:
            List of approved items
        """
        if not self.candidates_data:
            return []

        content_items = self.candidates_data.get('content', [])
        total_items = len(content_items)

        print("\n" + "=" * 80)
        print("🐾 CANADIAN PET PULSE - CONTENT REVIEW")
        print("=" * 80)
        print(f"\n📊 Total candidates: {total_items}")
        print("\nReview each item and decide whether to publish it.")
        print("Commands: y=approve, n=reject, s=skip to end, q=quit\n")

        for index, item in enumerate(content_items):
            # Show item preview
            preview = self.format_item_preview(item, index, total_items)
            print(preview)

            # Get decision
            decision = self.get_user_decision()

            if decision == 'y':
                self.approved_items.append(item)
                print(f"✅ Approved ({len(self.approved_items)} total)")

            elif decision == 'n':
                print("❌ Rejected")

            elif decision == 's':
                print(f"\n⏭️  Skipping remaining {total_items - index - 1} items...")
                break

            elif decision == 'q':
                print("\n👋 Quitting review...")
                return []

        return self.approved_items

    def save_approved(self, output_file: str) -> bool:
        """
        Save approved items to JSON file.

        Args:
            output_file: Path to save approved items

        Returns:
            True if successful
        """
        if not self.approved_items:
            print("\n⚠️  No items approved. Not saving.")
            return False

        # Create output data structure (same format as candidates)
        output_data = {
            'date': self.candidates_data.get('date'),
            'generated_at': datetime.utcnow().isoformat() + '+00:00',
            'reviewed_at': datetime.now().strftime('%Y-%m-%d %I:%M %p'),
            'stats': {
                'reddit_posts': sum(1 for item in self.approved_items if item.get('content_type') == 'reddit'),
                'news_articles': sum(1 for item in self.approved_items if item.get('content_type') == 'news'),
                'total_items': len(self.approved_items),
                'sources_succeeded': self.candidates_data.get('stats', {}).get('sources_succeeded', []),
                'sources_failed': self.candidates_data.get('stats', {}).get('sources_failed', []),
            },
            'content': self.approved_items,
            'review_metadata': {
                'total_candidates': len(self.candidates_data.get('content', [])),
                'approved_count': len(self.approved_items),
                'approval_rate': f"{len(self.approved_items) / len(self.candidates_data.get('content', [])) * 100:.1f}%",
            }
        }

        try:
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\n✅ Saved {len(self.approved_items)} approved items to: {output_file}")
            return True
        except Exception as e:
            print(f"\n❌ Error saving approved items: {e}")
            return False

    def generate_html(self, approved_file: str, output_dir: str) -> bool:
        """
        Generate final HTML from approved items.

        Args:
            approved_file: Path to approved items JSON
            output_dir: Directory for HTML output (docs/)

        Returns:
            True if successful
        """
        try:
            # Load approved data
            with open(approved_file, 'r') as f:
                data = json.load(f)

            # Initialize HTML generator
            template_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'generators',
                'templates'
            )
            generator = HTMLGenerator(template_dir, output_dir)

            # Generate site (this also copies CSS and saves JSON internally)
            generator.generate_site(
                trending_content=data['content'],
                stats=data['stats']
            )

            # Generate archive page for this date
            date = data.get('date')
            if date:
                generator.generate_archive_page(
                    date=date,
                    trending_content=data['content'],
                    stats=data['stats']
                )

                # Regenerate archive index
                generator.generate_archive_index()

            print(f"\n✅ Generated HTML site in: {output_dir}/")
            print(f"   - index.html ({len(data['content'])} items)")
            print(f"   - data.json")
            print(f"   - styles.css")
            if date:
                print(f"   - archive/{date}.html")
                print(f"   - archive/index.html")

            return True

        except Exception as e:
            print(f"\n❌ Error generating HTML: {e}")
            return False


def main():
    """Main entry point for content review."""

    # Determine paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data' / 'processed'
    docs_dir = project_root / 'docs'

    # Find most recent candidates file
    today = datetime.now().strftime('%Y%m%d')
    candidates_file = data_dir / f'trending_candidates_{today}.json'
    approved_file = data_dir / f'trending_approved_{today}.json'

    # Check if candidates file exists
    if not candidates_file.exists():
        # Try to find any candidates file
        candidates_files = sorted(data_dir.glob('trending_candidates_*.json'), reverse=True)
        if candidates_files:
            candidates_file = candidates_files[0]
            print(f"ℹ️  Using most recent candidates file: {candidates_file.name}")
        else:
            print("❌ No candidates file found. Run the pipeline first:")
            print("   python scripts/run_pipeline.py")
            return 1

    # Initialize reviewer
    reviewer = ContentReviewer(str(candidates_file))

    # Load candidates
    if not reviewer.load_candidates():
        return 1

    # Run interactive review
    approved_items = reviewer.review_interactive()

    if not approved_items:
        print("\n👋 No items approved. Exiting without changes.")
        return 0

    # Show summary
    print("\n" + "=" * 80)
    print("📊 REVIEW SUMMARY")
    print("=" * 80)
    total_candidates = len(reviewer.candidates_data.get('content', []))
    print(f"Total candidates: {total_candidates}")
    print(f"Approved items: {len(approved_items)}")
    print(f"Approval rate: {len(approved_items) / total_candidates * 100:.1f}%")

    # Save approved items
    if not reviewer.save_approved(str(approved_file)):
        return 1

    # Ask if user wants to generate HTML now
    print("\n" + "=" * 80)
    generate = input("🎨 Generate HTML site from approved items? (y/n): ").lower().strip()

    if generate == 'y':
        if reviewer.generate_html(str(approved_file), str(docs_dir)):
            print("\n" + "=" * 80)
            print("✅ CONTENT REVIEW COMPLETE!")
            print("=" * 80)
            print(f"\nYour curated site is ready at: {docs_dir}/index.html")
            print(f"Review it locally before deploying to GitHub Pages.")
            print(f"\nTo view: open {docs_dir}/index.html")
        else:
            return 1
    else:
        print("\n👋 HTML generation skipped. Run this script again to regenerate.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
