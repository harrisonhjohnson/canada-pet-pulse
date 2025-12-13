"""
HTML generator for Canadian Pet Pulse.
Generates static HTML from trending content using Jinja2 templates.
"""

from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timezone
from typing import List, Dict
import json
import shutil
import os
import logging
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def format_time_ago(timestamp) -> str:
    """
    Format timestamp as human-readable "time ago" string.

    Args:
        timestamp: Unix timestamp (float) or ISO string

    Returns:
        Human-readable time string (e.g., "3 hours ago")
    """
    try:
        # Handle Unix timestamp (Reddit)
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        # Handle ISO string (News)
        elif isinstance(timestamp, str):
            dt = date_parser.isoparse(timestamp)
            # Make timezone-aware if needed
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            return "Unknown time"

        # Calculate time difference
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = diff.total_seconds()

        # Format based on time difference
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            weeks = int(seconds / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    except Exception as e:
        logger.warning(f"Error formatting timestamp: {e}")
        return "Unknown time"


class HTMLGenerator:
    """
    Generate static HTML for GitHub Pages deployment.
    """

    def __init__(self, template_dir: str, output_dir: str):
        """
        Initialize HTML generator.

        Args:
            template_dir: Directory containing Jinja2 templates
            output_dir: Directory for generated HTML output
        """
        self.template_dir = template_dir
        self.output_dir = output_dir

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )

        # Add custom filters
        self.env.filters['format_time_ago'] = format_time_ago

    def generate_site(self, trending_content: List[Dict], stats: Dict,
                     output_filename: str = 'index.html'):
        """
        Generate complete static site.

        Args:
            trending_content: List of ranked content dictionaries
            stats: Site statistics (post counts, etc.)
            output_filename: Name of output HTML file
        """
        output_path = os.path.join(self.output_dir, output_filename)

        # Load template
        template = self.env.get_template('index.html.j2')

        # Prepare context data
        context = {
            'title': 'Canadian Pet Pulse',
            'generated_at': datetime.now(timezone.utc).strftime('%B %d, %Y at %I:%M %p ET'),
            'trending_content': trending_content[:50],  # Top 50 items
            'stats': stats,
            'total_items': len(trending_content),
        }

        # Render HTML
        html = template.render(**context)

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Generated HTML: {output_path}")

        # Also save JSON data for potential client-side features
        self._save_json_data(trending_content, stats)

        # Copy CSS file
        self._copy_static_assets()

    def _save_json_data(self, trending_content: List[Dict], stats: Dict):
        """
        Save JSON data export for client-side features.

        Args:
            trending_content: List of trending content
            stats: Statistics
        """
        data_path = os.path.join(self.output_dir, 'data.json')

        output = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'stats': stats,
            'content': trending_content[:100],  # Top 100 items
        }

        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Generated JSON: {data_path}")

    def _copy_static_assets(self):
        """Copy CSS and other static files to output directory."""
        # Copy styles.css
        styles_source = os.path.join(self.template_dir, 'styles.css')
        styles_dest = os.path.join(self.output_dir, 'styles.css')

        if os.path.exists(styles_source):
            shutil.copy2(styles_source, styles_dest)
            logger.info(f"Copied styles to {styles_dest}")
        else:
            logger.warning(f"Styles file not found: {styles_source}")

    def generate_archive_page(self, date: str, trending_content: List[Dict],
                             stats: Dict):
        """
        Generate archive page for a specific date.

        Args:
            date: Date string (YYYYMMDD)
            trending_content: Trending content for that date
            stats: Statistics for that date
        """
        # Create archive directory
        archive_dir = os.path.join(self.output_dir, 'archive')
        os.makedirs(archive_dir, exist_ok=True)

        # Format date for display
        from datetime import datetime
        try:
            date_obj = datetime.strptime(date, '%Y%m%d')
            date_formatted = date_obj.strftime('%B %d, %Y')
        except:
            date_formatted = date

        # Generate filename
        filename = f"{date}.html"
        output_path = os.path.join(archive_dir, filename)

        # Use archive template
        template = self.env.get_template('archive.html.j2')

        context = {
            'title': 'Canadian Pet Pulse',
            'date_formatted': date_formatted,
            'trending_content': trending_content,
            'stats': stats,
        }

        html = template.render(**context)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Generated archive page: {output_path}")

    def generate_archive_index(self):
        """
        Generate archive index page listing all available archive days.
        """
        archive_dir = os.path.join(self.output_dir, 'archive')

        if not os.path.exists(archive_dir):
            logger.warning("No archive directory found")
            return

        # Find all archive HTML files
        archive_files = sorted([f for f in os.listdir(archive_dir) if f.endswith('.html') and f != 'index.html'], reverse=True)

        # Parse dates from filenames
        archives = []
        for filename in archive_files:
            date_str = filename.replace('.html', '')
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, '%Y%m%d')
                archives.append({
                    'date': date_str,
                    'date_formatted': date_obj.strftime('%B %d, %Y'),
                    'filename': filename
                })
            except:
                continue

        # Generate index page
        index_path = os.path.join(archive_dir, 'index.html')

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Canadian Pet Pulse - Archive</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>🐾 Canadian Pet Pulse</h1>
            <p class="subtitle">Content Archive</p>
            <p><a href="../index.html" style="color: white; text-decoration: underline;">← Back to Today</a></p>
        </div>
    </header>

    <main class="container">
        <section class="trending-content">
            <h2>Browse Past Days</h2>
            <div style="max-width: 600px; margin: 0 auto;">
