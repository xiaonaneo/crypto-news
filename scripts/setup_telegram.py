#!/usr/bin/env python3
"""
Telegram Bot Setup Script
Helps you create and configure a Telegram bot for the news briefing
"""

import os
import sys


def print_step(step_num: int, title: str, content: str):
    """Print a setup step"""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {title}")
    print('='*60)
    print(content)
    print()


def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║     Crypto News Briefing - Telegram Bot Setup                 ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Create Bot
    print_step(1, "Create Your Telegram Bot", """
1. Open Telegram and search for @BotFather
2. Start a chat and send /newbot
3. Choose a name for your bot (e.g., "Crypto News Bot")
4. Choose a username (must end with 'bot', e.g., "crypto_news_bot")
5. BotFather will give you an API Token - COPY IT!
   Example: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

⚠️  IMPORTANT: Save this token securely!
    """)
    
    input("Press Enter when you've created your bot and have the token...")
    
    # Step 2: Get Chat ID
    print_step(2, "Get Your Chat ID", """
1. Search for @userinfobot on Telegram
2. Start a chat and send /start
3. It will reply with your User ID (a number like 123456789)
4. This is your CHAT_ID

Alternatively, for groups:
1. Add your bot to the group
2. Send a message in the group
3. Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
4. Look for "chat":{"id":-123456789,...} in the response
    """)
    
    input("Press Enter when you have your Chat ID...")
    
    # Step 3: Configure Bot
    print_step(3, "Configure Your Bot", """
Let's set up your bot configuration:
    """)
    
    # Get user input
    bot_token = input("Paste your Bot Token: ").strip()
    chat_id = input("Paste your Chat ID: ").strip()
    
    if not bot_token or not chat_id:
        print("\n❌ Error: Token and Chat ID are required!")
        sys.exit(1)
    
    # Validate format
    if ':' not in bot_token:
        print("\n⚠️  Warning: Token format looks incorrect (should contain ':')")
    
    # Create .env file
    print("\nCreating .env file...")
    
    env_content = f"""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN={bot_token}
TELEGRAM_CHAT_ID={chat_id}

# AI Summarization (optional - comment out if not using)
# ANTHROPIC_API_KEY=your_anthropic_api_key
# OPENAI_API_KEY=your_openai_api_key
# LLM_MODEL=claude-sonnet-4-20250514

# App Configuration
CRYPTO_KEYWORDS=bitcoin,ethereum,crypto,cryptocurrency,blockchain,btc,eth,solana,binance,coinbase
ANALYST_HANDLES=vitalikbuterin,balajis,cz_binance,elonmusk
RSS_HOURS_LOOKBACK=2
MAX_ARTICLES=15
SUMMARY_LENGTH=100
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✓ Created .env file")
    
    # Step 4: Test Bot
    print_step(4, "Test Your Bot", """
Testing your bot configuration...
    """)
    
    # Simple test
    import subprocess
    
    try:
        result = subprocess.run(
            ['curl', f'https://api.telegram.org/bot{bot_token}/getMe'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            if data.get('ok'):
                bot_name = data['result']['username']
                print(f"✓ Bot verified: @{bot_name}")
                print("\n🎉 Setup complete!")
            else:
                print(f"✗ Bot verification failed: {data.get('description')}")
        else:
            print(f"✗ Failed to connect to Telegram: {result.stderr}")
    
    except Exception as e:
        print(f"⚠️  Could not verify bot: {e}")
        print("Don't worry, you can test it when you run the main app.")
    
    # Final instructions
    print_step(5, "Next Steps", """
1. ✅ You've configured your Telegram bot
2. 📦 Install dependencies:
   pip install -r requirements.txt

3. ▶️ Run the news briefing:
   python src/main.py once   # Test run
   python src/main.py        # Start scheduler (runs every 2 hours)

4. 📖 For more options:
   python src/main.py help

📁 Your configuration is saved in:
   - .env (environment variables)
   - config.yaml (detailed configuration)
    """)
    
    print("🚀 Happy crypto news reading!")


if __name__ == "__main__":
    main()
