/**
 * Crypto News Bot - Cloudflare Worker
 * 每4小时抓取加密货币新闻并发送到 Telegram
 */

const RSS_SOURCES = [
  { name: "CoinTelegraph", url: "https://cointelegraph.com/rss", priority: 3 },
  { name: "CoinDesk", url: "https://www.coindesk.com/arc/outboundfeeds/rss/", priority: 3 },
  { name: "Bitcoin.com", url: "https://news.bitcoin.com/feed/", priority: 2 },
  { name: "Bitcoin Magazine", url: "https://bitcoinmagazine.com/feed", priority: 2 },
  { name: "CryptoPotato", url: "https://cryptopotato.com/feed/", priority: 2 },
  { name: "CryptoBriefing", url: "https://cryptobriefing.com/feed/", priority: 2 },
  { name: "The Daily Hodl", url: "https://dailyhodl.com/feed/", priority: 2 },
  { name: "Decrypt", url: "https://decrypt.co/feed", priority: 2 },
  { name: "CoinGecko Research", url: "https://coingecko.com/research.atom", priority: 2 },
  { name: "Messari", url: "https://messari.io/rss", priority: 2 },
  { name: "Benzinga Crypto", url: "https://feeds2.benzinga.com/markets/cryptocurrency", priority: 2 },
  { name: "Unchained", url: "https://unchainedpodcast.com/feed/", priority: 2 },
  { name: "深潮TechFlow", url: "https://techflowpost.substack.com/feed", priority: 2 },
  { name: "Odaily星球日报", url: "https://www.odaily.news/feed", priority: 2 },
  { name: "Yahoo Finance Crypto", url: "https://finance.yahoo.com/news/rssindex/tagged/cryptocurrency", priority: 2 },
  { name: "CryptoMoon", url: "https://cryptomoon.com/feed/", priority: 2 },
];

const CRYPTO_KEYWORDS = [
  "bitcoin", "btc", "eth", "ethereum", "crypto", "cryptocurrency",
  "binance", "coinbase", "ripple", "xrp", "solana", "sol",
  "cardano", "ada", "dogecoin", "doge", "polkadot", "dot",
  "chainlink", "link", "avalanche", "avax", "polygon", "matic",
  "uniswap", "aave", "defi", "nft", "web3", "blockchain",
  "etf", "sec", "cftc", "监管", "现货", "上市",
  "halving", "减半", "牛市", "bull", "崩盘", "crash"
];

const IMPORTANT_KEYWORDS = [
  "etf", "sec", "cftc", "监管", "批准", "通过", "拒绝",
  "halving", "减半", "bitcoin etf", "现货etf",
  "blackrock", "fidelity", "grayscale",
  "历史新高", "突破", "crash", "崩盘", "暴跌",
  "牛市", "bull", "all-time high", "ath"
];

// 过滤加密货币相关新闻
function isCryptoArticle(title, summary) {
  const text = `${title} ${summary}`.toLowerCase();
  return CRYPTO_KEYWORDS.some(kw => text.includes(kw.toLowerCase()));
}

// 计算重要性分数
function calculateImportance(article, sources) {
  let score = 0;
  const title = article.title.toLowerCase();
  const hoursOld = (Date.now() - article.published) / (1000 * 60 * 60);

  // 来源优先级 (25%)
  const source = sources.find(s => s.name === article.source);
  if (source) {
    score += (1.0 - (source.priority - 1) * 0.33) * 0.25;
  }

  // 时间衰减 (25%)
  score += Math.max(0, 1.0 - hoursOld / 12.0) * 0.25;

  // 突发新闻加成 (20%)
  if (hoursOld < 1) score += 1.0 * 0.20;
  else if (hoursOld < 2) score += 0.7 * 0.20;
  else if (hoursOld < 4) score += 0.4 * 0.20;

  // 重大关键词 (15%)
  const keywordCount = IMPORTANT_KEYWORDS.filter(kw => title.includes(kw.toLowerCase())).length;
  score += Math.min(keywordCount * 0.25, 1.0) * 0.15;

  // 多源验证 (15%) - 基于 URL 相似度
  const urlPattern = article.url.substring(0, 50);
  score += Math.min(article.sourceCount / 3.0, 1.0) * 0.15;

  return score;
}

