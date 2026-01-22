#!/usr/bin/env python3
"""
加密货币新闻简报 - DeepSeek AI 版
- 使用 DeepSeek API 进行 AI 总结
- 每8小时推送10条
"""

import os, yaml, logging, ssl, urllib.request, feedparser, requests
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

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

def summarize_with_deepseek(title, summary):
    """使用 DeepSeek AI 总结新闻"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    
    if not api_key:
        # 如果没有 API key，使用简单翻译
        return clean_html(title)
    
    try:
        # 清理内容
        title_clean = clean_html(title)
        summary_clean = clean_html(summary)
        
        # 构建 prompt
        prompt = f"""请用一句话总结以下加密货币新闻标题，保持专业性和信息完整性：

标题：{title_clean}
摘要：{summary_clean}

一句话总结："""
        
        # 调用 DeepSeek API
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 100,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("choices") and len(data["choices"]) > 0:
                result = data["choices"][0]["message"]["content"].strip()
                # 清理结果
                result = clean_html(result)
                # 如果结果太短或为空，使用原文
                if len(result) < 5:
                    return title_clean
                return result
        
    except Exception as e:
        logger.debug(f"DeepSeek API 错误: {e}")
    
    # 降级使用原文
    return title_clean

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
                        
                        # 检查是否加密货币相关新闻
                        if not crypto_only:
                            text = (title + " " + summary).lower()
                            if not any(kw.lower() in text for kw in crypto_keywords):
                                continue
                        
                        # 使用 DeepSeek AI 总结
                        summary_ai = summarize_with_deepseek(title, summary)
                        
                        articles.append({
                            "title": title,
                            "summary": summary_ai,
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

def format_briefing(articles, prices=None):
    """Format articles into a beautiful briefing (matching local format)"""
    if not articles:
        return "📰 *加密新闻简报*\n\n本周期未找到新文章。"

    lines = []

    # Header with prices
    lines.append("*加密新闻简报*")
    lines.append(datetime.now().strftime('%Y-%m-%d %H:%M'))
    lines.append("")

    # Add market prices if available
    if prices and prices.get('btc'):
        btc = prices['btc']
        change = btc.get('change_24h', 0)
        change_str = f"{change:+.2f}%" if change else ""
        lines.append(f"*₿ ${btc['price']:,.0f} {change_str}*")
        lines.append("")

    # Articles
    for i, article in enumerate(articles[:10], 1):
        title = article.get('title_cn', article.get('title', ''))
        summary = article.get('summary', '')
        source = article.get('source_zh', article.get('source', ''))
        url = article.get('url', '')

        lines.append(f"*{i} {title}*")
        lines.append(f"{summary}")
        if url:
            lines.append(f"[{source}]({url})")
        else:
            lines.append(f"_{source}_")
        lines.append("")

    return "\n".join(lines)


def send_to_telegram(articles, prices=None):
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

    if not TOKEN or not CHAT_ID:
        logger.error("未找到Telegram配置！")
        return False

    # Use beautiful formatting
    message = format_briefing(articles, prices)

    logger.info("发送到Telegram...")

    if len(message) > 4000:
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for i, chunk in enumerate(chunks, 1):
            resp = requests.post(
                "https://api.telegram.org/bot" + TOKEN + "/sendMessage",
                json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown", "disable_web_page_preview": True},
                timeout=30
            )
            if resp.status_code != 200:
                logger.error("发送第" + str(i) + "部分失败")
                return False
    else:
        resp = requests.post(
            "https://api.telegram.org/bot" + TOKEN + "/sendMessage",
            json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=30
        )

    if resp.status_code == 200:
        logger.info("成功发送到Telegram！")
        return True
    else:
        logger.error("发送失败: " + str(resp.status_code))
        return False

def main():
    print("=" * 70)
    print("加密货币新闻简报系统 - DeepSeek AI 版")
    print("=" * 70)
    print()
    
    # 检查 API Key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        logger.warning("未找到 DeepSeek API Key，将使用原始标题")
        logger.info("请在 GitHub Secrets 中添加 DEEPSEEK_API_KEY")
    
    logger.info("正在抓取并使用 AI 总结加密货币新闻...")
    fetcher = CryptoNewsFetcher()
    articles = fetcher.fetch_all()
    print()
    
    if not articles:
        logger.warning("未找到相关新闻")
        return
    
    logger.info("新闻预览:")
    for i, a in enumerate(articles[:5], 1):
        logger.info("   " + str(i) + ". " + a['summary'][:50] + "...")
    print()
    
    if send_to_telegram(articles):
        print("=" * 70)
        print("完成！请检查Telegram群组获取AI总结的新闻简报！")
        print("=" * 70)
    else:
        print("发送失败")

if __name__ == "__main__":
    main()
