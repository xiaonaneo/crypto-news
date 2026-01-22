#!/usr/bin/env python3
"""
加密货币新闻简报 - 纯中文版
- 全部中文显示
- 去掉所有图标
- 去掉分割线
- 每8小时推送10条
"""

import os, yaml, logging, ssl, urllib.request, feedparser, requests
from datetime import datetime, timedelta

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# SSL修复
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
    
    def clean_text(self, text: str, max_length: int = 200) -> str:
        if not text:
            return ""
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = ' '.join(text.split())
        if len(text) > max_length:
            text = text[:max_length] + "..."
        return text.strip()
    
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
                        
                        articles.append({
                            'title': self.clean_text(title, 150),
                            'summary': self.clean_text(summary, 500),
                            'source': feed['name'],
                            'source_zh': feed.get('zh_name', feed['name']),
                            'url': entry.link,
                            'published': pub_date
                        })
                        count += 1
                        
                    except Exception as e:
                        continue
                
                logger.info(f"   获取 {count} 篇\n")
                
            except Exception as e:
                logger.error(f"   错误: {e}\n")
        
        articles.sort(key=lambda x: x['published'].timestamp(), reverse=True)
        
        logger.info(f"总计获取 {len(articles)} 篇加密货币新闻")
        return articles[:10]

def generate_summary(title: str, summary: str) -> tuple:
    """生成中文摘要和详情"""
    title_clean = title.strip()
    summary_clean = summary.strip()
    
    # 摘要（50字）
    if len(summary_clean) > 50:
        brief = summary_clean[:50] + "..."
    else:
        brief = summary_clean
    
    # 详情（200字）
    if len(summary_clean) > 200:
        detail = summary_clean[:200] + "..."
    else:
        detail = summary_clean
    
    return brief, detail

def send_to_telegram(articles):
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not TOKEN or not CHAT_ID:
        logger.error("未找到Telegram配置！")
        return False
    
    # 构建纯中文消息
    lines = []
    lines.append("加密货币新闻简报")
    lines.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")
    lines.append(f"共收录 {len(articles)} 条最新资讯")
    lines.append("")
    
    for i, article in enumerate(articles, 1):
        brief, detail = generate_summary(article['title'], article.get('summary', ''))
        
        # 新闻条目
        lines.append(f"{i}. {article['title']}")
        lines.append("")
        lines.append(f"来源: {article['source_zh']}")
        lines.append(f"时间: {article['published'].strftime('%H:%M')}")
        lines.append("")
        lines.append(f"摘要: {brief}")
        lines.append("")
        lines.append(f"详情: {detail}")
        lines.append("")
    
    # 底部信息
    lines.extend([
        "自动加密货币新闻系统",
        "",
        "新闻来源:",
        "- 加密货币新闻网站 (CoinTelegraph)",
        "- 加密货币新闻网站 (CoinDesk)",
        "- 比特币杂志 (Bitcoin Magazine)",
        "- 加密新闻媒体 (Decrypt)",
        "- 加密货币新闻网站 (CryptoSlate)",
        "- 区块链新闻网站 (The Block)",
        "- 路透社 (Reuters)",
        "- 彭博社 (Bloomberg)",
        "- 金融时报 (Financial Times)",
        "- 美国全国广播公司 (CNBC)",
        "",
        f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"原文链接: {articles[0]['url']}" if articles else ""
    ])
    
    message = "\n".join(lines)
    
    logger.info("发送到Telegram...")
    
    # 分段发送
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
    print("加密货币新闻简报系统 - 纯中文版")
    print("=" * 70)
    print()
    
    logger.info("正在抓取最新加密货币新闻...")
    fetcher = CryptoNewsFetcher()
    articles = fetcher.fetch_all()
    print()
    
    if not articles:
        logger.warning("未找到相关新闻")
        return
    
    logger.info("新闻预览:")
    for i, a in enumerate(articles[:3], 1):
        logger.info(f"   {i}. {a['title'][:50]}...")
    print()
    
    success = send_to_telegram(articles)
    
    print()
    print("=" * 70)
    if success:
        print("完成！请检查Telegram群组获取完整新闻简报！")
    else:
        print("发送失败，请检查配置")
    print("=" * 70)

if __name__ == "__main__":
    main()
