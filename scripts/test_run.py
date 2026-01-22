#!/usr/bin/env python3
"""
Quick Test Script
Tests the news briefing without scheduling
"""

import sys
import os
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
import logging
from datetime import datetime
from modules.rss_fetcher_ssl import RSSFetcher  # Use SSL version
from modules.telegram_bot import TelegramBriefingBot
from modules.news_processor import NewsProcessor
from modules.summarizer import ArticleSummarizer


def main():
    """Run a test briefing"""
    print("=" * 60)
    print("Crypto News Briefing - Test Run")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    
    # Load config
    config_path = 'config.yaml'
    if not os.path.exists(config_path):
        config_path = '../config.yaml'
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    logger.info("\n📥 Fetching RSS feeds...")
    rss_fetcher = RSSFetcher(config)
    articles = rss_fetcher.fetch_all()
    
    logger.info(f"\n🔄 Processing {len(articles)} articles...")
    processor = NewsProcessor(config)
    articles = processor.filter_and_process(articles)
    
    logger.info(f"\n📝 Summarizing articles...")
    summarizer = ArticleSummarizer(config)
    articles = summarizer.summarize_articles(articles)
    
    # Format preview (don't send to Telegram)
    logger.info(f"\n📋 Formatted Briefing Preview:")
    logger.info("-" * 60)
    
    if not articles:
        logger.info("No articles found!")
        return
    
    for i, article in enumerate(articles[:5], 1):
        logger.info(f"{i}. [{article['source']}] {article['title']}")
        logger.info(f"   {article['url']}")
        logger.info(f"   {article['summary'][:100]}...")
        logger.info("")
    
    logger.info(f"... and {len(articles) - 5} more articles" if len(articles) > 5 else "")
    logger.info("-" * 60)
    
    logger.info(f"\n✅ Test complete! Found {len(articles)} articles.")
    logger.info("To send to Telegram, configure .env and run: python src/main.py once")
    
    # Ask if user wants to test Telegram
    if os.path.exists('.env'):
        send = input("\n🤖 Send to Telegram? (y/n): ").strip().lower()
        if send == 'y':
            # Load env vars
            from dotenv import load_dotenv
            load_dotenv()
            
            token = os.environ.get('TELEGRAM_BOT_TOKEN')
            chat_id = os.environ.get('TELEGRAM_CHAT_ID')
            
            if token and chat_id:
                logger.info("📤 Sending to Telegram...")
                bot = TelegramBriefingBot(token, chat_id, config.get('telegram', {}))
                success = bot.send_briefing(articles)
                
                if success:
                    logger.info("✅ Successfully sent to Telegram!")
                else:
                    logger.error("❌ Failed to send to Telegram")
            else:
                logger.warning("Telegram credentials not found in .env")
    else:
        logger.info("\n💡 Tip: Create .env file to enable Telegram notifications")


if __name__ == "__main__":
    main()
