# AGENTS.md

This document provides guidelines for AI agents working in this codebase.

## Project Overview

Crypto News Briefing - A Python application that fetches crypto news from RSS feeds and sends formatted digests to Telegram.

## Build/Lint/Test Commands

### Running the Application

```bash
# Run once (fetch and send immediately)
python src/main.py once

# Run with scheduler (every 8 hours by default)
python src/main.py

# Test run without Telegram
python scripts/test_run.py
```

### Testing Individual Modules

```bash
# Test RSS fetcher
python modules/rss_fetcher.py
python modules/rss_fetcher_ssl.py

# Test news processor
python modules/news_processor.py

# Test Telegram bot formatting
python modules/telegram_bot.py

# Test summarizer
python modules/summarizer.py
```

### Python Version

```bash
python --version  # Must be 3.8+
```

### Installing Dependencies

```bash
pip install -r requirements.txt
```

### Linting (No formal config - follow existing patterns)

```bash
# Manual checks - no automated linting configured
# Ensure code follows patterns in this document
```

## Code Style Guidelines

### Imports

**Order**: Standard library → Third-party → Local application

```python
# Standard library
import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Third-party
import yaml
from telegram import Bot
from telegram.error import TelegramError

# Local application
from modules.rss_fetcher import RSSFetcher
from modules.telegram_bot import TelegramBriefingBot
```

**Never use wildcard imports**: `from module import *`

### Formatting

- **Indentation**: 4 spaces (no tabs)
- **Line length**: Soft limit 120 characters
- **Blank lines**: 
  - 2 blank lines between top-level definitions (classes, functions)
  - 1 blank line between method definitions in a class
  - Use blank lines sparingly within functions for logical sections
- **No trailing whitespace**

### Type Hints

**Use type hints for function signatures**:

```python
# Good
def fetch_feed(self, feed_info: dict) -> List[Dict]:
    ...

def calculate_ranking_score(self, article: Dict) -> float:
    ...

# Good - complex types
from typing import List, Dict, Optional, Any

def process_articles(
    self, 
    articles: List[Dict],
    config: Optional[dict] = None
) -> List[Dict]:
    ...
```

**Avoid `Any` when possible**. If type is unknown, document why.

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `CryptoNewsBriefing`, `RSSFetcher` |
| Functions/Variables | snake_case | `fetch_all`, `calculate_recency_score` |
| Constants | UPPER_SASE | `MAX_ARTICLES`, `DEFAULT_TIMEOUT` |
| Private Methods | snake_case with leading underscore | `_init_database`, `_setup_logging` |
| Module-level Variables | snake_case | `logger = logging.getLogger(__name__)` |

### Docstrings

**Use docstrings for all public classes and functions**:

```python
class NewsProcessor:
    """Processes and filters news articles"""
    
    def filter_and_process(self, articles: List[Dict]) -> List[Dict]:
        """Main processing pipeline
        
        Deduplicates, ranks, and limits articles before sending.
        
        Args:
            articles: List of article dictionaries from RSS fetcher
            
        Returns:
            Processed and ranked articles
        """
        ...
```

**For private methods**, use inline comments or brief docstrings:

```python
def _init_database(self):
    """Initialize SQLite database for deduplication"""
    ...
```

### Error Handling

**Use try/except with specific exceptions and logging**:

```python
# Good
try:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    logger.error(f"Config file not found: {config_path}")
    sys.exit(1)
except yaml.YAMLError as e:
    logger.error(f"Invalid YAML in config: {e}")
    raise

# Bad - bare except
try:
    something()
except:
    pass  # Never do this!
```

**Never suppress errors silently**. Log at minimum warning level.

**Use logging consistently**:

```python
# Module-level logger
logger = logging.getLogger(__name__)

# In methods
logger.info("Fetching RSS feed: {feed_info['name']}")
logger.debug(f"Found article: {title[:50]}...")
logger.warning(f"Malformed XML in {feed_info['name']}: {e}")
logger.error(f"Failed to send message after {attempts} attempts")
```

### Logging Pattern

Always use `logging.getLogger(__name__)` at module level:

```python
import logging

logger = logging.getLogger(__name__)
```

### Configuration Files

- Use `config.yaml` for runtime configuration
- Use `.env` for secrets (tokens, API keys)
- Never commit `.env` to version control
- Use `python-dotenv` for loading `.env`:

```python
from dotenv import load_dotenv
load_dotenv()

token = os.environ.get('TELEGRAM_BOT_TOKEN')
```

### File Paths

**Use `pathlib.Path`** for path operations:

```python
from pathlib import Path

project_root = Path(__file__).parent.parent
config_path = project_root / "config.yaml"
log_file = Path("logs") / "briefing.log"
log_dir.mkdir(parents=True, exist_ok=True)
```

**Add project root to `sys.path`** when needed:

```python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

### Database Operations

**Use context managers for SQLite**:

```python
conn = sqlite3.connect(self.db_path)
cursor = conn.cursor()

try:
    cursor.execute("SELECT ...")
    results = cursor.fetchall()
finally:
    conn.close()  # Or use 'with' if available
```

**Always close connections** - use `with` statement where possible.

### Async/Await

**Use `asyncio.run()` for synchronous wrappers**:

```python
def send_briefing_sync(self, articles: List[Dict]) -> bool:
    """Synchronous wrapper for send_briefing"""
    return asyncio.run(self.send_briefing(articles))
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Commit changes (run tests first)
git add .
git commit -m "Add: brief description of changes"

# Push
git push -u origin feature/your-feature
```

**Commit message format**: `Add:`, `Fix:`, `Update:`, `Remove:` prefix.

### Key File Locations

| File | Purpose |
|------|---------|
| `src/main.py` | Application entry point |
| `config.yaml` | Runtime configuration |
| `modules/rss_fetcher.py` | RSS feed fetching |
| `modules/rss_fetcher_ssl.py` | RSS fetcher with SSL workaround |
| `modules/news_processor.py` | Deduplication, ranking |
| `modules/telegram_bot.py` | Telegram message sending |
| `modules/summarizer.py` | AI summarization (optional) |
| `scripts/test_run.py` | Interactive test script |

### Quick Test Checklist

Before committing, verify:
- [ ] `python src/main.py once` runs without errors
- [ ] No `print()` statements (use `logger.info()` instead)
- [ ] No hardcoded paths (use `Path` or `config.yaml`)
- [ ] Type hints on new functions
- [ ] Docstrings on new public methods
- [ ] Error handling with logging
