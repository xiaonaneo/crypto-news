"""
RSS News Fetcher Module
Fetches crypto news from various RSS feeds
"""

import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import hashlib
import re

logger = logging.getLogger(__name__)


class RSSFetcher:
    """Fetches and parses RSS feeds for crypto news"""
    
    def __init__(self, config: dict):
        self.config = config
        self.feeds = config.get('rss_sources', [])
        self.crypto_keywords = config.get('crypto_keywords', [])
        self.lookback_hours = config.get('hours_lookback', 2)
    
    def is_crypto_related(self, title: str, summary: str = "") -> bool:
        """Check if content is crypto-related based on keywords"""
        text = f"{title} {summary}".lower()
        return any(kw.lower() in text for kw in self.crypto_keywords)
    
    def get_article_hash(self, url: str) -> str:
        """Generate unique hash for article deduplication"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def parse_date(self, entry) -> datetime:
        """Parse date from feed entry"""
        try:
            if hasattr(entry, 'published_parsed'):
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed'):
                return datetime(*entry.updated_parsed[:6])
            elif hasattr(entry, 'dc_date'):
                return datetime.fromisoformat(entry.dc_date.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Failed to parse date: {e}")
        return datetime.now()
    
    def clean_text(self, text: str, max_length: int = 200) -> str:
        """Clean and truncate text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length] + "..."
        return text.strip()
    
    def fetch_feed(self, feed_info: dict) -> List[Dict]:
        """Fetch and parse a single RSS feed"""
        articles = []
        
        if not feed_info.get('enabled', True):
            logger.debug(f"Feed disabled: {feed_info['name']}")
            return articles
        
        try:
            logger.info(f"Fetching RSS feed: {feed_info['name']}")
            feed = feedparser.parse(feed_info['url'])
            
            if feed.bozo:
                logger.warning(f"Malformed XML in {feed_info['name']}: {feed.bozo_exception}")
            
            cutoff_time = datetime.now() - timedelta(hours=self.lookback_hours)
            
            for entry in feed.entries[:50]:  # Limit to recent 50 entries
                # Parse date
                pub_date = self.parse_date(entry)
                
                # Skip old articles
                if pub_date < cutoff_time:
                    continue
                
                # Check crypto relevance
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))
                
                if not self.is_crypto_related(title, summary):
                    continue
                
                # Create article dict
                article = {
                    'hash': self.get_article_hash(entry.link),
                    'source': feed_info['name'],
                    'source_priority': feed_info.get('priority', 1),
                    'title': self.clean_text(title),
                    'url': entry.link,
                    'summary': self.clean_text(summary, 300),
                    'published': pub_date,
                    'authors': entry.get('authors', []),
                    'categories': entry.get('categories', []),
                    'engagement': 0  # RSS doesn't have engagement data
                }
                
                articles.append(article)
                logger.debug(f"Found article: {title[:50]}...")
            
            logger.info(f"✓ {feed_info['name']}: Found {len(articles)} crypto articles")
            
        except Exception as e:
            logger.error(f"✗ Error fetching {feed_info['name']}: {e}")
        
        return articles
    
    def fetch_all(self) -> List[Dict]:
        """Fetch crypto news from all enabled RSS feeds"""
        all_articles = []
        
        for feed in self.feeds:
            articles = self.fetch_feed(feed)
            all_articles.extend(articles)
        
        # Sort by priority (higher priority = more trusted source)
        all_articles.sort(key=lambda x: (-x['source_priority'], x['published']), reverse=True)
        
        logger.info(f"Total: Fetched {len(all_articles)} articles from {len(self.feeds)} feeds")
        return all_articles


# Convenience function for standalone use
def fetch_crypto_rss(config_path: str = None) -> List[Dict]:
    """Fetch crypto news from RSS feeds"""
    import yaml
    
    if config_path is None:
        config_path = 'config.yaml'
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    fetcher = RSSFetcher(config)
    return fetcher.fetch_all()


if __name__ == "__main__":
    # Test the RSS fetcher
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = 'config.yaml'
    
    articles = fetch_crypto_rss(config_file)
    
    print(f"\nFound {len(articles)} crypto articles:\n")
    for i, article in enumerate(articles[:10], 1):
        print(f"{i}. [{article['source']}] {article['title']}")
        print(f"   {article['url']}")
        print()
