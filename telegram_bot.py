import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

import json

def get_subscribers():
    subscribers = set()
    default_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if default_chat_id and default_chat_id != "your_bot_token_here":
        subscribers.add(str(default_chat_id))
    
    try:
        if os.path.exists("subscribers.json"):
            with open("subscribers.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for chat_id in data:
                    subscribers.add(str(chat_id))
    except Exception as e:
        logger.error(f"Error reading subscribers.json: {e}")
        
    return list(subscribers)

def add_subscriber(chat_id):
    subscribers = get_subscribers()
    chat_id_str = str(chat_id)
    if chat_id_str not in subscribers:
        subscribers.append(chat_id_str)
        try:
            with open("subscribers.json", "w", encoding="utf-8") as f:
                json.dump(subscribers, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error writing to subscribers.json: {e}")
    return False

def remove_subscriber(chat_id):
    subscribers = get_subscribers()
    chat_id_str = str(chat_id)
    if chat_id_str in subscribers:
        subscribers.remove(chat_id_str)
        try:
            with open("subscribers.json", "w", encoding="utf-8") as f:
                json.dump(subscribers, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error writing to subscribers.json: {e}")
    return False

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not self.bot_token:
            logger.warning("Telegram token is missing! Alerts will be logged locally but not sent to Telegram.")
            
    def is_configured(self):
        return bool(self.bot_token and self.bot_token != "your_bot_token_here")

    def send_message(self, text: str):
        """
        Sends a message to all subscribed Telegram Chats via Telegram Bot API.
        """
        if not self.is_configured():
            logger.info(f"[MOCK TELEGRAM] Would have sent: {text}")
            return False

        subscribers = get_subscribers()
        if not subscribers:
            logger.warning("No subscribers found! Cannot send message.")
            return False

        success = True
        for chat_id in subscribers:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            try:
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"Successfully sent message to Telegram chat {chat_id}.")
            except Exception as e:
                logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    logger.error(f"Response: {response.text}")
                success = False
                
        return success

    # End of TelegramNotifier
