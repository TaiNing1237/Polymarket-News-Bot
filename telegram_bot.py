import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram token or chat ID is missing! Alerts will be logged locally but not sent to Telegram.")
            
    def is_configured(self):
        return bool(self.bot_token and self.chat_id and self.bot_token != "your_bot_token_here")

    def send_message(self, text: str):
        """
        Sends a message to the specified Telegram Chat via Telegram Bot API.
        """
        if not self.is_configured():
            logger.info(f"[MOCK TELEGRAM] Would have sent: {text}")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Successfully sent message to Telegram.")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                logger.error(f"Response: {response.text}")
            return False

    # End of TelegramNotifier
