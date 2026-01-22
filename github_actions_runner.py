#!/usr/bin/env python3
"""
加密货币新闻简报 - GitHub Actions 版本
完全复刻本地运行流程：
- RSS 抓取 → 处理 → AI摘要(翻译+摘要) → 精美格式发送
"""

import os, yaml, logging, ssl, urllib.request, feedparser, requests
from datetime import datetime, timedelta
from typing import List, Dict

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
        req = urllib.request.Request(url)
        return urllib.request.urlopen(req, timeout=30)

urllib.request.urlopen = _patch


def clean_html(text):
    if not text:
        return ""
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fetch_article_content(url: str) -> str:
    """Fetch article content from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()

        content = None
        selectors = ['article', '[role="main"]', '.article-content', '.post-content',
                     '.entry-content', '.content-body', '.story-body', 'main']

        for selector in selectors:
            content = soup.select_one(selector)
            if content and len(content.get_text(strip=True)) > 200:
                break

        if not content:
            content = soup.find('body')

        if content:
            text = content.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:3000]

        return ""
    except Exception as e:
        logger.debug(f"Failed to fetch {url}: {e}")
        return ""


def summarize_with_deepseek(title: str, summary: str, url: str = "") -> Dict[str, str]:
    """使用 DeepSeek AI 翻译标题并生成摘要（复刻本地逻辑）"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")

    if not api_key:
        logger.warning("DEEPSEEK_API_KEY not set, using original title")
        return {"title_cn": clean_html(title), "summary": clean_html(summary)[:200]}

    try:
        # 获取文章内容
        content = fetch_article_content(url) if url else ""

        if content:
            prompt = f"""
请用中文完成以下任务：

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
            prompt = f"""
请用中文完成以下任务：

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
                "max_tokens": 300
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("choices") and len(data["choices"]) > 0:
                result = data["choices"][0]["message"]["content"].strip()

                title_cn = clean_html(title)
                summary_cn = clean_html(summary)[:200]

                for line in result.split('\n'):
                    if line.startswith('标题翻译：'):
                        title_cn = line.replace('标题翻译：', '').strip()
                    elif line.startswith('摘要：'):
                        summary_cn = line.replace('摘要：', '').strip()

                return {"title_cn": title_cn, "summary": summary_cn}

    except Exception as e:
        logger.debug(f"DeepSeek API error: {e}")

    return {"title_cn": clean_html(title), "summary": clean_html(summary)[:200]}


class RSSFetcher:
    """RSS Feed Fetcher"""
    def __init__(self, config: dict):
        self.config = config
        self.feeds = config.get("rss_sources", [])
        self.lookback_hours = config.get("processing", {}).get("hours_lookback", 12)

    def fetch_all(self) -> List[Dict]:
        articles = []
        cutoff_time = datetime.now() - timedelta(hours=self.lookback_hours)

        for feed in self.feeds:
            if not feed.get("enabled", True):
                continue

            try:
                logger.info(f"📡 Fetching: {feed.get('zh_name', feed['name'])}")
                feed_data = feedparser.parse(feed["url"])
                crypto_only = feed.get("crypto_only", False)
                crypto_keywords = self.config.get("crypto_keywords", [])

                count = 0
                for entry in feed_data.entries[:30]:
                    try:
                        pub_date = datetime.now()
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                            if pub_date < cutoff_time:
                                continue

                        title = entry.get("title", "")
                        summary = entry.get("summary", entry.get("description", ""))
                        url = entry.get("link", "")

                        # Check crypto keywords
                        if not crypto_only:
                            text = (title + " " + summary).lower()
                            if not any(kw.lower() in text for kw in crypto_keywords):
                                continue

                        # AI summarize
                        ai_result = summarize_with_deepseek(title, summary, url)

                        articles.append({
                            "title": title,
                            "title_cn": ai_result["title_cn"],
                            "summary": ai_result["summary"],
                            "source": feed["name"],
                            "source_zh": feed.get("zh_name", feed["name"]),
                            "url": url,
                            "published": pub_date
                        })
                        count += 1
                    except Exception as e:
                        continue

                logger.info(f"   ✓ Found {count} crypto articles")
            except Exception as e:
                logger.error(f"   ✗ Error: {e}")

        articles.sort(key=lambda x: x["published"].timestamp(), reverse=True)
        max_articles = self.config.get("processing", {}).get("max_articles", 10)
        logger.info(f"📊 Total: {len(articles)} articles (limited to {max_articles})")
        return articles[:max_articles]


