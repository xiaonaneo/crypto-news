"""
Article Summarizer Module
Uses AI to summarize articles (optional)
"""

import asyncio
import logging
import os
import re
import requests
from typing import List, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ArticleSummarizer:
    """Summarizes articles using AI"""
    
    def __init__(self, config: dict):
        self.config = config
        self.use_llm = config.get('use_llm', False)
        self.model = config.get('model', 'deepseek-chat')
        self.summary_length = config.get('summary_length', 100)
        self.detail_length = config.get('detail_length', 200)
    
    def fetch_article_content(self, url: str, source: str) -> str:
        """Fetch article content from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()
            
            # Try to find main content based on common selectors
            content = None
            selectors = [
                'article',
                '[role="main"]',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content-body',
                '.story-body',
                'main'
            ]
            
            for selector in selectors:
                content = soup.select_one(selector)
                if content and len(content.get_text(strip=True)) > 200:
                    break
            
            if not content:
                content = soup.find('body')
            
            if content:
                # Get text and clean it
                text = content.get_text(separator=' ', strip=True)
                # Remove extra whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                # Limit length
                return text[:3000] if len(text) > 3000 else text
            
            return ""
            
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return ""
    
    def summarize_articles(self, articles: List[Dict]) -> List[Dict]:
        """Summarize articles using DeepSeek if configured"""
        import asyncio
        
        use_deepseek = os.environ.get('DEEPSEEK_API_KEY')
        
        if not use_deepseek:
            logger.warning("DEEPSEEK_API_KEY not set")
            return articles
        
        logger.info(f"Using DeepSeek AI to summarize {len(articles)} articles...")
        try:
            articles = asyncio.run(self.summarize_with_deepseek(articles))
        except Exception as e:
            logger.error(f"DeepSeek summarization failed: {e}")
        
        return articles
    
    async def summarize_with_deepseek(self, articles: List[Dict]) -> List[Dict]:
        """Fetch article content and summarize using DeepSeek API"""
        try:
            from openai import OpenAI
            
            api_key = os.environ.get('DEEPSEEK_API_KEY')
            if not api_key:
                logger.warning("DEEPSEEK_API_KEY not set")
                return articles
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            
            for i, article in enumerate(articles):
                logger.info(f"Processing {i+1}/{len(articles)}: {article['title'][:40]}...")
                
                # 1. Fetch article content from URL
                content = self.fetch_article_content(article['url'], article.get('source', ''))
                
                # 2. Generate summary with DeepSeek
                if content:
                    prompt = f"""
请用中文完成以下任务：

1. 将标题翻译成简洁的中文（不超过25字）
2. 阅读文章内容，用不超过100个汉字总结文章要点（只保留与加密货币直接相关的内容）

标题：{article['title']}
来源：{article.get('source', '')}

文章内容：
{content[:2000]}

请用以下格式输出：
标题翻译：[中文标题]
摘要：[不超过100字的摘要]
"""
                else:
                    # Use title as summary if can't fetch content
                    prompt = f"""
请用中文完成以下任务：

1. 将标题翻译成简洁的中文（不超过25字）
2. 根据标题生成一个不超过100字的摘要

标题：{article['title']}
来源：{article.get('source', '')}

请用以下格式输出：
标题翻译：[中文标题]
摘要：[不超过100字的摘要]
"""
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300
                )
                
                result = response.choices[0].message.content.strip()
                
                # Parse the result
                title_cn = article['title']  # Default to original
                summary = article.get('summary', '')
                
                for line in result.split('\n'):
                    if line.startswith('标题翻译：'):
                        title_cn = line.replace('标题翻译：', '').strip()
                    elif line.startswith('摘要：'):
                        summary = line.replace('摘要：', '').strip()
                
                article['title_cn'] = title_cn
                article['summary'] = summary
                logger.debug(f"Summarized: {article['title'][:30]}...")
        
        except ImportError:
            logger.warning("openai package not installed")
        except Exception as e:
            logger.error(f"Error summarizing with DeepSeek: {e}")
        
        return articles


# Convenience function
def summarize_articles(articles: List[Dict], config: dict = None) -> List[Dict]:
    """Summarize articles (convenience function)"""
    summarizer = ArticleSummarizer(config or {})
    return summarizer.summarize_articles(articles)


if __name__ == "__main__":
    from datetime import datetime, timezone, timedelta
    
    BJ_TIMEZONE = timezone(timedelta(hours=8))
    
    test_articles = [
        {
            'title': 'Bitcoin reaches new all-time high above $69,000',
            'url': 'https://example.com/bitcoin-new-high',
            'source': 'Reuters',
            'published': datetime.now(BJ_TIMEZONE)
        }
    ]
    
    import yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    summarizer = ArticleSummarizer(config)
    summarized = summarizer.summarize_articles(test_articles)
    
    print("Summarized articles:\n")
    for i, article in enumerate(summarized, 1):
        print(f"{i}. {article['title']}")
        print(f"   Summary: {article.get('summary', 'N/A')}\n")
