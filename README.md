# 📰 Crypto News Briefing

Automated crypto currency news briefing that fetches from major English financial news sources and Twitter/X, then sends a formatted digest to Telegram every 2 hours.

## 🌟 Features

- 📡 **RSS Feed Integration**: Reuters, Bloomberg, Financial Times, Wall Street Journal, CNBC
- 🐦 **Twitter/X Monitoring**: Track top crypto analysts and influencers
- 🤖 **AI Summarization**: Optional Claude/GPT summarization (disabled by default)
- 📱 **Telegram Delivery**: Beautiful formatted messages with Markdown
- ⏰ **Scheduled Delivery**: Every 2 hours automatically
- 🔄 **Deduplication**: Smart article deduplication using SQLite
- 📊 **Smart Ranking**: Articles ranked by recency, source authority, and engagement

## 🚀 Quick Start

### 1. Create Telegram Bot

```bash
# Run the interactive setup script
python scripts/setup_telegram.py
```

Or manually:
1. Message @BotFather on Telegram
2. Send `/newbot` to create a new bot
3. Copy your API token
4. Message @userinfobot to get your Chat ID

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure

Edit `.env` with your Telegram credentials:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 4. Run

```bash
# Test run (fetches and sends once)
python src/main.py once

# Start scheduler (runs every 2 hours)
python src/main.py
```

## 📁 Project Structure

```
crypto_news_briefing/
├── src/
│   ├── __init__.py
│   └── main.py           # Main application entry point
├── modules/
│   ├── __init__.py
│   ├── rss_fetcher.py    # RSS feed fetching
│   ├── telegram_bot.py   # Telegram message sending
│   ├── news_processor.py # Deduplication & ranking
│   └── summarizer.py     # AI summarization (optional)
├── config.yaml           # Main configuration file
├── .env                  # Environment variables (create from .env.example)
├── requirements.txt      # Python dependencies
└── scripts/
    └── setup_telegram.py # Interactive Telegram setup
```

## ⚙️ Configuration

### config.yaml

Key settings you can customize:

```yaml
# RSS Feeds
rss_sources:
  - name: Reuters
    url: https://www.reuters.com/rssFeed/cryptocurrencyNews
    enabled: true
    priority: 1

# Crypto keywords for filtering
crypto_keywords:
  - bitcoin
  - ethereum
  - crypto
  - blockchain
  # Add more keywords...

# Scheduling
scheduler:
  interval_hours: 2  # Change frequency here
  timezone: UTC

# Processing
processing:
  max_articles: 15   # Articles to process
  deduplication: true
```

### .env

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional: Enable AI summarization
# ANTHROPIC_API_KEY=your_key
# LLM_MODEL=claude-sonnet-4-20250514
```

## 📊 Source Priority

Articles are weighted by source:
- **Priority 1**: Reuters, Bloomberg, WSJ, CNBC (highest trust)
- **Priority 2**: Financial Times

Higher priority = higher ranking in briefings.

## 🐦 Twitter/X Monitoring

To add Twitter monitoring, you'll need to:
1. Install the Agent Twitter Client MCP server
2. Configure your Twitter credentials in the MCP config
3. Add analyst handles to `config.yaml`

Currently, the focus is on RSS feeds from major financial news sources.

## 🔧 Troubleshooting

### "No module named..." errors
```bash
pip install -r requirements.txt
```

### Telegram not receiving messages
1. Check your `.env` file has correct credentials
2. Make sure your bot is in the chat/group
3. Test with: `python scripts/setup_telegram.py`

### No articles found
1. Check internet connection
2. Verify RSS feeds are accessible in browser
3. Check logs in `logs/briefing.log`

### Scheduler not running
```bash
# Make sure you're not using an old Python version
python --version  # Should be 3.8+
```

## 📝 Logs

Check `logs/briefing.log` for detailed execution logs:
```bash
tail -f logs/briefing.log
```

## 🔒 Security Notes

- Never commit `.env` to version control
- Keep your Telegram bot token secure
- Review the privacy policies of news sources you aggregate

## 🤝 Contributing

Areas for improvement:
- Add more RSS feeds
- Implement full Twitter/X integration via MCP
- Add more summarization options
- Support for other platforms (Slack, Discord, etc.)

## 📄 License

MIT License - feel free to use and modify!

---

Built with ❤️ for crypto enthusiasts
