#!/bin/bash
cd "$(dirname "$0")"

echo "🚀 Starting Crypto News Briefing Scheduler..."
echo "📡 This will automatically send news to your Telegram every 2 hours"
echo ""
echo "⏹️  To stop: Press Ctrl+C"
echo ""

python3 src/main.py
