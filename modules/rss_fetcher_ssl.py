"""
RSS Fetcher with SSL workaround for environments with certificate issues
"""

import feedparser
import logging
import ssl
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import hashlib
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Beijing timezone for display
BJ_TIMEZONE = timezone(timedelta(hours=8))


# Create SSL context that doesn't verify certificates (for dev environments)
def create_unverified_ssl_context():
    """Create an SSL context that doesn't verify certificates"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


# Monkey patch feedparser to use unverified SSL
_original_urlopen = urllib.request.urlopen

def _patched_urlopen(url, *args, **kwargs):
    """Patched urlopen that doesn't verify SSL certificates"""
    try:
        return _original_urlopen(url, *args, **kwargs, context=create_unverified_ssl_context())
    except (ssl.SSLCertVerificationError, urllib.error.URLError) as e:
        logger.debug(f"SSL error with {url}, retrying with verification disabled: {e}")
        import urllib.request
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            return response


# Apply patch
urllib.request.urlopen = _patched_urlopen


class RSSFetcher:
    """Fetches and parses RSS feeds for crypto news"""
    
    def __init__(self, config: dict, last_push_timestamp: datetime = None):
        self.config = config
        self.feeds = config.get('rss_sources', [])
        self.crypto_keywords = config.get('crypto_keywords', [])
        self.exclude_keywords = config.get('exclude_keywords', [])

        # Use last push timestamp if provided, otherwise fallback to hours_lookback
        if last_push_timestamp:
            self.cutoff_timestamp = last_push_timestamp
        else:
            processing_config = config.get('processing', {})
            self.lookback_hours = processing_config.get('hours_lookback',
                                                         config.get('hours_lookback', 24))
            self.cutoff_timestamp = datetime.now(BJ_TIMEZONE) - timedelta(hours=self.lookback_hours)
    
    def is_crypto_related(self, title: str = "", summary: str = "", source_name: str = "", crypto_only: bool = False) -> bool:
        """Check if content is crypto-related using enhanced keyword analysis"""
        # If source is crypto-only, skip keyword filtering
        if crypto_only:
            return True

        if not title and not summary:
            return False

        text = f"{title} {summary}".lower()

        # First, check for exclusion keywords - if they appear prominently, likely not crypto
        exclude_score = sum(1 for kw in self.exclude_keywords if kw.lower() in text)
        if exclude_score >= 2:  # Multiple finance/stock mentions suggest non-crypto content
            return False

        # Check for crypto keywords with scoring system
        crypto_score = 0
        found_keywords = []

        for kw in self.crypto_keywords:
            if kw.lower() in text:
                found_keywords.append(kw)
                # Weight different types of keywords differently
                if kw in ['bitcoin', 'ethereum', 'btc', 'eth']:  # Core crypto terms
                    crypto_score += 3
                elif kw in ['crypto', 'cryptocurrency', 'blockchain']:  # General terms
                    crypto_score += 2
                else:  # Specific terms
                    crypto_score += 1

        # Require minimum crypto relevance score (at least 2 points of crypto relevance)
        if crypto_score >= 2:
            logger.debug(f"Crypto-related article: '{title[:50]}...' (score: {crypto_score}, keywords: {found_keywords[:3]})")
            return True
        else:
            logger.debug(f"Non-crypto article: '{title[:50]}...' (score: {crypto_score})")
            return False
    
    def get_article_hash(self, url: str) -> str:
        """Generate unique hash for article deduplication"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def parse_date(self, entry) -> datetime:
        """Parse date from feed entry, converting to Beijing time"""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                # published_parsed is UTC time (struct_time)
                utc_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                # Convert to Beijing time
                return utc_dt.astimezone(BJ_TIMEZONE)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                utc_dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                return utc_dt.astimezone(BJ_TIMEZONE)
            elif hasattr(entry, 'dc_date') and entry.dc_date:
                dt = datetime.fromisoformat(entry.dc_date.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(BJ_TIMEZONE)
            elif hasattr(entry, 'published') and entry.published:
                date_str = entry.published
                for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt.astimezone(BJ_TIMEZONE)
                    except:
                        continue
        except Exception as e:
            logger.debug(f"Failed to parse date: {e}")
        # Fallback to current Beijing time
        return datetime.now(BJ_TIMEZONE)
    
    def clean_text(self, text: str, max_length: int = 200) -> str:
        """Clean and truncate text"""
        if not text:
            return ""
        
        text = re.sub(r'<[^>]+>', '', text)
        text = ' '.join(text.split())
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
                logger.warning(f"Malformed XML in {feed_info['name']}")
            
            crypto_only = feed_info.get('crypto_only', False)

            for entry in feed.entries[:50]:
                pub_date = self.parse_date(entry)

                if pub_date <= self.cutoff_timestamp:
                    continue
                
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))
                
                if not self.is_crypto_related(title, summary, feed_info['name'], crypto_only):
                    continue
                
                article = {
                    'hash': self.get_article_hash(entry.link),
                    'source': feed_info['name'],
                    'source_priority': feed_info.get('priority', 1),
                    'title': self.clean_text(title),
                    'url': entry.link,
                    'published': pub_date,
                    'engagement': 0
                }
                
                articles.append(article)
            
            logger.info(f"✓ {feed_info['name']}: Found {len(articles)} crypto articles")
            
        except Exception as e:
            logger.error(f"✗ Error fetching {feed_info['name']}: {e}")
            import traceback
            traceback.print_exc()
        
        return articles
    
    def fetch_all(self) -> List[Dict]:
        """Fetch crypto news from all enabled RSS feeds"""
        all_articles = []
        
        for feed in self.feeds:
            articles = self.fetch_feed(feed)
            all_articles.extend(articles)
        
        all_articles.sort(key=lambda x: (-x['source_priority'], x['published']), reverse=True)
        
        logger.info(f"Total: Fetched {len(all_articles)} articles from {len(self.feeds)} feeds")
        return all_articles


if __name__ == "__main__":
    import yaml
    
    logging.basicConfig(level=logging.INFO)
    
    config_path = '/Users/lixiaonan/vibe coding/测试文件夹/config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    fetcher = RSSFetcher(config)
    print(f"Using lookback hours: {fetcher.lookback_hours}")
    articles = fetcher.fetch_all()
    
    print(f"\nFound {len(articles)} crypto articles:\n")
    for i, article in enumerate(articles[:10], 1):
        print(f"{i}. [{article['source']}] {article['title'][:60]}...")
