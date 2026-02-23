# Polymarket Sentinel 🦅

Polymarket Sentinel 目前是一個基於 Python 開發的「預測市場熱榜推播機器人」。主要透過 Polymarket Gamma API 每兩小時 (或早晚 定時) 自動擷取全站資金流動量最大的時事話題，清除龐雜的運動賽事後，交由 LLM (Llama-3) 萃取子選項關鍵字並翻譯，最後格式化發送到使用者的 Telegram 頻道。

---

## 🛠 目前實作邏輯 (Current Implementation)

1. **深度資料抓取與過濾**
   - 透過 API 取得 Polymarket 全站前 `300` 筆 trending 事件，以確保能挖出深藏不露但交易量駭人的超級綜合選項 (如「GTA 6 發行前會發生啥事」)。
   - **體育過濾器**: 自動偵測 `seriesSlug` 與 `tags`，過濾掉所有附帶 `NBA`, `NFL`, `NHL`, `MLB`, `UFC`, `Soccer`, `Tennis` 等標籤的賽事，保留最核心的政治、經濟與娛樂話題。

2. **精準群組化與雙重排序 (Sorting & Grouping)**
   - 將同一個大事件 (`event_slug`) 旗下的所有子市場組合在一起，解決 API 預設回傳零散市場的問題。
   - **大盤排序**: 依據該事件底下的「總交易量 (Total Volume)」降冪排序，取出最熱門的前 20 大事件。
   - **時間排序**: 在這 20 大熱門中，再次依照「截止日期 (`end_date`)」由近到遠重新排序，精選出即將開獎的 Top 10 事件。
   - 事件整體的截止日期會自動取旗下所有子市場的最晚期限 (`max(sub_market ends)`)，避免日期錯亂。

3. **微觀子選項排序與 LLM 萃取**
   - 若為**單一是非題** (僅1個選項)：直接呈現。若是問日期，Prompt 會強制 LLM 把日期極度縮寫 (例如 `6/30 前`)，且跨年時必須標註 `明年 6/30 前`。
   - 若為**多選項競爭**：系統會依據目前市場上的「Yes 獲勝機率」由高至低重新排序，並僅擷取前 5 名。
   - LLM 負責將英文原問題提煉為最純粹的**核心關鍵字** (如: 人名、球隊、具體數字範圍)，避免冗長無聊的問句洗版。

4. **Telegram 限定的視覺化 UI**
   - 每篇標題提供【雙語對照】：`【事件 X】[流暢中文翻譯] (英文原標題)`。
   - 總交易量精簡為 `k / M` 格式展示 (如 `$6.8M`)。
   - **動態符號標記 ( Emoji UI )**:
     - 對於「單一是非題」：勝率 >= 50% 標註 🟢，勝率 < 50% 標註 🔴。
     - 對於「多選項競爭」：移除紅綠燈，改為在命中率最高的第一名選項開頭標註 👑 (皇冠)。
   - LLM 限定以一句話客觀解釋為何市場會開出這個機率，嚴禁廢話分析。

5. **自動化部署**
   - 透過內建的 `schedule` 套件，目前設定為每天早晨 `08:00` 與晚間 `20:00` 自動從背景產出報表並推播。

---

## 🚀 未來量化交易架構規劃 (Future Event-Driven Trading)

本專案將演進為一個 **「事件驅動型量化模擬交易系統 (Event-Driven Algorithmic Paper Trading System)」。**

### 1. 偵測與下單引擎 (The Hunter)
- **執行頻率**: `每 1 分鐘`
- **主要職責**: 尋找進場時機
  1. 擷取降息機率、大選等「特定目標市場」的即時機率。
  2. 爬取過去 1 分鐘內的最新重大新聞 (Twitter, RSS, News APIs)。
  3. LLM 瞬間判定該新聞是否翻轉市場預期，給出 BUY/SELL 建議。
  4. 若有強烈訊號，寫入 `SQLite` 產生一筆「虛擬訂單」，狀態設為 OPEN。

### 2. 結算清算引擎 (The Closer)
- **執行頻率**: `每 1 分鐘`
- **主要職責**: 持倉監控與收割
  1. 讀取 `SQLite` 中狀態為 `OPEN` 且滿足平倉條件（例如: 持倉滿 1 小時）的訂單。
  2. 取得該選項結算時的最新機率。
  3. 比較買入成本與現價，計算盈虧 (PnL)。
  4. 將狀態變更為 `CLOSED`，並發送獲利戰報至 Telegram 頻道。

---

## ⚡ 如何啟動 (Setup Guide)

此專案支援在 Windows 上無痛執行，並具有背景常駐功能。

### 1. 取得所需的 API Keys (完全免費)

這支程式依賴於免費的 AI 與 Telegram 推播服務：

**A. 取得 Groq API Key (免費強大的 Llama 3)**
1. 前往 [Groq Console](https://console.groq.com/keys) 並註冊帳號。
2. 點擊 `Create API Key`，隨便取個名字。
3. 將產生的金鑰複製下來。

**B. 取得 Telegram Bot Token**
1. 打開 Telegram，搜尋 `@BotFather` 並傳送訊息 `/newbot`。
2. 替你的機器人取個名字和 Username。
3. BotFather 會給你一串 Token（例如：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`），請複製下來。

**C. 取得 Telegram Chat ID**
1. 在 Telegram 搜尋剛剛創立的機器人 Username，點擊 Start 隨便傳個訊息給它。
2. 打開瀏覽器，前往：`https://api.telegram.org/bot<你的BotToken>/getUpdates`
   *(記得把 `<你的BotToken>` 換成你上一步拿到的字串)*
3. 在畫面顯示的 JSON 中找到 `"chat":{"id": 12345678,...}`，那串數字（如 `12345678`）就是你的 Chat ID。

### 2. 設定環境變數

1. 在專案資料夾中，複製 `.env.example` 檔案並重新命名為 `.env`。
2. 用任何文字編輯器（如記事本）打開 `.env`。
3. 將剛剛取得的三把鑰匙填入對應的位置：

```ini
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxx
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
TELEGRAM_CHAT_ID=12345678
```

### 3. 安裝與執行

#### 📍 初次安裝 (Windows)
在專案目錄下打開終端機 (PowerShell 或 Command Prompt)：

```bash
# 1. 建立並啟動虛擬環境 (強烈建議)
python -m venv .venv
.\.venv\Scripts\activate

# 2. 安裝必要的套件
pip install -r requirements.txt
```

#### 📍 日常啟動與背景執行
我們已經為 Windows 用戶準備了專屬的執行檔：

- **啟動機器人：** 直接在資料夾中「雙擊」 `start_background.bat`。
- **背景常駐：** 畫面上會跳出一個黑色的終端機視窗，只要你不關閉它，它就會每天早上 08:00 與晚上 20:00 自動為你推播最新市場動向。
- **查看狀態：** 所有的執行日誌與錯誤都會自動儲存到專案目錄下的 `polymarket.log` 檔案中，你可以隨時打開它查看機器人是否正常運作。
- **修改程式碼：** 如果你修改了 `.py` 檔案，你需要關掉原先的黑色視窗，再重新雙擊一次 `start_background.bat` 套用新設定。
