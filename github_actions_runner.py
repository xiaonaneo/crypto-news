#!/usr/bin/env python3
"""
加密货币新闻简报 - GitHub Actions 版本
完全复刻本地部署 (src/main.py) 的所有功能：
- RSS 抓取 (SSL 处理) → 处理去重 → AI 摘要(翻译+摘要) → 精美格式发送
"""

import os, sys, yaml, logging, ssl, urllib.request, feedparser, requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Beijing timezone for display
BJ_TIMEZONE = timezone(timedelta(hours=8))


# ============== SSL 处理 ==============
_orig_urlopen = urllib.request.urlopen

def _patched_urlopen(url, *a, **k):
    """修复 SSL 和 URL 类型问题"""
    try:
        if isinstance(url, urllib.request.Request):
            return _orig_urlopen(url, *a, **k, context=ssl_context)
        return _orig_urlopen(url, *a, **k, context=ssl_context)
    except Exception:
        pass
    
    # Fallback: 直接使用 requests
    if isinstance(url, urllib.request.Request):
        url = url.full_url
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        return resp.raw
    except:
        return _orig_urlopen(url, *a, **k)

urllib.request.urlopen = _patched_urlopen

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


# ============== 工具函数 ==============
def clean_text(text: str) -> str:
    """清理 HTML 标签和多余空格"""
    if not text:
        return ""
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def safe_get(data: dict, *keys, default="") -> str:
    """安全获取嵌套字典值"""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data if data else default


# ============== AI 摘要模块 ==============
def fetch_article_content(url: str) -> str:
    """获取文章正文内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'nav']):
            tag.decompose()

        content = None
        selectors = [
            'article', '[role="main"]', '.article-content', '.post-content',
            '.entry-content', '.content-body', '.story-body', 'main',
            '.news-content', '.article-body'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem and len(elem.get_text(strip=True)) > 200:
                content = elem
                break

        if not content:
            content = soup.find('body')

        if content:
            text = content.get_text(separator=' ', strip=True)
            return clean_text(text)[:3000]

        return ""
    except Exception as e:
        logger.debug(f"Failed to fetch article: {e}")
        return ""


def summarize_with_deepseek(title: str, summary: str, url: str = "") -> Dict[str, str]:
    """使用 DeepSeek AI 翻译标题并生成摘要"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return {"title_cn": clean_text(title), "summary": clean_text(summary)[:150]}

    try:
        content = fetch_article_content(url) if url else ""

        if content:
            prompt = f"""请用中文完成以下任务：

1. 将标题翻译成简洁的中文（不超过25字）
2. 阅读文章内容，用不超过100个汉字总结文章要点（只保留与加密货币直接相关的内容）

标题：{title}
来源：{summary[:500]}

文章内容：
{content[:2000]}

请用以下格式输出：
标题翻译：[中文标题]
摘要：[不超过100字的摘要]
"""
        else:
            prompt = f"""请用中文完成以下任务：

1. 将标题翻译成简洁的中文（不超过25字）
2. 根据标题和摘要生成一个不超过100字的摘要

标题：{title}
摘要：{summary[:500]}

请用以下格式输出：
标题翻译：[中文标题]
摘要：[不超过100字的摘要]
"""

        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.3
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("choices") and len(data["choices"]) > 0:
                result = data["choices"][0]["message"]["content"].strip()

                title_cn = clean_text(title)
                summary_cn = clean_text(summary)[:150]

                for line in result.split('\n'):
                    line = line.strip()
                    if line.startswith('标题翻译：'):
                        title_cn = line.replace('标题翻译：', '').strip()
                    elif line.startswith('摘要：'):
                        summary_cn = line.replace('摘要：', '').strip()

                return {"title_cn": title_cn, "summary": summary_cn}

    except Exception as e:
        logger.debug(f"DeepSeek API error: {e}")

    return {"title_cn": clean_text(title), "summary": clean_text(summary)[:150]}


# ============== RSS 抓取模块 ==============
def fetch_single_feed(feed: dict, cutoff_time, crypto_keywords: List[str]) -> List[Dict]:
    """单线程抓取单个 RSS 源"""
    url = feed.get("url", "")
    name = feed.get("name", "Unknown")
    crypto_only = feed.get("crypto_only", False)
    priority = feed.get("priority", 3)
    articles = []

    try:
        logger.info(f"📡 Fetching: {name}")

        # 使用 requests 获取内容
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)

        if resp.status_code != 200:
            logger.warning(f"   ✗ HTTP {resp.status_code}")
            return []

        feed_data = feedparser.parse(resp.content)

        if not feed_data.entries:
            logger.warning(f"   ✗ No entries")
            return []

        count = 0
        for entry in feed_data.entries[:30]:
            try:
                pub_date = datetime.now(BJ_TIMEZONE)
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        utc_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        pub_date = utc_dt.astimezone(BJ_TIMEZONE)
                    except:
                        pass
                    if pub_date < cutoff_time:
                        continue

                title = safe_get(entry, "title", default="")
                if not title:
                    continue

                summary = safe_get(entry, "summary", default="") or safe_get(entry, "description", default="")
                url = safe_get(entry, "link", default="")

                # 过滤加密货币关键词
                if not crypto_only:
                    text = (title + " " + summary).lower()
                    if not any(kw.lower() in text for kw in crypto_keywords):
                        continue

                # AI 摘要
                ai_result = summarize_with_deepseek(title, summary, url)

                articles.append({
                    "title": title,
                    "title_cn": ai_result["title_cn"],
                    "summary": ai_result["summary"],
                    "source": name,
                    "url": url,
                    "published": pub_date,
                    "priority": priority
                })
                count += 1
            except Exception:
                continue

        logger.info(f"   ✓ Found {count} crypto articles")
        return articles

    except Exception as e:
        logger.error(f"   ✗ Error: {str(e)[:50]}")
        return []


