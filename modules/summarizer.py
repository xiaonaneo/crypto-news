"""
Article Summarizer Module
Uses AI to summarize articles (optional)
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class ArticleSummarizer:
    """Summarizes articles using AI"""
    
    def __init__(self, config: dict):
        self.config = config
        self.use_llm = config.get('use_llm', False)
        self.model = config.get('model', 'claude-sonnet-4-20250514')
        self.length_limit = config.get('length_limit', 100)
    
    def summarize_articles(self, articles: List[Dict]) -> List[Dict]:
        """Summarize articles (placeholder - implement with your LLM)"""
        for article in articles:
            # If article already has a good summary, keep it
            if article.get('summary') and len(article['summary']) > 20:
                # Truncate to limit
                article['summary'] = article['summary'][:self.length_limit] + "..."
                continue
            
            # Placeholder: use title as summary
            article['summary'] = article['title'][:self.length_limit] + "..."
        
        return articles
    
    async def summarize_with_claude(self, articles: List[Dict]) -> List[Dict]:
        """Summarize using Claude API (example implementation)"""
        try:
            import anthropic
            client = anthropic.Anthropic()
            
            for article in articles:
                if len(article.get('summary', '')) > 50:
                    continue  # Already has good summary
                
                prompt = f"""
Summarize this news article in exactly 2-3 sentences (under 100 characters total):

Title: {article['title']}
Content: {article.get('summary', article['title'])}

Summary:
"""
                
                message = client.messages.create(
                    model=self.model,
                    max_tokens=100,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                article['summary'] = message.content[0].text.strip()
                logger.debug(f"Summarized: {article['title'][:30]}...")
        
        except ImportError:
            logger.warning("anthropic package not installed, using default summarization")
        except Exception as e:
            logger.error(f"Error summarizing with Claude: {e}")
        
        return articles
    
    async def summarize_with_openai(self, articles: List[Dict]) -> List[Dict]:
        """Summarize using OpenAI API (example implementation)"""
        try:
            from openai import OpenAI
            client = OpenAI()
            
            for article in articles:
                if len(article.get('summary', '')) > 50:
                    continue
                
                prompt = f"""
Summarize this news article in exactly 2-3 sentences (under 100 characters total):

Title: {article['title']}
Content: {article.get('summary', article['title'])}

Summary:
"""
                
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100
                )
                
                article['summary'] = response.choices[0].message.content.strip()
                logger.debug(f"Summarized: {article['title'][:30]}...")
        
        except ImportError:
            logger.warning("openai package not installed, using default summarization")
        except Exception as e:
            logger.error(f"Error summarizing with OpenAI: {e}")
        
        return articles


# Convenience function
def summarize_articles(articles: List[Dict], config: dict = None) -> List[Dict]:
    """Summarize articles (convenience function)"""
    summarizer = ArticleSummarizer(config or {})
    return summarizer.summarize_articles(articles)


if __name__ == "__main__":
    # Test the summarizer
    from datetime import datetime
    
    test_articles = [
        {
            'title': 'Bitcoin reaches new all-time high above $69,000',
            'summary': 'Bitcoin surged to a new record high of $69,044 on Tuesday, driven by increasing institutional adoption and growing mainstream acceptance. The breakthrough came after several major financial institutions announced plans to offer cryptocurrency investment products to their clients.',
            'published': datetime.now(),
            'source': 'Reuters'
        },
        {
            'title': 'Ethereum developers delay major network upgrade',
            'summary': '',  # Empty summary - should be filled
            'published': datetime.now(),
            'source': 'Bloomberg'
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
        print(f"   Summary: {article['summary']}\n")
