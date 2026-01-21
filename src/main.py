#!/usr/bin/env python3
"""
Crypto News Briefing - Main Entry Point
Fetches crypto news from RSS feeds and Twitter, formats, and sends to Telegram
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from modules.rss_fetcher_ssl import RSSFetcher
from modules.telegram_bot import TelegramBriefingBot
from modules.news_processor import NewsProcessor
from modules.summarizer import ArticleSummarizer
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger


import logging
logger = logging.getLogger(__name__)

class CryptoNewsBriefing:
    """Main application class"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.rss_fetcher = RSSFetcher(self.config)
        self.processor = NewsProcessor(self.config)
        self.summarizer = ArticleSummarizer(self.config)
        
        # Telegram bot (optional)
        self.telegram_bot = None
        self._init_telegram()
        
        logger.info("Crypto News Briefing initialized")
    
    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        config_path = Path(self.config_path)
        
        if not config_path.exists():
            # Try default paths
            for default_path in ['config.yaml', '../config.yaml']:
                path = Path(default_path)
                if path.exists():
                    config_path = path
                    break
        
        if not config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            sys.exit(1)
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Configuration loaded: {config_path}")
        return config
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Create logs directory
        log_file = log_config.get('file', 'logs/briefing.log')
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        global logger
        logger = logging.getLogger(__name__)
    
    def _init_telegram(self):
        """Initialize Telegram bot"""
        import dotenv
        
        # Load environment variables
        dotenv.load_dotenv()
        
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if token and chat_id:
            self.telegram_bot = TelegramBriefingBot(
                token=token,
                chat_id=chat_id,
                config=self.config.get('telegram', {})
            )
            logger.info("✓ Telegram bot configured")
        else:
            logger.warning("✗ Telegram credentials not found (skipping Telegram)")
    
    def run_once(self) -> bool:
        """Run the news briefing process once"""
        logger.info("=" * 50)
        logger.info("Starting news briefing run...")
        logger.info("=" * 50)
        
        try:
            # Step 1: Fetch RSS news
            logger.info("📥 Step 1: Fetching RSS feeds...")
            articles = self.rss_fetcher.fetch_all()
            
            if not articles:
                logger.warning("No articles fetched from RSS feeds")
            
            # Step 2: Process articles (deduplicate, rank)
            logger.info("🔄 Step 2: Processing articles...")
            articles = self.processor.filter_and_process(articles)
            
            if not articles:
                logger.warning("No articles after processing")
            
            # Step 3: Summarize articles
            logger.info("📝 Step 3: Summarizing articles...")
            articles = self.summarizer.summarize_articles(articles)
            
            if not articles:
                logger.warning("No articles to summarize")
            
            # Step 4: Send to Telegram
            if self.telegram_bot:
                logger.info("📤 Step 4: Sending to Telegram...")
                success = self.telegram_bot.send_briefing_sync(articles)
                
                if success:
                    logger.info("✓ Briefing completed successfully!")
                else:
                    logger.error("✗ Failed to send to Telegram")
                
                return success
            else:
                logger.info("📋 Step 4: Telegram not configured, skipping send")
                logger.info(f"Found {len(articles)} articles:")
                for i, article in enumerate(articles[:5], 1):
                    logger.info(f"  {i}. [{article['source']}] {article['title'][:50]}...")
                
                return bool(articles)
        
        except Exception as e:
            logger.error(f"Error during briefing run: {e}", exc_info=True)
            return False
    
    def run_scheduled(self):
        """Run the scheduler"""
        scheduler_config = self.config.get('scheduler', {})
        interval_hours = scheduler_config.get('interval_hours', 2)
        timezone = scheduler_config.get('timezone', 'UTC')
        run_at_start = scheduler_config.get('run_at_start', True)
        
        logger.info(f"Starting scheduler: every {interval_hours} hours ({timezone})")
        
        scheduler = BlockingScheduler(timezone=timezone)
        
        # Add job
        scheduler.add_job(
            self.run_once,
            trigger=IntervalTrigger(hours=interval_hours),
            id='crypto_news_briefing',
            name='Fetch and send crypto news briefing',
            replace_existing=True,
            max_instances=1
        )
        
        # Run immediately if configured
        if run_at_start:
            logger.info("Running initial briefing...")
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Initial run failed: {e}")
        
        # Start scheduler
        logger.info("Scheduler started. Press Ctrl+C to stop.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped.")
    
    def cleanup(self):
        """Cleanup old data"""
        cleanup_days = self.config.get('database', {}).get('cleanup_days', 7)
        self.processor.cleanup_old_articles(cleanup_days)


def main():
    """Main entry point"""
    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ['--once', '-o', 'once']:
            # Run once and exit
            app = CryptoNewsBriefing()
            success = app.run_once()
            sys.exit(0 if success else 1)
        
        elif command in ['--help', '-h', 'help']:
            print("""
Crypto News Briefing

Usage:
    python main.py              # Run scheduled (every 2 hours)
    python main.py once         # Run once and exit
    python main.py help         # Show this help

Environment Variables:
    TELEGRAM_BOT_TOKEN  - Telegram bot token
    TELEGRAM_CHAT_ID    - Telegram chat ID to send to

Configuration:
    Edit config.yaml to customize feeds, keywords, and scheduling.
            """)
            sys.exit(0)
    
    # Default: run scheduled
    app = CryptoNewsBriefing()
    
    # Setup signal handlers
    import signal
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, cleaning up...")
        app.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run scheduled
    app.run_scheduled()


if __name__ == "__main__":
    main()
