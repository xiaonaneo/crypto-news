"""
Telegram Bot Module
Handles sending briefings to Telegram
"""

import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramBriefingBot:
    """Sends crypto news briefings to Telegram"""
    
    def __init__(self, token: str, chat_id: str, config: dict = None):
        self.token = token
        self.chat_id = chat_id
        self.config = config or {}
        self.max_length = self.config.get('max_message_length', 4000)
        self.parse_mode = self.config.get('parse_mode', 'Markdown')
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 5)
    
    async def send_message_with_retry(self, bot: Bot, text: str) -> bool:
        """Send message with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=self.parse_mode,
                    disable_web_page_preview=True
                )
                return True
            
            except TelegramError as e:
                logger.warning(f"Telegram send attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to send message after {self.retry_attempts} attempts")
                    return False
        
        return False
    
    def format_briefing(self, articles: List[Dict]) -> str:
        """Format articles into a nice briefing"""
        if not articles:
            return "📰 *Crypto News Briefing*\n\nNo new articles found in this cycle."
        
        lines = []
        
        # Header
        lines.append("📰 *Crypto News Briefing*")
        lines.append(f"_{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}_")
        lines.append("")
        lines.append(f"📊 Found {len(articles)} crypto articles")
        lines.append("")
        lines.append("─" * 30)
        lines.append("")
        
        # Articles
        for i, article in enumerate(articles[:10], 1):  # Limit to 10
            # Title with emoji based on source
            source_emoji = {
                'Reuters': '🔴',
                'Bloomberg': '🔵',
                'Financial Times': '🟠',
                'Wall Street Journal': '🟣',
                'CNBC': '🔷',
                'Twitter': '🐦'
            }.get(article.get('source', '📰'), '📰')
            
            lines.append(f"{source_emoji} *{i}. {article['title']}*")
            lines.append("")
            
            # Metadata
            meta_parts = []
            if article.get('source'):
                meta_parts.append(f"📍 {article['source']}")
            if article.get('published'):
                meta_parts.append(f"🕐 {article['published'].strftime('%H:%M')}")
            if article.get('engagement', 0) > 0:
                meta_parts.append(f"❤️ {article['engagement']}")
            
            if meta_parts:
                lines.append("   " + " • ".join(meta_parts))
                lines.append("")
            
            # Summary
            if article.get('summary'):
                lines.append(f"   📝 {article['summary']}")
                lines.append("")
            
            # URL
            if article.get('url'):
                lines.append(f"   🔗 [Read more]({article['url']})")
                lines.append("")
            
            lines.append("─" * 30)
            lines.append("")
        
        # Footer
        lines.append("🤖 *Automated Crypto News Briefing*")
        lines.append("📡 Sources: Reuters, Bloomberg, FT, WSJ, CNBC + Twitter/X")
        
        return "\n".join(lines)
    
    async def send_briefing(self, articles: List[Dict]) -> bool:
        """Send formatted briefing to Telegram"""
        if not self.token or not self.chat_id:
            logger.error("Telegram credentials not configured")
            return False
        
        try:
            bot = Bot(token=self.token)
            
            # Format the briefing
            briefing = self.format_briefing(articles)
            
            # Check message length
            if len(briefing) > self.max_length:
                logger.info(f"Message too long ({len(briefing)} chars), splitting...")
                
                # Split into chunks
                chunks = []
                current_chunk = ""
                
                for line in briefing.split("\n"):
                    if len(current_chunk) + len(line) + 1 > self.max_length:
                        chunks.append(current_chunk)
                        current_chunk = line
                    else:
                        current_chunk += "\n" + line if current_chunk else line
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Send chunks
                success = True
                for i, chunk in enumerate(chunks, 1):
                    logger.info(f"Sending chunk {i}/{len(chunks)}")
                    if not await self.send_message_with_retry(bot, chunk):
                        success = False
                
                return success
            
            else:
                # Send as single message
                success = await self.send_message_with_retry(bot, briefing)
                
                if success:
                    logger.info(f"✓ Briefing sent successfully: {len(articles)} articles")
                else:
                    logger.error("✗ Failed to send briefing")
                
                return success
        
        except Exception as e:
            logger.error(f"✗ Error sending to Telegram: {e}")
            return False
    
    def send_briefing_sync(self, articles: List[Dict]) -> bool:
        """Synchronous wrapper for send_briefing"""
        return asyncio.run(self.send_briefing(articles))


# Convenience function
def send_telegram_briefing(articles: List[Dict], token: str = None, chat_id: str = None) -> bool:
    """Send briefing to Telegram (synchronous)"""
    if not token or not chat_id:
        logger.error("Telegram token and chat_id required")
        return False
    
    bot = TelegramBriefingBot(token, chat_id)
    return bot.send_briefing_sync(articles)


if __name__ == "__main__":
    # Test the Telegram bot
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    # Create test articles
    test_articles = [
        {
            'source': 'Reuters',
            'title': 'Bitcoin surges past $50,000 as institutional interest grows',
            'url': 'https://example.com/article1',
            'summary': 'Bitcoin rallied above $50,000 for the first time this year...',
            'published': datetime.now(),
            'engagement': 0
        },
        {
            'source': 'Bloomberg',
            'title': 'Ethereum ETF approval odds increase: analysts',
            'url': 'https://example.com/article2',
            'summary': 'Analysts are raising their probability estimates for an Ethereum ETF approval...',
            'published': datetime.now(),
            'engagement': 0
        }
    ]
    
    # Test formatting
    bot = TelegramBriefingBot("test_token", "test_chat_id")
    briefing = bot.format_briefing(test_articles)
    
    print("Formatted briefing:")
    print(briefing)
    print(f"\nLength: {len(briefing)} characters")