"""

        for archive in archives:
            html += f"""
                <div style="background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0 0 10px 0;">
                        <a href="{archive['filename']}" style="color: #E74C3C; text-decoration: none;">
                            {archive['date_formatted']}
                        </a>
                    </h3>
                    <p style="color: #666; margin: 0;">View curated Canadian pet content from this day</p>
                </div>
"""

        if not archives:
            html += """
                <div class="empty-state">
                    <div class="empty-state-icon">🐕</div>
                    <p class="empty-state-text">No archived content yet</p>
                    <p class="empty-state-subtext">Check back after your first daily update!</p>
                </div>
"""

        html += """
            </div>
        </section>
    </main>

    <footer>
        <div class="container">
            <p><strong>Canadian Pet Pulse</strong> - Browse historical content</p>
            <p><a href="../index.html">View Today's Content</a></p>
            <p><a href="https://github.com/harrisonhjohnson/canada-pet-pulse" target="_blank" rel="noopener noreferrer">View on GitHub</a></p>
        </div>
    </footer>
</body>
</html>
"""

        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Generated archive index with {len(archives)} days")


# Example usage and testing
if __name__ == '__main__':
    import sys
    from pathlib import Path

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Setup paths
    project_root = Path(__file__).parent.parent
    template_dir = project_root / 'generators' / 'templates'
    output_dir = project_root / 'docs'

    print("HTML Generator Test")
    print("=" * 60)

    # Create mock data
    now_timestamp = datetime.now(timezone.utc).timestamp()

    mock_content = [
        {
            'content_type': 'reddit',
            'title': 'Toronto dog park recommendations',
            'permalink': 'https://reddit.com/r/toronto/test1',
            'selftext': 'Looking for great dog parks in the GTA area. Any suggestions?',
            'score': 150,
            'num_comments': 45,
            'subreddit': 'toronto',
            'created_utc': now_timestamp - (3 * 3600),  # 3 hours ago
            'canadian_score': 0.8,
            'trending_score': 3.5,
        },
        {
            'content_type': 'news',
            'title': 'New pet safety regulations announced',
            'link': 'https://cbc.ca/news/test',
            'summary': 'Health Canada announces new regulations for pet food safety and labeling requirements.',
            'source': 'CBC Canada',
            'published': datetime.now(timezone.utc).isoformat(),
            'canadian_score': 1.0,
            'trending_score': 8.5,
        },
        {
            'content_type': 'reddit',
            'title': 'Best puppy training tips?',
            'permalink': 'https://reddit.com/r/puppy101/test2',
            'selftext': '',
            'score': 50,
            'num_comments': 20,
            'subreddit': 'puppy101',
            'created_utc': now_timestamp - (5 * 3600),  # 5 hours ago
            'canadian_score': 0.2,
            'trending_score': 2.1,
        },
    ]

    mock_stats = {
        'reddit_posts': 2,
        'news_articles': 1,
        'total_items': 3,
    }

    # Generate HTML
    print("\nGenerating HTML...")
    generator = HTMLGenerator(str(template_dir), str(output_dir))
    generator.generate_site(mock_content, mock_stats)

    print(f"\n✓ Generated site at: {output_dir / 'index.html'}")
    print(f"✓ JSON data at: {output_dir / 'data.json'}")
    print(f"✓ Styles copied to: {output_dir / 'styles.css'}")
    print(f"\nOpen {output_dir / 'index.html'} in a browser to view!")
