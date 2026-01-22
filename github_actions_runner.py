#!/usr/bin/env python3
"""
加密货币新闻简报 - 完整版
- 完整句子
- 丰富内容
- 每8小时推送10条
"""

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

def clean_html(text: str) -> str:
    if not text:
        return ""
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def translate_text(text: str) -> str:
    if not text:
        return ""
    text = clean_html(text)
    if len(text) < 5:
        return text
    try:
        result = translator.translate(text)
        return result if result else text
    except:
        return text

def create_content(title: str, summary: str, source: str) -> str:
    """根据标题生成完整内容"""
    title_zh = translate_text(title)
    summary_zh = translate_text(summary)
    
    title_zh = clean_html(title_zh)
    summary_zh = clean_html(summary_zh)
    
    # 如果摘要有用，用摘要
    if len(summary_zh) > len(title_zh) + 20:
        # 确保句子完整
        content = summary_zh
        if len(content) > 150:
            # 在句号处截断
            for i in range(140, len(content)):
                if content[i] in '。！？':
                    return content[:i+1].strip()
        return content.strip()
    
    # 否则用标题
    # 标题转陈述句
    content = title_zh
    if not content.endswith(('。', '！', '？')):
        content += '。'
    
    return content

class CryptoNewsFetcher:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.feeds = self.config.get('rss_sources', [])
        self.crypto_keywords = self.config.get('crypto_keywords', [])
        self.lookback_hours = self.config.get('processing', {}).get('hours_lookback', 12)
    
    def is_crypto_related(self, title: str, summary: str, crypto_only: bool = False) -> bool:
        if crypto_only:
            return True
        text = f"{title} {summary}".lower()
        return any(kw.lower() in text for kw in self.crypto_keywords)
    
    def fetch_all(self):
        articles = []
        cutoff_time = datetime.now() - timedelta(hours=self.lookback_hours)
        
        for feed in self.feeds:
            if not feed.get('enabled', True):
                continue
            
            try:
                logger.info(f"正在抓取: {feed.get('zh_name', feed['name'])}")
                feed_data = feedparser.parse(feed['url'])
                crypto_only = feed.get('crypto_only', False)
                
                count = 0
                for entry in feed_data.entries[:30]:
                    try:
                        pub_date = datetime.now()
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                            if pub_date < cutoff_time:
                                continue
                        
                        title = entry.get('title', '')
                        summary = entry.get('summary', entry.get('description', ''))
                        
                        if not self.is_crypto_related(title, summary, crypto_only):
                            continue
                        
                        title_zh = translate_text(title)
                        content = create_content(title, summary, feed.get('zh_name', ''))
                        
                        articles.append({
                            'title': title_zh,
                            'content': content,
                            'source_zh': feed.get('zh_name', feed['name']),
                            'url': entry.link,
                            'published': pub_date
                        })
                        count += 1
                        
                    except:
                        continue
                
                logger.info(f"   获取 {count} 篇\n")
                
            except Exception as e:
                logger.error(f"   错误: {e}\n")
        
        articles.sort(key=lambda x: x['published'].timestamp(), reverse=True)
        
        logger.info(f"总计获取 {len(articles)} 篇加密货币新闻")
        return articles[:10]

def send_to_telegram(articles):
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not TOKEN or not CHAT_ID:
        logger.error("未找到Telegram配置！")
        return False
    
    lines = []
    lines.append("加密货币新闻简报")
    lines.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")
    
    for i, article in enumerate(articles, 1):
        lines.append(f"{i}. {article['title']}")
        lines.append(f"{article['content']}")
        lines.append(f"来源: {article['source_zh']}")
        lines.append("")
    
    message = "\n".join(lines)
    
    logger.info("发送到Telegram...")
    
    if len(message) > 4000:
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for i, chunk in enumerate(chunks, 1):
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": chunk, "disable_web_page_preview": True},
                timeout=30
            )
            if resp.status_code != 200:
                logger.error(f"发送第{i}部分失败: {resp.status_code}")
                return False
    else:
        resp = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message, "disable_web_page_preview": True},
            timeout=30
        )
    
    if resp.status_code == 200:
        logger.info("成功发送到Telegram！")
        return True
    else:
        logger.error(f"发送失败: {resp.status_code}")
        return False

def main():
    print("=" * 70)
    print("加密货币新闻简报系统 - 完整版")
    print("=" * 70)
    print()
    
    logger.info("正在抓取并翻译最新加密货币新闻...")
    fetcher = CryptoNewsFetcher()
    articles = fetcher.fetch_all()
    print()
    
    if not articles:
        logger.warning("未找到相关新闻")
        return
    
    logger.info("新闻预览:")
    for i, a in enumerate(articles[:3], 1):
        logger.info(f"   {i}. {a['title'][:40]}...")
        logger.info(f"      {a['content'][:60]}...")
    print()
    
    success = send_to_telegram(articles)
    
    print()
    print("=" * 70)
    if success:
        print("完成！请检查Telegram群组获取新闻简报！")
    else:
        print("发送失败，请检查配置")
    print("=" * 70)

if __name__ == "__main__":
    main()
