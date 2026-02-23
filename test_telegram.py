import logging
from telegram_bot import TelegramNotifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test():
    notifier = TelegramNotifier()
    if not notifier.is_configured():
        logger.error("\n❌ [錯誤] 無法取得 Telegram 設定！\n請確認你已經在專案根目錄的 `.env` 檔案中填入了:\nTELEGRAM_BOT_TOKEN=...\nTELEGRAM_CHAT_ID=...\n")
        return

    logger.info("Token 存在，嘗試發送測試訊息...")
    success = notifier.send_message("✅ <b>機器人測試成功！</b>\nPolymarket 監控系統已成功與這個 Chat 建置連線。")
    
    if success:
        logger.info("\n✅ 訊息送出成功！請檢查你的 Telegram 對話。如果有收到訊息，你就可以開始執行 main.py 了。")
    else:
        logger.info("\n❌ 訊息送出失敗！請檢查 Token 和 Chat ID 是否正確。")

if __name__ == "__main__":
    test()