class RSSFetcher:
    """RSS 抓取器 - 优化版，支持并行抓取"""
    def __init__(self, config: dict):
        self.config = config
        self.feeds = config.get("rss_sources", [])
        self.lookback_hours = config.get("processing", {}).get("hours_lookback", 12)

    def fetch_all(self) -> List[Dict]:
        articles = []
        cutoff_time = datetime.now(BJ_TIMEZONE) - timedelta(hours=self.lookback_hours)
        crypto_keywords = self.config.get("crypto_keywords", [])

        # 过滤启用的源
        enabled_feeds = [f for f in self.feeds if f.get("enabled", True)]

        # 并行抓取 (最多 5 个并发)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(fetch_single_feed, feed, cutoff_time, crypto_keywords): feed
                for feed in enabled_feeds
            }

            for future in as_completed(futures):
                feed_articles = future.result()
                articles.extend(feed_articles)

        # 按时间排序
        articles.sort(key=lambda x: x["published"].timestamp(), reverse=True)

        max_articles = self.config.get("processing", {}).get("max_articles", 10)
        logger.info(f"📊 Total: {len(articles)} articles (max {max_articles})")
        return articles[:max_articles]


# ============== 价格获取模块 ==============
def fetch_btc_price() -> Dict:
    """获取 BTC 价格"""
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            btc = data.get("bitcoin", {})
            return {
                "price": btc.get("usd", 0),
                "change_24h": btc.get("usd_24h_change", 0)
            }
    except Exception as e:
        logger.debug(f"BTC price fetch failed: {e}")
    return {"price": 0, "change_24h": 0}


# ============== Telegram 格式化模块 ==============
def format_briefing(articles: List[Dict], prices: Dict = None) -> str:
    """格式化简报"""
    if not articles:
        return "📰 *加密新闻简报*\n\n本周期未找到新文章。"

    lines = []

    lines.append("*加密新闻简报*")
    lines.append(datetime.now(BJ_TIMEZONE).strftime('%Y-%m-%d %H:%M'))
    lines.append("")

    if prices and prices.get("price"):
        change = prices.get("change_24h", 0)
        change_str = f"{change:+.2f}%" if change else ""
        lines.append(f"*₿ ${prices['price']:,.0f} {change_str}*")
        lines.append("")

    for i, article in enumerate(articles, 1):
        title = article.get("title_cn", article.get("title", ""))
        summary = article.get("summary", "")
        source = article.get("source", "Unknown")
        url = article.get("url", "")
        time_str = article["published"].strftime("%H:%M")

        lines.append(f"*{i} {title}*")
        lines.append(f"{summary}")
        if url:
            lines.append(f"[{source}]({url}) | {time_str}")
        else:
            lines.append(f"_{source} | {time_str}_")
        lines.append("")

    return "\n".join(lines)


def send_to_telegram(articles: List[Dict], prices: Dict = None) -> bool:
    """发送到 Telegram"""
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

    if not TOKEN or not CHAT_ID:
        logger.error("Telegram credentials not configured!")
        return False

    message = format_briefing(articles, prices)
    logger.info("📤 Sending to Telegram...")

    if len(message) > 4000:
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for i, chunk in enumerate(chunks, 1):
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": CHAT_ID,
                    "text": chunk,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                },
                timeout=30
            )
            if resp.status_code != 200:
                logger.error(f"Failed chunk {i}: {resp.status_code}")
                return False
    else:
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
        logger.info(f"✓ Successfully sent {len(articles)} articles to Telegram!")
        return True
    else:
        logger.error(f"Failed to send: {resp.status_code}")
        return False


# ============== 主函数 ==============
def main():
    """主入口"""
    print("=" * 60)
    print("🚀 Crypto News Briefing - GitHub Actions")
    print("=" * 60)
    print()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        logger.warning("⚠️ DEEPSEEK_API_KEY not set")

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    logger.info("📊 Step 0: Fetching market prices...")
    prices = fetch_btc_price()
    if prices.get("price"):
        change = prices.get("change_24h", 0)
        change_str = f"{change:+.2f}%" if change else ""
        logger.info(f"   BTC: ${prices['price']:,.0f} {change_str}")

    logger.info("\n📥 Step 1: Fetching RSS feeds (parallel)...")
    fetcher = RSSFetcher(config)
    articles = fetcher.fetch_all()

    if not articles:
        logger.warning("No articles found!")
        return

    print()
    logger.info("📋 Preview:")
    for i, a in enumerate(articles[:5], 1):
        logger.info(f"   {i}. {a['title_cn'][:40]}... ({a['source']})")
    print()

    logger.info("📤 Step 2: Sending to Telegram...")
    if send_to_telegram(articles, prices):
        print("=" * 60)
        print("✅ Done! Check Telegram for the briefing.")
        print("=" * 60)
    else:
        print("❌ Failed to send to Telegram")


if __name__ == "__main__":
    main()
