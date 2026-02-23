import logging
import time
import schedule
from summary_job import run_summary

# Configure standard logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def job():
    logger.info("Starting Polymarket Summary scan cycle...")
    try:
        run_summary()
    except Exception as e:
        logger.error(f"Error during summary scan cycle: {e}")

if __name__ == "__main__":
    logger.info("=== Polymarket Summary Tracker Started ===")
    
    # Run once immediately on startup
    job()
    
    # Schedule to run every day at 08:00 and 20:00
    schedule.every().day.at("08:00").do(job)
    schedule.every().day.at("20:00").do(job)
    logger.info("Scheduler configured. Will scan and send summary every day at 08:00 and 20:00. Press Ctrl+C to exit.")
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Tracker stopped by user.")
