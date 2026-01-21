# 🚀 Quick Setup Guide

## 5分钟快速开始

Follow these steps to get your crypto news briefing running:

### Step 1: 安装依赖

```bash
# Create Python virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: 配置 Telegram Bot

运行交互式设置脚本：
```bash
python scripts/setup_telegram.py
```

Or manually:
1. 搜索 `@BotFather` on Telegram
2. 发送 `/newbot` 创建新 bot
3. 复制 API Token
4. 搜索 `@userinfobot` 获取你的 Chat ID
5. 编辑 `.env` 文件，填入 token 和 chat_id

### Step 3: 测试运行

```bash
# Test without scheduling
python scripts/test_run.py

# Or test with sending to Telegram
python src/main.py once
```

### Step 4: 启动定时任务

```bash
# Start the scheduler (runs every 2 hours)
python src/main.py
```

## 📋 所需环境

- **Python**: 3.8+ (已安装 3.13.0 ✓)
- **依赖**: 
  - feedparser
  - python-telegram-bot
  - apscheduler
  - requests
  - beautifulsoup4
  - python-dotenv

## 🔧 如果 pip 安装失败

由于网络限制，如果 pip install 失败：

### 方法 1: 使用镜像源
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 方法 2: 手动安装关键包
```bash
pip install feedparser python-telegram-bot apscheduler requests beautifulsoup4 python-dotenv
```

### 方法 3: 使用 conda
```bash
conda create -n crypto_news python=3.11
conda activate crypto_news
pip install -r requirements.txt
```

## 🐛 常见问题

### Q: 提示 "ModuleNotFoundError"
A: 确保已激活虚拟环境，并运行 `pip install -r requirements.txt`

### Q: Telegram 收不到消息
A: 
1. 检查 `.env` 文件中的 token 和 chat_id 是否正确
2. 确保 bot 在你的聊天列表中
3. 运行 `python scripts/setup_telegram.py` 重新验证

### Q: 没有找到文章
A: 
1. 检查网络连接
2. 验证 RSS 链接是否可访问
3. 查看 `logs/briefing.log` 获取详细错误

### Q: 如何停止程序
A: 按 `Ctrl+C` 停止调度器

## 📁 文件说明

```
.
├── src/main.py           # 主程序入口
├── config.yaml           # 配置文件
├── .env                  # 环境变量 (敏感信息)
├── requirements.txt      # Python 依赖
├── scripts/
│   ├── setup_telegram.py # Telegram 设置向导
│   └── test_run.py       # 测试脚本
├── modules/
│   ├── rss_fetcher.py    # RSS 抓取
│   ├── telegram_bot.py   # Telegram 发送
│   ├── news_processor.py # 文章处理
│   └── summarizer.py     # 摘要生成
└── logs/                 # 日志目录
```

## ⚙️ 自定义配置

### 修改新闻源
编辑 `config.yaml` 中的 `rss_sources` 部分

### 修改关键词
编辑 `config.yaml` 中的 `crypto_keywords` 部分

### 修改发送频率
编辑 `config.yaml` 中的 `scheduler.interval_hours`

### 修改文章数量
编辑 `config.yaml` 中的 `processing.max_articles`

## 🎯 下一步

1. ✅ 运行测试: `python scripts/test_run.py`
2. 📱 配置 Telegram
3. ▶️ 启动调度器: `python src/main.py`
4. 📖 阅读 README.md 了解更多

## 💡 提示

- 使用 `python src/main.py once` 进行单次测试
- 查看日志: `tail -f logs/briefing.log`
- 修改配置后重启程序
- 定期清理旧文章: 程序会自动清理7天前的数据

需要帮助？查看详细文档：README.md
