#!/usr/bin/env python3
import os, yaml, logging, ssl, urllib.request, feedparser, requests
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)
translator = GoogleTranslator(source='auto', target='zh-CN')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
_orig = urllib.request.urlopen

def _patch(url, *a, **k):
    try: return _orig(url, *a, **k, context=ctx)
    except:
        req = urllib.request.Request(url)
        return urllib.request.urlopen(req, timeout=30)

urllib.request.urlopen = _patch

def translate_text(text):
    if not text:
        return ""
    try:
        return translator.translate(text) or text
    except:
        return text

class CryptoNewsFetcher:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.feeds = self.config.get("rss_sources", [])
        self.lookback_hours = self.config.get("processing", {}).get("hours_lookback", 12)
    
    def fetch_all(self):
        articles = []
        cutoff_time = datetime.now() - timedelta(hours=self.lookback_hours)
        
        for feed in self.feeds:
            if not feed.get("enabled", True):
                continue
            
            try:
                logger.info("正在抓取: " + feed.get('zh_name', feed['name']))
                feed_data = feedparser.parse(feed["url"])
                
                count = 0
                for entry in feed_data.entries[:30]:
                    try:
                        pub_date = datetime.now()
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                            if pub_date < cutoff_time:
                                continue
                        
                        title = entry.get("title", "")
                        articles.append({
                            "title": translate_text(title),
                            "source_zh": feed.get("zh_name", feed["name"]),
                            "published": pub_date
                        })
                        count += 1
                    except:
                        continue
                
                logger.info("   获取 " + str(count) + " 篇")
            except Exception as e:
                logger.error("   错误: " + str(e))
        
        articles.sort(key=lambda x: x["published"].timestamp(), reverse=True)
        logger.info("总计获取 " + str(len(articles)) + " 篇加密货币新闻")
        return articles[:10]

def send_to_telegram(articles):
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not TOKEN or not CHAT_ID:
        logger.error("未找到Telegram配置！")
        return False
    
    lines = ["加密货币新闻简报", datetime.now().strftime("%Y-%m-%d %H:%M"), ""]
    for i, a in enumerate(articles, 1):
        lines.append(str(i) + ". " + a['title'])
        lines.append("")
    
    message = "\n".join(lines)
    
    logger.info("发送到Telegram...")
    resp = requests.post(
        "https://api.telegram.org/bot" + TOKEN + "/sendMessage",
        json={"chat_id": CHAT_ID, "text": message, "disable_web_page_preview": True},
        timeout=30
    )
    
    return resp.status_code == 200

def main():
    print("=" * 70)
    print("加密货币新闻简报系统 - 标题版")
    print("=" * 70)
    print()
    
    logger.info("正在抓取加密货币新闻标题...")
    fetcher = CryptoNewsFetcher()
    articles = fetcher.fetch_all()
    print()
    
    if not articles:
        logger.warning("未找到相关新闻")
        return
    
    logger.info("新闻预览:")
    for i, a in enumerate(articles[:5], 1):
        logger.info("   " + str(i) + ". " + a['title'])
    print()
    
    if send_to_telegram(articles):
        print("完成！请检查Telegram群组获取新闻简报！")
    else:
        print("发送失败")

if __name__ == "__main__":
    main()