def fetch_btc_price() -> Dict:
    """Fetch BTC price from CoinGecko"""
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "price": data.get("bitcoin", {}).get("usd", 0),
                "change_24h": data.get("bitcoin", {}).get("usd_24h_change", 0)
            }
    except Exception as e:
        logger.debug(f"BTC price fetch failed: {e}")
    return {"price": 0, "change_24h": 0}


def format_briefing(articles: List[Dict], prices: Dict = None) -> str:
    """Format articles into beautiful briefing (复刻本地格式)"""
    if not articles:
        return "📰 *加密新闻简报*\n\n本周期未找到新文章。"

    lines = []

    # Header
    lines.append("*加密新闻简报*")
    lines.append(datetime.now().strftime('%Y-%m-%d %H:%M'))
    lines.append("")

    # BTC price
    if prices and prices.get("price"):
        change = prices.get("change_24h", 0)
        change_str = f"{change:+.2f}%" if change else ""
        lines.append(f"*₿ ${prices['price']:,.0f} {change_str}*")
        lines.append("")

    # Articles: 标题、摘要、来源、时间、链接
    for i, article in enumerate(articles, 1):
        title = article.get("title_cn", article.get("title", ""))
        summary = article.get("summary", "")
        source = article.get("source_zh", article.get("source", ""))
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
    """Send formatted briefing to Telegram"""
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

    if not TOKEN or not CHAT_ID:
        logger.error("Telegram credentials not configured!")
        return False

    # Use beautiful format
    message = format_briefing(articles, prices)
    logger.info("📤 Sending to Telegram...")

    # Send with Markdown parse_mode
    if len(message) > 4000:
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for i, chunk in enumerate(chunks, 1):
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown", "disable_web_page_preview": True},
                timeout=30
            )
            if resp.status_code != 200:
                logger.error(f"Failed to send chunk {i}")
                return False
    else:
        resp = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=30
        )

    if resp.status_code == 200:
        logger.info(f"✓ Successfully sent {len(articles)} articles to Telegram!")
        return True
    else:
        logger.error(f"Failed to send: {resp.status_code}")
        return False


def main():
    print("=" * 60)
    print("🚀 Crypto News Briefing - GitHub Actions")
    print("=" * 60)
    print()

    # Check API key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        logger.warning("⚠️ DEEPSEEK_API_KEY not set, using raw titles")

    # Load config
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Step 1: Fetch BTC price
    logger.info("📊 Fetching BTC price...")
    prices = fetch_btc_price()
    if prices.get("price"):
        logger.info(f"   BTC: ${prices['price']:,.0f} ({prices['change_24h']:+.2f}%)")

    # Step 2: Fetch RSS
    logger.info("\n📥 Fetching RSS feeds...")
    fetcher = RSSFetcher(config)
    articles = fetcher.fetch_all()

    if not articles:
        logger.warning("No articles found!")
        return

    # Step 3: Send to Telegram
    print()
    logger.info("📋 Preview:")
    for i, a in enumerate(articles[:3], 1):
        logger.info(f"   {i}. {a['title_cn'][:40]}...")
    print()

    if send_to_telegram(articles, prices):
        print("=" * 60)
        print("✅ Done! Check Telegram for the briefing.")
        print("=" * 60)
    else:
        print("❌ Failed to send to Telegram")


if __name__ == "__main__":
    main()
