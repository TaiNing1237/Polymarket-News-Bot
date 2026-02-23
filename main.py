import logging
import time
import schedule
import threading
import os
from dotenv import load_dotenv
from summary_job import run_summary, generate_summary_text
from telegram_bot import add_subscriber, remove_subscriber

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure standard logging to output to console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("polymarket.log", encoding="utf-8")
    ]
)

# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def job():
    logger.info("Starting Polymarket Summary scan cycle...")
    try:
        run_summary()
    except Exception as e:
        logger.error(f"Error during summary scan cycle: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if add_subscriber(chat_id):
        welcome_msg = (
            "✅ <b>歡迎使用 Polymarket 動向機器人！</b>\n\n"
            "這個機器人會為您追蹤 Polymarket 預測市場上最熱門、流動性最高的話題，並在每天的 <b>早上 08:00</b> 與 <b>晚上 20:00</b> 自動為您發送最新的市場重點摘要，以及前 24 小時內的機率趨勢變化。\n\n"
            "若未來想取消訂閱，請隨時輸入 /stop\n\n"
            "正在為您整理最新市場動向，請稍候..."
        )
        await update.message.reply_text(welcome_msg, parse_mode="HTML")
        logger.info(f"New user subscribed: {chat_id}. Generating immediate summary...")
        
        try:
            summary_text = generate_summary_text()
            await update.message.reply_text(summary_text, parse_mode="HTML", disable_web_page_preview=True)
            logger.info(f"Immediate summary sent to {chat_id}.")
        except Exception as e:
            logger.error(f"Error generating immediate summary for {chat_id}: {e}")
            await update.message.reply_text("⚠️ 產生摘要時發生錯誤，您將在下次自動更新時收到正常推播。")
            
    else:
        already_msg = (
            "您已經在訂閱名單中了！\n"
            "機器人將在每天的 08:00 與 20:00 發送最新動向。\n"
            "若想取消訂閱，請輸入 /stop"
        )
        await update.message.reply_text(already_msg, parse_mode="HTML")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if remove_subscriber(chat_id):
        await update.message.reply_text("⛔️ <b>已取消訂閱</b>\n您將不再收到 Polymarket 的定時動向推播。未來若想重新開啟，隨時可以輸入 /start 再次訂閱！", parse_mode="HTML")
        logger.info(f"User unsubscribed: {chat_id}")
    else:
        await update.message.reply_text("您目前不在訂閱名單中喔！", parse_mode="HTML")

def run_schedule():
    """執行排程的背景執行緒函數"""
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    logger.info("=== Polymarket Summary Tracker Started ===")
    
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Schedule to run every day at 08:00 and 20:00
    schedule.every().day.at("08:00").do(job)
    schedule.every().day.at("20:00").do(job)
    logger.info("Scheduler configured. Will scan and send summary every day at 08:00 and 20:00. Press Ctrl+C to exit.")
    
    # Start schedule loop in background
    t = threading.Thread(target=run_schedule, daemon=True)
    t.start()
    
    # Run once immediately on startup in a separate thread so it doesn't delay bot polling startup
    threading.Thread(target=job, daemon=True).start()

    if bot_token and bot_token != "your_bot_token_here":
        logger.info("Starting Telegram Bot Polling...")
        application = Application.builder().token(bot_token).build()
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("stop", stop_command))
        
        # Run polling (this blocks the main thread)
        application.run_polling()
    else:
        logger.warning("No valid TELEGRAM_BOT_TOKEN found. Running in scheduler-only mode.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Tracker stopped by user.")
