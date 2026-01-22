#!/usr/bin/env python3
"""
加密货币新闻简报 - GitHub Actions 版本
完整复刻本地运行流程
"""

import os, yaml, logging, ssl, urllib.request, feedparser, requests
from datetime import datetime, timedelta
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# SSL fix for RSS feeds with XML issues
_orig = urllib.request.urlopen
def _patch(url, *a, **k):
    try: 
        return _orig(url, *a, **k, context=ctx)
    except Exception:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return urllib.request.urlopen(req, timeout=30)
urllib.request.urlopen = _patch

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


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
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()

        content = None
        selectors = ['article', '[role="main"]', '.article-content', '.post-content',
                     '.entry-content', '.content-body', '.story-body', 'main', '.news-content']

        for selector in selectors:
            element = soup.select_one(selector)
            if element and len(element.get_text(strip=True)) > 200:
                content = element
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
    """使用 DeepSeek AI 翻译标题并生成摘要"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")

    if not api_key:
        logger.warning("⚠️ DEEPSEEK_API_KEY not set")
        return {"title_cn": clean_html(title), "summary": clean_html(summary)[:150]}

    try:
        content = fetch_article_content(url) if url else ""

        if content:
            prompt = f"""
请完成以下任务（仅输出翻译结果，不要其他内容）：

1. 将标题翻译成简洁中文（不超过20字）
2. 用不超过80字总结文章要点（只保留加密货币相关内容）

标题：{title}

文章内容摘要：{content[:1500]}

输出格式：
[翻译后的标题]
[摘要]
"""
        else:
            prompt = f"""
请完成以下任务（仅输出翻译结果，不要其他内容）：

1. 将标题翻译成简洁中文（不超过20字）
2. 根据摘要用不超过80字总结要点

标题：{title}
摘要：{summary[:500]}

输出格式：
[翻译后的标题]
[摘要]
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
                "max_tokens": 200,
                "temperature": 0.3
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("choices") and len(data["choices"]) > 0:
                result = data["choices"][0]["message"]["content"].strip()
                lines = [line.strip() for line in result.split('\n') if line.strip()]
                
                if len(lines) >= 2:
                    return {"title_cn": lines[0], "summary": lines[1]}
                elif len(lines) == 1:
                    return {"title_cn": lines[0], "summary": clean_html(summary)[:150]}

    except Exception as e:
        logger.debug(f"DeepSeek API error: {e}")

    return {"title_cn": clean_html(title), "summary": clean_html(summary)[:150]}


class RSSFetcher:
    """RSS Feed Fetcher - 修复 XML 解析问题"""
    def __init__(self, config: dict):
        self.config = config
        self.feeds = config.get("rss_sources", [])
        self.lookback_hours = config.get("processing", {}).get("hours_lookback", 12)

    def fetch_all(self) -> List[Dict]:
        articles = []
        cutoff_time = datetime.now() - timedelta(hours=self.lookback_hours)
        crypto_keywords = self.config.get("crypto_keywords", [])

        for feed in self.feeds:
            if not feed.get("enabled", True):
                continue

            url = feed.get("url", "")
            crypto_only = feed.get("crypto_only", False)
            zh_name = feed.get("zh_name", feed["name"])

            try:
                logger.info(f"📡 Fetching: {zh_name}")

                # Parse with SSL context fix
                feed_data = feedparser.parse(url)

                if feed_data.bozo and not feed_data.entries:
                    logger.warning(f"   ⚠️ XML parse error, trying fallback...")
                    # Try alternative: fetch raw content and parse
                    try:
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                            raw_data = resp.read()
                            feed_data = feedparser.parse(raw_data)
                    except Exception as e2:
                        logger.error(f"   ✗ Fallback failed: {str(e2)[:50]}")
                        continue

                count = 0
                for entry in feed_data.entries[:30]:
                    try:
                        pub_date = datetime.now()
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                            if pub_date < cutoff_time:
                                continue

                        title = entry.get("title", "") or ""
                        summary = entry.get("summary", entry.get("description", "")) or ""
                        url = entry.get("link", "") or ""

                        if not title:
                            continue

                        # Check crypto keywords for non-crypto-only feeds
                        if not crypto_only:
                            text = (title + " " + summary).lower()
                            if not any(kw.lower() in text for kw in crypto_keywords):
                                continue

                        # AI summarize (translate title + generate summary)
                        ai_result = summarize_with_deepseek(title, summary, url)

                        articles.append({
                            "title": title,
                            "title_cn": ai_result["title_cn"],
                            "summary": ai_result["summary"],
                            "source": feed["name"],
                            "source_zh": zh_name,
                            "url": url,
                            "published": pub_date
                        })
                        count += 1
                    except Exception as e:
                        continue

                logger.info(f"   ✓ Found {count} articles")

            except Exception as e:
                logger.error(f"   ✗ Error: {e}")
                continue

        articles.sort(key=lambda x: x["published"].timestamp(), reverse=True)
        max_articles = self.config.get("processing", {}).get("max_articles", 10)
        logger.info(f"📊 Total: {len(articles)} articles (max {max_articles})")
        return articles[:max_articles]


def fetch_btc_price() -> Dict:
    """Fetch BTC price"""
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
    """Format articles - 标题、摘要、来源、时间、链接"""
    if not articles:
        return "📰 *加密新闻简报*\n\n本周期未找到新文章。"

    lines = []

    lines.append("*加密新闻简报*")
    lines.append(datetime.now().strftime('%Y-%m-%d %H:%M'))
    lines.append("")

    # BTC price
    if prices and prices.get("price"):
        change = prices.get("change_24h", 0)
        change_str = f"{change:+.2f}%" if change else ""
        lines.append(f"*₿ ${prices['price']:,.0f} {change_str}*")
        lines.append("")

    # Articles
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
    """Send to Telegram"""
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
                json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown", "disable_web_page_preview": True},
                timeout=30
            )
            if resp.status_code != 200:
                logger.error(f"Failed chunk {i}: {resp.status_code}")
                return False
    else:
        resp = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=30
        )

    if resp.status_code == 200:
        logger.info(f"✓ Sent {len(articles)} articles to Telegram!")
        return True
    else:
        logger.error(f"Failed: {resp.status_code}")
        return False


def main():
    print("=" * 60)
    print("🚀 Crypto News Briefing - GitHub Actions")
    print("=" * 60)
    print()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        logger.warning("⚠️ DEEPSEEK_API_KEY not set")

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Step 1: BTC price
    logger.info("📊 Fetching BTC price...")
    prices = fetch_btc_price()
    if prices.get("price"):
        logger.info(f"   BTC: ${prices['price']:,.0f} ({prices['change_24h']:+.2f}%)")

    # Step 2: RSS feeds
    logger.info("\n📥 Fetching RSS feeds...")
    fetcher = RSSFetcher(config)
    articles = fetcher.fetch_all()

    if not articles:
        logger.warning("No articles found!")
        return

    # Preview
    print()
    logger.info("📋 Preview:")
    for i, a in enumerate(articles[:5], 1):
        logger.info(f"   {i}. {a['title_cn'][:40]}...")
    print()

    # Step 3: Send
    if send_to_telegram(articles, prices):
        print("=" * 60)
        print("✅ Done! Check Telegram.")
        print("=" * 60)
    else:
        print("❌ Failed")


if __name__ == "__main__":
    main()
