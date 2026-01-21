#!/usr/bin/env python3
"""
GitHub Actions Crypto News Runner
Simplified version for GitHub Actions
"""

import os, yaml, logging, ssl, urllib.request, feedparser, requests
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# SSL fix
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
_orig = urllib.request.urlopen
def _patch(url, *a, **k):
    try: return _orig(url, *a, **k, context=ctx)
    except:
        import urllib.request
        req = urllib.request.Request(url)
        return urllib.request.urlopen(req, timeout=30)
urllib.request.urlopen = _patch

class CryptoNewsFetcher:
    def __init__(self):
        self.feeds = [
            {'name': 'CoinTelegraph', 'url': 'https://cointelegraph.com/rss', 'enabled': True, 'priority': 2, 'crypto_only': True},
            {'name': 'CoinDesk', 'url': 'https://www.coindesk.com/arc/outboundfeeds/rss/', 'enabled': True, 'priority': 2, 'crypto_only': True},
        ]
    
    def fetch_all(self):
        articles = []
        for f in self.feeds:
            if not f['enabled']: continue
            try:
                logger.info(f"📥 Fetching: {f['name']}")
                feed = feedparser.parse(f['url'])
                for e in feed.entries[:30]:
                    try:
                        pub_date = datetime.now()
                        if hasattr(e, 'published_parsed') and e.published_parsed:
                            pub_date = datetime(*e.published_parsed[:6])
                            if pub_date < datetime.now() - timedelta(hours=24):
                                continue
                        
                        articles.append({
                            'title': e.get('title', '')[:80],
                            'source': f['name'],
                            'url': e.link,
                            'published': pub_date
                        })
                    except Exception as ex:
                        logger.debug(f"Error parsing entry: {ex}")
            except Exception as e:
                logger.error(f"✗ Error {f['name']}: {e}")
        
        logger.info(f"✅ Total: {len(articles)} articles")
        return articles[:10]

def send_to_telegram(articles):
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not TOKEN or not CHAT_ID:
        logger.error("❌ Telegram credentials not found!")
        return False
    
    # Build message
    lines = [
        "📰 *Crypto News Briefing*",
        f"_{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        f"📊 Found {len(articles)} crypto articles",
        "",
        "-" * 30,
        ""
    ]
    
    for i, a in enumerate(articles, 1):
        emoji = "📰" if a['source'] == 'CoinTelegraph' else "📊"
        lines.append(f"{emoji} *{i}. {a['title']}*")
        lines.append("")
        lines.append(f"   📍 {a['source']} • 🕐 {a['published'].strftime('%H:%M')}")
        lines.append("")
    
    lines.extend([
        "-" * 30,
        "",
        "🤖 *Automated Crypto News Briefing*",
        "📡 Sources: CoinTelegraph, CoinDesk"
    ])
    
    message = "\n".join(lines)
    
    # Send
    logger.info("📤 Sending to Telegram...")
    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        },
        timeout=30
    )
    
    if resp.status_code == 200:
        logger.info("✅ SUCCESS! News sent to Telegram!")
        return True
    else:
        logger.error(f"❌ FAILED: {resp.status_code}")
        return False

def main():
    print("=" * 70)
    print("🚀 Crypto News Briefing - GitHub Actions")
    print("=" * 70)
    print()
    
    # Fetch news
    logger.info("📥 Fetching crypto news...")
    fetcher = CryptoNewsFetcher()
    articles = fetcher.fetch_all()
    print()
    
    # Send
    success = send_to_telegram(articles)
    
    print()
    print("=" * 70)
    if success:
        print("🎉 Done! Check your Telegram for the news briefing!")
    else:
        print("❌ Failed to send news")
    print("=" * 70)

if __name__ == "__main__":
    main()
