# ⚡ Quick Start

## 3步开始使用

### Step 1: 一键安装依赖并配置
```bash
# 1. 安装 Python 依赖
pip install feedparser python-telegram-bot apscheduler requests beautifulsoup4 python-dotenv

# 2. 配置 Telegram Bot
python scripts/setup_telegram.py

# 3. 测试运行
python src/main.py once
```

### Step 4: 启动定时发送
```bash
# 启动后每2小时自动发送一次
python src/main.py
```

## 📋 系统要求

- ✅ Python 3.8+ (已检测到 3.13.0)
- ✅ pip 包管理器
- ✅ Telegram 账号
- 🌐 网络连接 (用于抓取 RSS 新闻)

## 🔧 手动安装 (如果 pip 失败)

```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 或逐个安装
pip install feedparser
pip install python-telegram-bot
pip install apscheduler
pip install requests
pip install beautifulsoup4
pip install python-dotenv
```

## 🚀 下一步操作

1. **安装依赖** (如果还没安装)
2. **运行设置向导**: `python scripts/setup_telegram.py`
3. **测试**: `python scripts/test_run.py`
4. **启动**: `python src/main.py`

## 📖 详细文档

- 完整指南: [README.md](README.md)
- 故障排除: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- 配置说明: 查看 `config.yaml`

## ❓ 获取帮助

```bash
# 查看帮助
python src/main.py help

# 查看日志
tail -f logs/briefing.log

# 手动运行一次
python src/main.py once
```

## 🎯 预期效果

运行后你将每2小时收到一次 Telegram 消息，包含：
- 📰 10条最新的加密货币新闻
- 🐦 来自顶级分析师的 Twitter 动态
- 📊 来源权威性排名
- 🔗 完整链接
