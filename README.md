# 🐾 Canadian Pet Pulse

Daily trending pet content aggregator for the Canadian market. Automatically collects, filters, and ranks pet-related discussions from Reddit and Canadian news sources.

**Live Site**: [https://yourusername.github.io/canadian-pet-pulse/](https://yourusername.github.io/canadian-pet-pulse/) *(update after deployment)*

---

## 📊 What It Does

Canadian Pet Pulse aggregates trending pet content from across Canada:

- **Reddit Posts**: Monitors pet and Canadian subreddits (r/dogs, r/puppy101, r/toronto, r/vancouver, r/canada, etc.)
- **News Articles**: Scrapes Canadian news sources (CBC, CTV, Global News) for pet-related stories
- **Smart Filtering**: Uses AI-powered Canadian relevance scoring (cities, provinces, keywords, postal codes)
- **Trending Algorithm**: Ranks content by engagement, recency, and Canadian relevance
- **Daily Updates**: Automatically refreshes at 2 AM ET via GitHub Actions

---

## 🎯 Features

### Canadian Relevance Detection
Sophisticated scoring algorithm that identifies Canadian content:
- **City Detection**: Toronto, Vancouver, Montreal, Calgary, Ottawa, etc.
- **Province Detection**: All provinces and territories (Ontario, BC, Quebec, Alberta, etc.)
- **Keyword Matching**: Canadian-specific terms (CRA, RCMP, Tim Hortons, etc.)
- **Postal Code Recognition**: A1A 1A1 pattern matching

### Trending Score Calculation
Smart ranking combines multiple factors:
- **Engagement Metrics**: Upvotes, comments, discussion activity
- **Time Decay**: Fresher content scores higher
- **Canadian Boost**: Higher relevance = higher ranking
- **Source Credibility**: Major news outlets get boosted

### Mobile-First Design
- Responsive layout for all devices
- Fast loading (static HTML)
- Clean, newspaper-style design
- Reddit orange + Canadian red color scheme

---

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/canadian-pet-pulse.git
cd canadian-pet-pulse

# Install dependencies
pip install -r requirements.txt

# Run scraper and generate site
python3 scripts/generate_site.py

# View site
open docs/index.html
```

### Testing Individual Components

```bash
# Test scrapers
python3 scripts/test_scrapers.py

# Test processors (filtering & ranking)
python3 scripts/test_processors.py

# Test full pipeline
python3 scripts/test_full_pipeline.py
```

---

## 📁 Project Structure

```
canadian-pet-pulse/
├── scrapers/
│   ├── reddit_scraper.py       # Reddit JSON endpoint scraper
│   ├── news_scraper.py         # RSS feed scraper
│   └── base_scraper.py         # Shared utilities
├── processors/
│   ├── canadian_filter.py      # Canadian relevance scoring
│   ├── content_ranker.py       # Trending score calculation
│   └── data_schemas.py         # Pydantic data models
├── generators/
│   ├── html_generator.py       # Static HTML generation
│   └── templates/
│       ├── index.html.j2       # Jinja2 template
│       └── styles.css          # Responsive CSS
├── scripts/
│   ├── generate_site.py        # Main site generation script
│   ├── test_scrapers.py        # Scraper validation tests
│   └── test_processors.py      # Processor integration tests
├── data/
│   ├── raw/                    # Raw scraper outputs
│   └── processed/              # Filtered & ranked data
├── docs/                       # GitHub Pages output
│   ├── index.html              # Generated site
│   ├── data.json               # JSON export
│   └── styles.css              # Styles
├── .github/workflows/
│   └── daily-scrape.yml        # GitHub Actions automation
├── requirements.txt
└── README.md
```

---

## 🤖 Automation

The site updates automatically daily at 2 AM ET using GitHub Actions:

1. **Scrape**: Collects Reddit posts and news articles
2. **Filter**: Identifies Canadian-relevant content
3. **Rank**: Calculates trending scores
4. **Generate**: Creates static HTML
5. **Deploy**: Pushes to GitHub Pages

Manual trigger: Go to Actions → Daily Update → Run workflow

---

## 🧪 How It Works

### 1. Data Collection
```python
# Reddit Scraper
reddit_scraper = RedditScraper()
posts = reddit_scraper.scrape_all(
    subreddits=['dogs', 'toronto', 'vancouver'],
    limit_per_sub=15
)
# Uses public JSON endpoints (no auth required)
# Rate limiting: 2-second delay between requests
```

### 2. Canadian Filtering
```python
# Canadian Filter
canadian_filter = CanadianFilter()
canadian_posts = canadian_filter.filter_by_subreddit(posts)
# Scoring: cities (0.3), provinces (0.2), keywords (0.15), postal codes (0.2)
# Auto-includes Canadian subreddits (r/toronto, r/vancouver)
```

### 3. Trending Ranking
```python
# Content Ranker
ranker = ContentRanker()
ranked = ranker.rank_all_content(canadian_posts, news_articles)
# Formula: log10(engagement) × time_decay × canadian_boost
# Sorted by trending score (highest first)
```

### 4. HTML Generation
```python
# HTML Generator
generator = HTMLGenerator(template_dir, output_dir)
generator.generate_site(ranked, stats)
# Jinja2 templates → Static HTML
# Mobile-responsive, SEO-optimized
```

---

## 🛠️ Configuration

### Subreddits
Edit `scrapers/reddit_scraper.py`:
```python
SUBREDDITS = [
    'dogs', 'puppy101', 'DogTraining',  # Pet subreddits
    'toronto', 'vancouver', 'montreal',  # City subreddits
    'canada',                             # National subreddit
]
```

### News Sources
Edit `scrapers/news_scraper.py`:
```python
RSS_FEEDS = {
    'CBC Canada': 'https://www.cbc.ca/webfeed/rss/rss-canada',
    'CTV News': 'https://www.ctvnews.ca/rss/...',
    'Global News': 'https://globalnews.ca/feed/',
}
```

### Canadian Keywords
Edit `processors/canadian_filter.py`:
```python
CITIES = ['toronto', 'vancouver', 'montreal', ...]
PROVINCES = ['ontario', 'quebec', 'bc', ...]
KEYWORDS = ['canada', 'canadian', 'canuck', ...]
```

---

## 📦 Dependencies

- **requests** (2.31.0): HTTP requests
- **feedparser** (6.0.11): RSS feed parsing
- **beautifulsoup4** (4.12.2): HTML cleaning
- **Jinja2** (3.1.2): Template rendering
- **pydantic** (2.5.3): Data validation
- **python-dateutil** (2.8.2): Date parsing

All dependencies listed in `requirements.txt`.

---

## 🔒 Privacy & Ethics

- **Public Data Only**: Uses publicly available Reddit posts and news RSS feeds
- **No Authentication**: No user tracking or data collection
- **Robots.txt Compliant**: Respects website scraping policies
- **Rate Limiting**: 2-second delays between requests to avoid server load
- **Attribution**: All content links back to original sources

---

## 🚧 Roadmap

### Phase 1 (Complete)
- ✅ Reddit scraping
- ✅ News RSS scraping
- ✅ Canadian relevance filtering
- ✅ Trending score calculation
- ✅ Static HTML generation
- ✅ GitHub Pages deployment
- ✅ GitHub Actions automation

### Phase 2 (Future)
- [ ] Google Trends integration
- [ ] Instagram/TikTok trending content
- [ ] Amazon Canada product trends
- [ ] Email/Slack notifications
- [ ] Historical trend analysis

### Phase 3 (Future)
- [ ] Database storage (PostgreSQL)
- [ ] Archive pages by date
- [ ] Regional filtering (by province)
- [ ] Category filtering (dogs vs cats)
- [ ] Sentiment analysis

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Reddit**: Public JSON API for community content
- **Canadian News Outlets**: CBC, CTV, Global News for RSS feeds
- **Jinja2**: Excellent templating engine
- **GitHub Pages**: Free static site hosting

---

## 📧 Contact

Questions or suggestions? Open an issue on GitHub.

---

**Built with ❤️ for Canadian pet owners**
