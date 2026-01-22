"""
News Processor Module
Handles article deduplication, filtering, and ranking
"""

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

# Beijing timezone for display
BJ_TIMEZONE = timezone(timedelta(hours=8))


class NewsProcessor:
    """Processes and filters news articles"""
    
    def __init__(self, config: dict, db_path: str = "data/articles.db"):
        self.config = config
        self.db_path = db_path
        self.deduplication = config.get('deduplication', True)
        self.max_articles = config.get('max_articles', 15)
        
        # Ranking weights
        ranking = config.get('ranking', {})
        self.recency_weight = ranking.get('recency_weight', 0.4)
        self.source_weight = ranking.get('source_weight', 0.3)
        self.engagement_weight = ranking.get('engagement_weight', 0.3)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for deduplication"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                source TEXT,
                published_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")
    
    def is_duplicate(self, article: Dict) -> bool:
        """Check if article already exists in database"""
        if not self.deduplication:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM articles WHERE url_hash = ?",
            (article['hash'],)
        )
        
        exists = cursor.fetchone() is not None
        conn.close()
        
        return exists
    
    def mark_processed(self, articles: List[Dict]):
        """Mark articles as processed in database"""
        if not self.deduplication:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for article in articles:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO articles (url_hash, url, title, source, published_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        article['hash'],
                        article['url'],
                        article['title'],
                        article['source'],
                        article['published']
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to mark article: {e}")
        
        conn.commit()
        conn.close()
    
    def cleanup_old_articles(self, days: int = 7):
        """Remove articles older than N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now(BJ_TIMEZONE) - timedelta(days=days)
        cursor.execute("DELETE FROM articles WHERE created_at < ?", (cutoff,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old articles")
    
    def calculate_recency_score(self, article: Dict) -> float:
        """Calculate recency score (0-1)"""
        now = datetime.now(BJ_TIMEZONE)
        hours_old = (now - article['published']).total_seconds() / 3600
        
        # Exponential decay: very recent = high score
        if hours_old < 1:
            return 1.0
        elif hours_old < 2:
            return 0.9
        elif hours_old < 4:
            return 0.7
        elif hours_old < 8:
            return 0.5
        else:
            return 0.3
    
    def calculate_source_score(self, article: Dict) -> float:
        """Calculate source authority score (0-1)"""
        source_priority = article.get('source_priority', 1)
        return min(source_priority / 3.0, 1.0)  # Max score for priority 3+
    
    def calculate_engagement_score(self, article: Dict) -> float:
        """Calculate engagement score (0-1)"""
        engagement = article.get('engagement', 0)
        # Normalize: assume 1000+ engagement = max score
        return min(engagement / 1000.0, 1.0)
    
    def calculate_ranking_score(self, article: Dict) -> float:
        """Calculate overall ranking score"""
        recency = self.calculate_recency_score(article)
        source = self.calculate_source_score(article)
        engagement = self.calculate_engagement_score(article)
        
        return (
            self.recency_weight * recency +
            self.source_weight * source +
            self.engagement_weight * engagement
        )
    
    def rank_articles(self, articles: List[Dict]) -> List[Dict]:
        """Rank and sort articles"""
        scored = [(self.calculate_ranking_score(a), a) for a in articles]
        scored.sort(key=lambda x: -x[0])
        
        return [a for score, a in scored]
    
    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles"""
        seen_hashes: set = set()
        unique = []
        
        for article in articles:
            if article['hash'] not in seen_hashes:
                seen_hashes.add(article['hash'])
                unique.append(article)
        
        removed = len(articles) - len(unique)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate articles")
        
        return unique
    
    def filter_and_process(self, articles: List[Dict]) -> List[Dict]:
        """Main processing pipeline"""
        logger.info(f"Processing {len(articles)} articles...")
        
        # Deduplicate
        articles = self.deduplicate_articles(articles)
        
        # Rank
        articles = self.rank_articles(articles)
        
        # Limit count
        articles = articles[:self.max_articles]
        
        # Mark as processed
        self.mark_processed(articles)
        
        logger.info(f"✓ Processed: {len(articles)} unique articles")
        return articles


# Convenience function
def process_articles(articles: List[Dict], config: dict = None) -> List[Dict]:
    """Process articles (convenience function)"""
    processor = NewsProcessor(config or {})
    return processor.filter_and_process(articles)


if __name__ == "__main__":
    # Test the processor
    import sys
    from modules.rss_fetcher import RSSFetcher
    
    logging.basicConfig(level=logging.INFO)
    
    # Load config
    import yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Fetch some test articles
    fetcher = RSSFetcher(config)
    articles = fetcher.fetch_all()
    
    if not articles:
        # Create test data
        articles = [
            {
                'hash': 'abc123',
                'source': 'Reuters',
                'source_priority': 1,
                'title': 'Test Article 1',
                'url': 'https://example.com/1',
                'summary': 'Test summary 1',
                'published': datetime.now(BJ_TIMEZONE),
                'engagement': 100
            },
            {
                'hash': 'def456',
                'source': 'Bloomberg',
                'source_priority': 1,
                'title': 'Test Article 2',
                'url': 'https://example.com/2',
                'summary': 'Test summary 2',
                'published': datetime.now(BJ_TIMEZONE),
                'engagement': 500
            }
        ]
    
    # Process
    processor = NewsProcessor(config)
    processed = processor.filter_and_process(articles)
    
    print(f"\nProcessed {len(processed)} articles:\n")
    for i, article in enumerate(processed[:5], 1):
        print(f"{i}. [{article['source']}] {article['title']}")
