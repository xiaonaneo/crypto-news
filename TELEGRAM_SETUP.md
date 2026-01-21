# 📱 Telegram Bot 手动设置指南

由于环境限制，请按照以下步骤手动配置：

## Step 1: 创建 Bot

1. **打开 Telegram**
2. **搜索并联系 @BotFather**（这是官方机器人创建工具）
3. **发送命令**：
   ```
   /newbot
   ```
4. **给 Bot 起名字**（例如）：`Crypto News Bot`
5. **给 Bot 起用户名**（必须以 `bot` 结尾，例如）：`crypto_news_lxn_bot`
6. **复制 BotFather 返回的 Token**（格式如：`123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`）

⚠️ **重要**：这个 token 非常敏感，不要分享给他人！

## Step 2: 获取你的 Chat ID

1. **搜索并联系 @userinfobot**
2. **发送命令**：`/start`
3. **它会回复你的用户 ID**（一串数字，例如）：`123456789`

这就是你的 `TELEGRAM_CHAT_ID`

## Step 3: 编辑配置文件

用文本编辑器打开 `.env` 文件：

```bash
# macOS:
open .env

# 或直接编辑：
nano .env
```

修改以下内容：

```env
# 将 your_bot_token_here 替换为你的 Bot Token
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# 将 your_chat_id_here 替换为你的 Chat ID
TELEGRAM_CHAT_ID=123456789
```

## Step 4: 验证配置

运行验证脚本：

```bash
python3 scripts/test_run.py
```

如果配置正确，它会显示找到的新闻，并询问是否发送到 Telegram。

## Step 5: 启动定时任务

```bash
python3 src/main.py once  # 单独运行一次测试
python3 src/main.py       # 启动定时调度（每2小时运行一次）
```

## 🔍 常见问题

### Q: 找不到 @BotFather？
A: 确保在 Telegram 应用内搜索，不是搜索引擎

### Q: Token 格式是什么样的？
A: 包含数字和字母，中间有冒号，例如：`123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

### Q: Chat ID 是负数？
A: 如果是在群里，Chat ID 会是负数（例如：`-123456789`），这是正常的

### Q: 收不到消息？
A: 检查：
   1. Bot Token 是否正确
   2. Chat ID 是否正确
   3. Bot 是否在聊天列表中
   4. 是否屏蔽了机器人

### Q: 如何给 Bot 添加头像？
A: 联系 @BotFather，发送 `/setuserpic` 然后选择你的 Bot

## 📞 测试 Bot

在浏览器中访问以下链接（将 `YOUR_TOKEN` 替换为你的 token）：

```
https://api.telegram.org/botYOUR_TOKEN/getMe
```

如果返回 JSON 数据包含 `"ok":true`，说明 Bot 配置正确。

## ✅ 配置完成检查清单

- [ ] Bot Token 已复制并保存
- [ ] Chat ID 已获取并保存
- [ ] `.env` 文件已正确编辑
- [ ] 运行 `python3 scripts/test_run.py` 测试通过
- [ ] 收到测试消息（如果选择了发送）

---

**设置完成后告诉我，我会帮你进行测试运行！**
