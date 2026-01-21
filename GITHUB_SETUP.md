# 🚀 GitHub Actions 部署指南

## 将加密货币新闻简报系统部署到 GitHub Actions，实现 24/7 自动运行！

---

## 📋 **步骤 1：创建 GitHub 仓库**

### 1.1 创建新仓库
1. 打开 https://github.com
2. 点击右上角 "+" → "New repository"
3. 仓库名称：`crypto-news-briefing`
4. 选择 **Public** 或 **Private**
5. **不要**勾选 "Add a README file"
6. 点击 "Create repository"

### 1.2 上传代码

在终端运行：

```bash
cd "/Users/lixiaonan/vibe coding/测试文件夹"

# 初始化 git
git init

# 添加所有文件（排除 .gitignore 中的文件）
git add .

# 提交
git commit -m "Add crypto news briefing system"

# 添加远程仓库（替换 YOUR_USERNAME 为你的用户名）
git remote add origin https://github.com/YOUR_USERNAME/crypto-news-briefing.git

# 推送到 GitHub
git push -u origin main
```

---

## 🔐 **步骤 2：配置 Secrets**

### 2.1 进入仓库设置
1. 打开你的 GitHub 仓库页面
2. 点击 "Settings" 标签
3. 点击左侧 "Secrets and variables" → "Actions"

### 2.2 添加 Secrets
点击 "New repository secret"，添加：

| Secret 名称 | 值 |
|-------------|-----|
| `TELEGRAM_BOT_TOKEN` | `7208100496:AAFfcfTLwvQNm-BaeJU0rt_47rNvYCDANqs` |
| `TELEGRAM_CHAT_ID` | `-1002701636404` |

**操作步骤：**
1. 点击 "New repository secret"
2. Name: `TELEGRAM_BOT_TOKEN`
3. Value: 粘贴你的 Bot Token
4. 点击 "Add secret"
5. 重复添加 `TELEGRAM_CHAT_ID`

---

## ✅ **步骤 3：测试运行**

### 3.1 手动触发
1. 在 GitHub 仓库页面
2. 点击 "Actions" 标签
3. 找到 "Crypto News Briefing" workflow
4. 点击 "Run workflow" → 选择 "main" 分支
5. 点击 "Run workflow"

### 3.2 查看运行状态
- 绿色 ✅ = 成功
- 红色 ❌ = 失败
- 点击查看日志

---

## ⏰ **步骤 4：自动运行**

配置完成后，系统会自动：

| 时间 | 操作 |
|------|------|
| 每 2 小时 | 自动抓取新闻并发送到 Telegram |
| UTC 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22 | 发送新闻简报 |

**北京时间**：8:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00, 次日 0:00, 2:00, 4:00, 6:00

---

## 🛠️ **步骤 5：修改配置**

### 5.1 修改新闻源
编辑 `config.yaml`：

```yaml
rss_sources:
  - name: CoinTelegraph
    url: https://cointelegraph.com/rss
    enabled: true
    priority: 2
    crypto_only: true
  
  - name: CoinDesk
    url: https://www.coindesk.com/arc/outboundfeeds/rss/
    enabled: true
    priority: 2
    crypto_only: true
```

### 5.2 修改发送频率
编辑 `.github/workflows/crypto-news.yml`：

```yaml
on:
  schedule:
    # 修改运行频率
    - cron: '0 */2 * * *'  # 每 2 小时
    # - cron: '0 */4 * * *'  # 每 4 小时
    # - cron: '0 8 * * *'    # 每天 8:00 UTC
```

修改后：
```bash
git add .
git commit -m "Update schedule"
git push
```

GitHub Actions 会自动运行！

---

## 📊 **监控运行**

### 查看运行历史
1. GitHub 仓库 → "Actions" 标签
2. 查看每次运行的：
   - 状态（成功/失败）
   - 运行时间
   - 日志

### 手动触发
1. GitHub 仓库 → "Actions" 标签
2. 选择 "Crypto News Briefing"
3. 点击 "Run workflow"

---

## 💡 **常见问题**

### Q: 推送代码后多久运行？
A: 立即自动运行（在 Actions 标签页可见）

### Q: 免费套餐够用吗？
A: 足够！GitHub Actions 每月提供 2000 分钟免费运行时间

### Q: 可以手动发送吗？
A: 可以！点击 "Run workflow" 手动触发

### Q: 失败会通知吗？
A: 默认不会，可配置 GitHub 通知（Settings → Notifications）

---

## 🎉 **完成！**

配置完成后，你的加密货币新闻简报系统将：
- ✅ 24/7 自动运行（无需电脑开机）
- ✅ 每 2 小时发送新闻到群组
- ✅ 完全免费
- ✅ 自动执行，无需人工干预

**立即开始：**
1. 创建 GitHub 仓库
2. 上传代码
3. 配置 Secrets
4. 完成！

---

## 📞 **获取帮助**

如果遇到问题：
1. 查看 Actions 标签页的运行日志
2. 常见错误：Secret 配置错误、网络问题
3. 检查 config.yaml 格式是否正确

**祝你部署顺利！** 🚀📱