// 解析 RSS
async function fetchRSS(source) {
  try {
    const response = await fetch(source.url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; CryptoNewsBot/1.0)" },
      signal: AbortSignal.timeout(15000)
    });

    if (!response.ok) return [];

    const text = await response.text();
    const articles = [];
    const itemRegex = /<item[^>]*>([\s\S]*?)<\/item>/gi;
    let match;

    while ((match = itemRegex.exec(text)) !== null) {
      const content = match[1];
      const titleMatch = content.match(/<title><!\[CDATA\[(.*?)\]\]><\/title>/i) || content.match(/<title>(.*?)<\/title>/i);
      const linkMatch = content.match(/<link>(.*?)<\/link>/i);
      const descMatch = content.match(/<description><!\[CDATA\[(.*?)\]\]><\/description>/i) || content.match(/<description>(.*?)<\/description>/i);
      const dateMatch = content.match(/<pubDate>(.*?)<\/pubDate>/i);

      if (titleMatch && linkMatch) {
        const title = titleMatch[1].trim();
        const summary = descMatch ? descMatch[1].replace(/<[^>]+>/g, "").substring(0, 300) : "";
        let published = dateMatch ? new Date(dateMatch[1]) : new Date();

        // 过滤并解析时间
        if (isCryptoArticle(title, summary)) {
          articles.push({
            title,
            url: linkMatch[1].trim(),
            summary,
            published: published.getTime(),
            source: source.name,
            priority: source.priority
          });
        }
      }
    }

    return articles;
  } catch (error) {
    console.error(`Error fetching ${source.name}:`, error.message);
    return [];
  }
}

// 发送消息到 Telegram
async function sendToTelegram(message) {
  const token = TELEGRAM_BOT_TOKEN;
  const chatId = TELEGRAM_CHAT_ID;

  if (!token || !chatId) {
    console.error("Missing Telegram credentials");
    return false;
  }

  try {
    const response = await fetch(
      `https://api.telegram.org/bot${token}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId,
          text: message,
          parse_mode: "HTML",
          disable_web_page_preview: false
        })
      }
    );

    const result = await response.json();
    if (!result.ok) {
      console.error("Telegram error:", result.description);
    }
    return result.ok;
  } catch (error) {
    console.error("Telegram request failed:", error.message);
    return false;
  }
}

// 格式化新闻消息
function formatNewsMessage(articles) {
  if (articles.length === 0) {
    return "📭 过去4小时内没有新的重要加密货币新闻。";
  }

  const now = new Date();
  const dateStr = now.toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" });
  const timeStr = now.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });

  let message = `📊 <b>加密货币新闻简报</b>\n`;
  message += `📅 ${dateStr} ${timeStr}\n`;
  message += `━━━━━━━━━━━━━━━━\n`;
  message += `📰 共 ${articles.length} 条重要新闻\n\n`;

  articles.forEach((article, index) => {
    const num = index + 1;
    const time = new Date(article.published).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    const priorityIcon = article.priority === 3 ? "🔴" : article.priority === 2 ? "🟡" : "🟢";

    message += `${priorityIcon} <b>${num}. ${article.title}</b>\n`;
    message += `   📎 ${article.source} | ${time}\n`;
    message += `   🔗 ${article.url}\n\n`;
  });

  message += `━━━━━━━━━━━━━━━━\n`;
  message += `🤖 自动推送 | 每4小时更新`;

  return message;
}

// 主函数
export default {
  async scheduled(controller, env, ctx) {
    console.log("🚀 开始抓取加密货币新闻...");

    // 并行抓取所有 RSS 源
    const allArticles = await Promise.all(RSS_SOURCES.map(fetchRSS));
    let articles = allArticles.flat();

    // 按时间过滤（过去4小时内）
    const fourHoursAgo = Date.now() - 4 * 60 * 60 * 1000;
    articles = articles.filter(a => a.published > fourHoursAgo);

    // 多源验证：统计相同 URL 模式
    const urlPatternCount = {};
    articles.forEach(a => {
      const pattern = a.url.substring(0, 60);
      urlPatternCount[pattern] = (urlPatternCount[pattern] || 0) + 1;
    });
    articles.forEach(a => {
      const pattern = a.url.substring(0, 60);
      a.sourceCount = urlPatternCount[pattern];
    });

    // 按重要性排序
    articles.sort((a, b) => calculateImportance(b, RSS_SOURCES) - calculateImportance(a, RSS_SOURCES));

    // 取前10条
    articles = articles.slice(0, 10);

    console.log(`📰 找到 ${articles.length} 条重要新闻`);

    // 发送到 Telegram
    const message = formatNewsMessage(articles);
    const success = await sendToTelegram(message);

    if (success) {
      console.log("✅ 消息已发送到 Telegram");
    } else {
      console.error("❌ 发送失败");
    }
  },

  async fetch(request, env, ctx) {
    return new Response("Crypto News Bot is running. Scheduled to run every 4 hours.", {
      headers: { "Content-Type": "text/plain" }
    });
  }
};
