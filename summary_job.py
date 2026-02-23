import sys
import os
import json
from polymarket_api import PolymarketAPI
from telegram_bot import TelegramNotifier
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime, timezone

def format_volume(volume: float) -> str:
    """將交易量格式化為附帶單位的短字串 (如 2.1B, 15.3M)"""
    if volume >= 1_000_000_000:
        return f"${volume / 1_000_000_000:.1f}B"
    elif volume >= 1_000_000:
        return f"${volume / 1_000_000:.1f}M"
    elif volume >= 1_000:
        return f"${volume / 1_000:.1f}K"
    return f"${volume:.0f}"

from typing import Optional

def get_llm_summary(markets_data: list) -> Optional[str]:
    """
    呼叫 Groq API (Llama 3 70B) 將 Polymarket 資料總結並加入背景常識。
    """
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("未設定 GROQ_API_KEY，跳過 LLM 摘要。")
        return None
        
    client = Groq(api_key=api_key)
    
    # 準備給 LLM 的 Prompt
    today_str = datetime.now().strftime('%Y/%m/%d')
    prompt = "你是一個專業的預測市場分析師與時事評論員。這是一份最近在 Polymarket 上熱門且高流動性的預測市場清單，已經按照「截止日期」由近到遠為你排序好了：\n\n"
    for i, ev in enumerate(markets_data, 1):
        vol_formatted = format_volume(ev['total_volume'])
        end_date = ev['end_date'][:10] if ev['end_date'] else "未知"
        prompt += f"【事件 {i}】\n標題：{ev['title']}\n💰 總交易量：{vol_formatted}\n⏳ 截止日期：{end_date}\n"
        
        prompt += "📈 子選項原文與數據：\n"
        # 為了避免過長，每個事件取交易量最大的前 5 個子市場
        top_sub = ev['sub_markets'][:5]
        for m in top_sub:
            odds_str = " | ".join(f"{o}: {p*100:.0f}% ({chg*100:+.0f}%)" for o, p, chg in zip(m['outcomes'], m['prices'], m['price_changes']))
            prompt += f"  - {m['question']} ➔ {odds_str}\n"
        prompt += "\n"
        
    prompt += f"""請根據上述資料，撰寫一篇給使用者的中文 Telegram 摘要推播。
請嚴格遵守以下格式規則：
1. **推播主標題**：你的完整回覆的「第一行」必須固定是「<b>今日 {today_str} Polymarket市場動向</b>」，不要加上任何自創的問候語，然後空一行。
2. **標題翻譯**：格式請用「<b>【事件 X】[中文翻譯]</b> <i>([英文原標題])</i>」。例如「<b>【事件 1】美國 2025 年關稅收入</b> <i>(How much revenue will the U.S. raise from tariffs in 2025?)</i>」
3. **保留基本數據**：下一行忠實呈現「💰 總交易量：... \n ⏳ 截止：...」。
4. **極致精煉子選項 (最重要的一點)**：請直接萃取核心關鍵字，並在機率的旁邊「務必括號附加上 24 小時的變化率」(例如: `Yes: 96% (-1%)`)。
   - 錯誤示範：「- Will the U.S. collect less than $100b in revenue in 2025? ➔ Yes: 96% | No: 4%」
   - 正確示範：「  - 低於 $100b ➔ Yes: 96% (+2%)」
   - 關於日期的縮寫同前。
   - 若為【單一是非題】，請在變化率旁加上紅綠燈。範例：「  - 6/30 前 ➔ Yes: 48% (-5%) 🔴」
   - 若為【多選項競爭】，機率最高者加上皇冠，並附帶變化率。範例：「  - 👑 One Battle After Another ➔ Yes: 74% (+12%)」
5. **杜絕廢話分析**：不用幫每一個事件擠出分析。排版務必緊湊適合 Telegram 閱讀。
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "你是一個專業、客觀且精通全球政經局勢的分析師。"
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"呼叫 Groq API 失敗: {e}")
        return None

def generate_summary_text() -> str:
    """擷取並產生最新 Polymarket 短評字串，不負責發送推播。"""
    api = PolymarketAPI()
    events = api.get_active_events(limit=300) # 提昇 limit 抓到足夠深度的巨頭資料
    
    # 過濾體育賽事
    SPORTS_SLUGS = {'nfl', 'nba', 'nhl', 'mlb', 'ufc', 'soccer', 'tennis', 'march-madness', 'sports', 'golf', 'f1', 'premier-league', 'champions-league', 'cricket', 'rugby'}
    filtered_events = []
    for ev in events:
        slug = ev.get('seriesSlug', '').lower()
        if slug in SPORTS_SLUGS:
            continue
            
        is_sport = False
        for t in ev.get('tags', []):
            label = t.get('label', '').lower() if isinstance(t, dict) else str(t).lower()
            if any(s in label for s in ['sport', 'nba', 'nfl', 'nhl', 'mlb', 'ufc', 'soccer', 'football', 'basketball', 'baseball', 'tennis']):
                is_sport = True
                break
                
        if not is_sport:
            filtered_events.append(ev)
            
    markets = api.extract_markets_from_events(filtered_events)
    
    # 整理資料：改以 Event 為單位群組
    events_map = {}
    current_utc_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    for m in markets:
        event_slug = m.get('event_slug')
        if not event_slug: continue
        
        # volume 處理
        try:
            vol = float(m.get('volumeNum', m.get('volume', 0)) or 0)
        except:
            vol = 0.0
            
        outcomes_raw = m.get('outcomes', "[]")
        prices_raw = m.get('outcomePrices', "[]")
        price_change = m.get('oneDayPriceChange', 0.0) 
        
        if isinstance(outcomes_raw, str) and outcomes_raw.startswith('['):
            try: outcomes = json.loads(outcomes_raw)
            except: outcomes = []
        else: outcomes = outcomes_raw
            
        if isinstance(prices_raw, str) and prices_raw.startswith('['):
            try: prices = json.loads(prices_raw)
            except: prices = []
        else: prices = prices_raw
            
        if not outcomes or not prices or len(outcomes) != len(prices):
            continue
            
        prices_float = []
        for p in prices:
            try: prices_float.append(float(p))
            except: prices_float.append(0.0)
                
        try: chg_val = float(price_change) if price_change else 0.0
        except: chg_val = 0.0
            
        changes_float = []
        if len(outcomes) == 2:
            changes_float = [chg_val, -chg_val]
        else:
            changes_float = [chg_val] + [0.0] * (len(outcomes)-1)
            
        # 排除完全 100% 或 0% 的已經結束市場，但不排除低機率 (多選項賽事中機率可能極低)
        if any(p >= 0.999 or p <= 0.001 for p in prices_float):
            continue
            
        end_date = m.get('endDate', '')
        # 如果沒有截止日期，或是截止日期已經過了 (過期)，就不處理
        if not end_date or end_date < current_utc_iso:
            continue
            
        sub_market = {
            "question": m.get('question', ''),
            "volume": vol,
            "outcomes": outcomes,
            "prices": prices_float,
            "price_changes": changes_float
        }
        
        if event_slug not in events_map:
            events_map[event_slug] = {
                "title": m.get('event_title', 'Unknown Event'),
                "end_date": end_date,
                "total_volume": 0.0,
                "sub_markets": []
            }
        else:
            if end_date > events_map[event_slug]["end_date"]:
                events_map[event_slug]["end_date"] = end_date
                
        events_map[event_slug]["sub_markets"].append(sub_market)
        events_map[event_slug]["total_volume"] += vol

    # 轉為 list 並過濾出沒有活躍子市場的 Event
    processed_events = [ev for ev in events_map.values() if ev["sub_markets"]]

    # 先照 Event 的 Total Volume 取出前 20 大熱門事件
    processed_events.sort(key=lambda x: x['total_volume'], reverse=True)
    top_volume_events = processed_events[:20]
    
    # 從這20個高流動性中，按照 End Date (截止時間由近到遠) 重新排序，選出前 10
    top_volume_events.sort(key=lambda x: x['end_date'])
    top_events = top_volume_events[:10]
    
    # 對於多選項賽事，我們改成依據 Yes 機率排序，並擷取前 5 名；若只有單一選項，維持原樣
    for ev in top_events:
        if len(ev['sub_markets']) > 1:
            ev['sub_markets'].sort(key=lambda x: x['prices'][0] if x['prices'] else 0, reverse=True)
            ev['sub_markets'] = ev['sub_markets'][:5]
    
    print("嘗試使用 Groq Llama 3 70B 產生摘要...")
    llm_msg = get_llm_summary(top_events)
    # llm_msg = None
    
    if llm_msg:
        final_msg = llm_msg
    else:
        # 開發測試用純文字版 (不經過 LLM)
        today_str = datetime.now().strftime('%Y/%m/%d')
        final_msg = f"📊 <b>今日 {today_str} Polymarket市場動向 (純資料檢視)</b>\n\n"
        for i, ev in enumerate(top_events, 1):
            vol_formatted = format_volume(ev['total_volume'])
            end_date = ev['end_date'][:10] if ev['end_date'] else "未知"
            final_msg += f"<b>【事件 {i}】{ev['title']}</b>\n"
            final_msg += f"💰 總交易量: {vol_formatted} | ⏳ 截止: {end_date}\n"
            
            top_sub = ev['sub_markets'][:5]
            for m in top_sub:
                odds_str = " | ".join(f"{o}: {p*100:.1f}% ({chg*100:+.1f}%)" for o, p, chg in zip(m['outcomes'], m['prices'], m['price_changes']))
                final_msg += f"  - {m['question']}: {odds_str}\n"
            final_msg += "\n"
            
    return final_msg

def run_summary():
    final_msg = generate_summary_text()
    
    # 發送給機器人
    notifier = TelegramNotifier()
    if notifier.is_configured():
        notifier.send_message(final_msg)
        print("Telegram 訊息已發送。")
    else:
        print("尚未設定 Telegram Token，印出本機範例：")
        print(final_msg)

if __name__ == "__main__":
    run_summary()
