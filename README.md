# Polymarket Sentinel 🦅

每天自動從 Polymarket 挑選一個熱門話題深度分析，結合 Google News 最新動態，用繁體中文發送到 Telegram。

**核心理念：不每天推 10 個市場（容易重複無聊），改為每天深挖一個最值得關注的話題。**

---

## 架構

本專案使用 **n8n** 視覺化工作流 + **Google Sheets** 管理用戶，取代原有的 Python bot。

```
Polymarket API ──► 過濾運動/排序 ──► 加權隨機選一個話題
                                          │
                                    Google Search（最新新聞）
                                          │
                                     Groq AI 深度分析
                                          │
                              Telegram 發給所有訂閱者
```

---

## 三個 n8n Workflows

### Workflow A：每日排程（08:00）
1. 抓 Polymarket top 300 events
2. 過濾運動賽事、按 event_slug 分組、加總 volume
3. 取 top 20，再依到期日取 top 10
4. 讀 Google Sheets `sent_history`（近 14 天）→ 排除已發過的話題
5. **加權隨機選一個話題**（volume 越大被選中機率越高）
6. SerpAPI Google Search 抓最新新聞
7. Groq API（llama-3.3-70b）生成中文深度分析
8. 記錄到 `sent_history`，更新 `config` 的 `last_message`
9. 讀 `subscribers`，Loop → Telegram 發給所有人

### Workflow B：Telegram Bot（Webhook）
- `/start`：加入 `subscribers`，把最後一封訊息（`config.last_message`）轉發給新用戶
- `/stop`：設 `subscribers.active = FALSE`

### Workflow C：錯誤監控（選配）
- 任何 workflow 失敗時，Telegram 通知自己

---

## Google Sheets 結構

**試算表名稱：polymarket-sentinel**

### `subscribers` tab
| chat_id | subscribed_at | active | username |
|---|---|---|---|
| 123456789 | 2026-03-06T08:00:00Z | TRUE | @alice |

### `sent_history` tab
| sent_date | event_slug | event_title | total_volume | full_message | sent_at |
|---|---|---|---|---|---|
| 2026-03-06 | will-trump-x | Will Trump... | 5000000 | （完整訊息）| 2026-03-06T08:05:00Z |

### `config` tab
| key | value |
|---|---|
| last_message | （今天最新的完整訊息，每天更新） |
| last_sent_at | 2026-03-06T08:05:00Z |

---

## 設定步驟

### 1. n8n（已有 Docker）

需要對外 HTTPS URL 供 Telegram webhook 使用。用 **Cloudflare Tunnel**（免費）：

```bash
# 安裝 cloudflared（Windows）
# 下載 https://github.com/cloudflare/cloudflared/releases/latest

# 快速測試（URL 每次重啟會變）
cloudflared tunnel --url http://localhost:5678

# 穩定方案（需要 Cloudflare 帳號 + 域名）
cloudflared login
cloudflared tunnel create n8n-tunnel
cloudflared tunnel run n8n-tunnel
```

在 `docker-compose.yml` 加入：
```yaml
environment:
  - WEBHOOK_URL=https://your-tunnel-url
  - N8N_HOST=your-tunnel-url
```

### 2. 設定 Telegram Webhook（一次性）

```
GET https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-n8n-url/webhook/telegram-bot
```

> ⚠️ 設定後舊 Python bot 必須停止（同一個 Token 不能同時 polling + webhook）

### 3. n8n Credentials（在 n8n UI 的 Settings > Credentials 設定）

| 服務 | 類型 | 說明 |
|------|------|------|
| Groq | HTTP Header Auth | `Authorization: Bearer gsk_xxx` |
| Telegram | Telegram Bot API | Bot Token |
| Google Sheets | Google OAuth2 | 需要 OAuth 授權流程 |
| SerpAPI | HTTP Header Auth | API Key（免費 100次/月，夠用） |

### 4. 所需 API Keys

| 服務 | 取得方式 | 費用 |
|------|---------|------|
| Groq | [console.groq.com/keys](https://console.groq.com/keys) | 免費 |
| Telegram Bot | 向 `@BotFather` 發 `/newbot` | 免費 |
| SerpAPI | [serpapi.com](https://serpapi.com) | 免費 100次/月 |
| Google Sheets | Google Cloud Console > OAuth 2.0 | 免費 |

---

## 推播格式（Telegram）

```
今日深度聚焦：[中文話題標題]

市場怎麼說：...（賠率 + 24H 變化的含意）

新聞背景：...（最新新聞整理）

市場邏輯：...（新聞與賠率的關係）

值得關注：...（2 個關鍵指標或日期）

Polymarket: https://polymarket.com/event/[slug]
```

---

## Legacy

原有的 Python 實作（`main.py`, `summary_job.py` 等）已移至 [`legacy/`](./legacy/) 資料夾，僅供參考。
